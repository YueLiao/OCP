"""Agent-side enablers for the static_alternating + whitening key-schedule archetype:

  1. pi_round_constant_cells(n) - a ROUND CONSTANT GENERATOR: Midori's alpha_i/beta_i read
     from the fractional hex of pi, so a spec can say {"source": "pi_hex"} instead of the LLM
     hand-copying 700+ bits (the error-prone part of extracting Midori-like ciphers).
  2. key_extract_indices entries of the form {"xor": [share0, share1]} - a COMBINED subkey
     built inside the SUBKEYS function (extract both shares, XOR), i.e. Midori's whitening
     key WK = K0 (+) K1. This is the one capability the plain single-extraction build lacked.

Both are exercised by building a Midori64 CipherSpec (the shape the archetype expander emits)
and checking it against the designer's Appendix A test vectors.
"""
import io
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_spec import CipherSpec, LayerSpec, pi_round_constant_cells
from agent.skills.cipher_definition import build_blockcipher_from_spec, _spec_needs_unroll

_SC = [0, 10, 5, 15, 14, 4, 11, 1, 9, 3, 12, 6, 7, 13, 2, 8]
_M = [[0, 1, 1, 1], [1, 0, 1, 1], [1, 1, 0, 1], [1, 1, 1, 0]]
_COL = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]
_SB0 = [12, 10, 13, 3, 14, 11, 15, 7, 8, 9, 1, 5, 0, 2, 4, 6]


def _midori64_spec():
    wk = {"xor": [list(range(16)), list(range(16, 32))]}          # WK = K0 (+) K1
    extract = [wk] + [list(range(0, 16)) if r % 2 == 0 else list(range(16, 32))
                      for r in range(2, 17)] + [wk]               # 17 rounds: pre-WK, K0/K1, post-WK
    ctable = [[0] * 16] + pi_round_constant_cells(15) + [[0] * 16]  # row r-1 used by round r
    return CipherSpec(
        name="MidoriArch", cipher_type="blockcipher",
        block_size=64, word_bitsize=4, nbr_words=16, nbr_rounds=17,
        key_size=128, key_word_bitsize=4, key_nbr_words=32,
        key_extract_indices=extract, sbox_tables={"Sb0": _SB0},
        round_structure=[
            LayerSpec("add_round_key", {"operator": "xor", "mask": [1] * 16}),
            LayerSpec("add_constant", {"add_type": "xor", "constant_mask": [1] * 16,
                                       "constant_table": ctable}, except_rounds=[1, 17]),
            LayerSpec("sbox", {"sbox_name": "Sb0", "index": [[j] for j in range(16)]}, except_rounds=[17]),
            LayerSpec("permutation", {"table": _SC}, except_rounds=[16, 17]),
            LayerSpec("matrix", {"matrix": _M, "indices": _COL, "polynomial": "0x0"}, except_rounds=[16, 17]),
        ],
    )


def _pack(cells):
    x = 0
    for v in cells:
        x = (x << 4) | (v & 0xF)
    return x


def test_pi_round_constant_generator_shape():
    rows = pi_round_constant_cells(15)
    assert len(rows) == 15 and all(len(r) == 16 for r in rows)
    assert all(v in (0, 1) for r in rows for v in r)
    assert rows[0] == [0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1]  # alpha_0 from pi 2,4,3,f


def test_xor_extraction_spec_validates():
    assert _midori64_spec().validate() == []


def test_midori64_from_spec_with_xor_whitening_matches_kats():
    spec = _midori64_spec()
    assert _spec_needs_unroll(spec)
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)
        fd = get_files_dir(); fd.mkdir(parents=True, exist_ok=True)
        imp.generate_implementation(cipher, fd / f"{cipher.name}.py", "python", True)
    kats = [
        ([0] * 16, [0] * 32, 0x3c9cceda2bbd449a),
        ([4, 2, 12, 2, 0, 15, 13, 3, 11, 5, 8, 6, 8, 7, 9, 14],
         [6, 8, 7, 13, 14, 13, 3, 11, 3, 12, 8, 5, 11, 3, 15, 3,
          5, 11, 1, 0, 0, 9, 8, 6, 3, 14, 2, 10, 8, 12, 11, 15], 0x66bcdc6270d901cd),
    ]
    for P, K, C in kats:
        with redirect_stdout(io.StringIO()):
            out = imp.evaluate_python(cipher, [P, K], output_len=64)
        assert _pack(out[:16]) == C, f"got {_pack(out[:16]):016x} want {C:016x}"


# --- The declarative sugar: key_archetype + round_constants -> expand_key_archetype() ---

def _midori64_data_path():
    return [
        LayerSpec("sbox", {"sbox_name": "Sb0", "index": [[j] for j in range(16)]}),
        LayerSpec("permutation", {"table": _SC}),
        LayerSpec("matrix", {"matrix": _M, "indices": _COL, "polynomial": "0x0"}),
    ]


def _midori64_declarative_spec():
    # what an LLM emits: data path only + a 4-field key archetype
    return CipherSpec(
        name="MidoriDecl", cipher_type="blockcipher",
        block_size=64, word_bitsize=4, nbr_words=16, nbr_rounds=16,
        key_size=128, key_word_bitsize=4, key_nbr_words=32,
        sbox_tables={"Sb0": _SB0}, round_structure=_midori64_data_path(),
        key_archetype={"type": "static_alternating", "shares": 2, "whitening": "xor_shares",
                       "round_constants": {"source": "pi_hex", "count": 15}})


def test_expand_key_archetype_shape():
    exp = _midori64_declarative_spec().expand_key_archetype()
    assert exp.nbr_rounds == 17                                  # R + 1 for post-whitening
    assert [l.layer_type for l in exp.round_structure] == \
        ["add_round_key", "add_constant", "sbox", "permutation", "matrix"]
    assert exp.key_extract_indices[0] == {"xor": [list(range(16)), list(range(16, 32))]}
    assert exp.key_extract_indices[1] == list(range(16))         # round 2 -> K0
    assert exp.key_extract_indices[16] == {"xor": [list(range(16)), list(range(16, 32))]}
    assert exp.key_archetype is None                             # consumed


def test_declarative_archetype_validates_and_matches_kats():
    spec = _midori64_declarative_spec()
    assert spec.validate() == []                                 # validate expands then checks
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)
        fd = get_files_dir(); fd.mkdir(parents=True, exist_ok=True)
        imp.generate_implementation(cipher, fd / f"{cipher.name}.py", "python", True)
        out = imp.evaluate_python(cipher, [[0] * 16, [0] * 32], output_len=64)
    assert _pack(out[:16]) == 0x3c9cceda2bbd449a


def test_archetype_carries_through_facts_layer():
    # The text-first FACTS layer must carry key_archetype to the payload so an LLM that
    # declares it gets a correct Midori without a hand-written extraction table.
    from agent.skills.cipher_text_input import CipherFacts, cipher_spec_payload_from_facts
    facts = CipherFacts.from_dict({
        "name": "MidoriFactsTest", "primitive_type": "blockcipher",  # unique name: evaluate reads files.<name>
        "rounds": {"nbr_rounds": 16},
        "state": {"block_size": 64, "word_bitsize": 4, "nbr_words": 16},
        "operations": [
            {"type": "sbox", "params": {"sbox_name": "Sb0", "index": [[j] for j in range(16)]}},
            {"type": "permutation", "params": {"table": _SC}},
            {"type": "matrix", "params": {"matrix": _M, "indices": _COL, "polynomial": "0x0"}},
        ],
        "tables": {"sbox_tables": {"Sb0": _SB0}},
        "key_schedule": {"key_size": 128, "key_word_bitsize": 4, "key_nbr_words": 32},
        "key_archetype": {"type": "static_alternating", "shares": 2, "whitening": "xor_shares",
                          "round_constants": {"source": "pi_hex", "count": 15}},
    })
    assert facts.validate()[0] == []                             # no "key_extract_indices required"
    payload = cipher_spec_payload_from_facts(facts)
    assert payload.get("key_archetype")
    spec = CipherSpec.from_dict(payload)
    assert spec.validate() == []
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)
        fd = get_files_dir(); fd.mkdir(parents=True, exist_ok=True)
        imp.generate_implementation(cipher, fd / f"{cipher.name}.py", "python", True)  # name must match evaluate()
        out = imp.evaluate_python(cipher, [[0] * 16, [0] * 32], output_len=64)
    assert _pack(out[:16]) == 0x3c9cceda2bbd449a


def test_versioned_spec_builds_by_instantiating_default():
    # A versioned family carries placeholder 0 dimensions at top level; build_* must
    # instantiate the default version first, else it constructs 0 rounds/words and crashes
    # with "list index out of range" (the reported bug). Here: build must NOT raise.
    from agent.skills.cipher_definition import build_blockcipher_from_spec
    spec = CipherSpec.from_dict({
        "name": "Verd", "cipher_type": "blockcipher",
        "block_size": 0, "word_bitsize": 0, "nbr_words": 0, "nbr_rounds": 0,
        "key_size": 16, "key_word_bitsize": 4, "key_nbr_words": 4,
        "key_extract_indices": [0, 1, 2, 3], "sbox_tables": {"S": list(range(16))},
        "round_structure": [
            {"layer_type": "add_round_key", "params": {"operator": "xor", "mask": [1, 1, 1, 1]}},
            {"layer_type": "sbox", "params": {"sbox_name": "S", "index": [[0], [1], [2], [3]]}},
        ],
        "versions": {"A": {"block_size": 16, "word_bitsize": 4, "nbr_words": 4, "nbr_rounds": 4}},
        "default_version": "A",
    })
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)          # must not raise IndexError
    assert cipher.functions["PERMUTATION"].nbr_rounds == 4  # instantiated version A


def test_key_archetype_composes_with_cell_layout():
    # Midori declared the way the LLM prefers: cell_layout + CELL ops (subcell_sbox/
    # cell_shiftrow/mixcolumn) + a key_archetype. expand_key_archetype must emit BIT-level
    # key add / constants (mask over all cell_bits*nbr_cells bits, each cell's constant at its
    # LSB, key modeled bit-sliced) so it composes with the cell_layout lowering. -> correct KAT.
    spec = CipherSpec(
        name="MidoriCell", cipher_type="blockcipher",
        cell_layout={"cell_bits": 4, "nbr_cells": 16}, nbr_rounds=16,
        key_size=128, key_word_bitsize=4, key_nbr_words=32, sbox_tables={"Sb0": _SB0},
        round_structure=[
            LayerSpec("subcell_sbox", {"sbox_name": "Sb0"}),
            LayerSpec("cell_shiftrow", {"table": _SC}),
            LayerSpec("mixcolumn", {"matrix": _M, "polynomial": "0x3",
                                    "columns": [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]}),
        ],
        key_archetype={"type": "static_alternating", "shares": 2, "whitening": "xor_shares",
                       "round_constants": {"source": "pi_hex"}})
    assert spec.validate() == []
    exp = spec.expand_key_archetype()
    assert exp.key_word_bitsize == 1 and exp.key_nbr_words == 128     # key made bit-sliced
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        out = imp.evaluate_python(cipher, [[0] * 64, [0] * 128], output_len=64)
    assert int("".join(str(b) for b in out[:64]), 2) == 0x3c9cceda2bbd449a


def test_matrix_layer_dim_mismatch_is_caught_by_validate():
    # A 16x16 matrix with 4-word column groups (bit-level matrix, cell-level grouping) must be
    # flagged at validate time, not crash at build ("input vector does not match matrix size").
    spec = CipherSpec(
        name="BadMat", cipher_type="blockcipher",
        block_size=64, word_bitsize=1, nbr_words=64, nbr_rounds=2,
        key_size=64, key_word_bitsize=1, key_nbr_words=64, key_extract_indices=list(range(64)),
        sbox_tables={},
        round_structure=[
            LayerSpec("matrix", {"matrix": [[1] * 16 for _ in range(16)],
                                 "indices": [[4 * c + r for r in range(4)] for c in range(16)]}),
        ])
    errs = spec.validate()
    assert any("matrix" in e and "16x16" in e for e in errs), errs


def test_word_level_midori64_key_archetype_kat():
    """Midori64 is a WORD-level cipher (word_bitsize=4, binary MixColumn) - the key_archetype
    emits the whitening + alternating keys + pi constants, and it verifies against the all-zero
    designer vector. This pins that a cell-oriented SPN with a binary matrix must NOT be pushed
    to bit-level cell_layout (that path is unnecessary and was failing to build)."""
    from agent.skills.cipher_definition import verify_cipher_test_vectors, _normalize_test_vectors
    cs = CipherSpec(
        name="MidoriArchWL", cipher_type="blockcipher",
        block_size=64, word_bitsize=4, nbr_words=16, nbr_rounds=16,
        key_size=128, key_word_bitsize=4, key_nbr_words=32,
        key_archetype={"type": "static_alternating", "shares": 2, "whitening": "xor_shares",
                       "round_constants": {"source": "pi_hex", "count": 15}},
        sbox_tables={"Sb0": _SB0},
        round_structure=[
            LayerSpec("sbox", {"sbox_name": "Sb0", "index": [[j] for j in range(16)]}),
            LayerSpec("permutation", {"table": _SC}),
            LayerSpec("matrix", {"matrix": _M, "indices": _COL, "polynomial": "0x0"}),
        ],
    )
    cs.test_vectors = _normalize_test_vectors(
        [{"plaintext": "0000000000000000", "key": "0" * 32, "output": "3c9cceda2bbd449a"}],
        "blockcipher", 4, 4)
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(cs)
        res = verify_cipher_test_vectors(cipher, cs)
    assert res["all_passed"], res.get("failures")
