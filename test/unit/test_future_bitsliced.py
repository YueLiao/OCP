"""FUTURE-64/128 built end to end in FULL bit-sliced form (word_bitsize=1) from a
CipherSpec, verified against the designer's known-answer test vectors.

This is the L2 capability: a cipher whose 4-bit-cell data path (GF(2^4) MixColumn) and
whose key schedule (a whole-64-bit-half rotate-by-5 that crosses cell boundaries) cannot
share a word granularity, so both are modeled at word_bitsize=1. The bit-level MixColumn
matrix, ShiftRow permutation and key-rotation permutations are DERIVED by the cell_sliced
helpers rather than hand-written. Exercises together: gf_matrix_to_bit_matrix (GF(2^4)->
GF(2) bit expansion via a binary MatrixLayer), cell_perm_to_bit_perm, bit_rotation_perm,
except_rounds (no MixColumn in the last round), pre_whitening, and unrolled code generation.
"""
import io
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cipher_definition import build_blockcipher_from_spec, _spec_needs_unroll
from agent.skills.cell_sliced import (
    gf_matrix_to_bit_matrix, cell_perm_to_bit_perm, bit_rotation_perm,
)

SBOX = [0x1, 0x3, 0x0, 0x2, 0x7, 0xe, 0x4, 0xd, 0x9, 0xa, 0xc, 0x6, 0xf, 0x5, 0x8, 0xb]
MIX = [[8, 9, 1, 8], [3, 2, 9, 9], [2, 3, 8, 9], [9, 9, 8, 1]]
SR = [0, 13, 10, 7, 4, 1, 14, 11, 8, 5, 2, 15, 12, 9, 6, 3]
RC_HEX = [0x1248248148128124, 0x2481481281241248, 0x4812812412482481, 0x8124124824814812, 0,
          0x1248248148128124, 0x2481481281241248, 0x4812812412482481, 0x8124124824814812, 0]

# designer test vectors (AFRICACRYPT 2022 paper, appendix A)
KATS = [
    (0xffffffffffffffff, 0x000102030405060708090a0b0c0d0e0f, 0x68e030733fe73b8a),
    (0xffffffffffffffff, 0xffffffffffffffffffffffffffffffff, 0x333ba4b7646e09f2),
    (0x5353414d414e5441, 0x05192832010913645029387763948871, 0x5ce1b8d8d01a9310),
    (0x6162636465666768, 0x00000000000000000000000000000000, 0xcc5ba5e52038b6df),
    (0x0000000000000000, 0x00000000000000000000000000000000, 0x298650c13199cdec),
]


def _to_bits(v, n):
    return [(v >> (n - 1 - j)) & 1 for j in range(n)]


def _future_bitsliced_spec():
    sbox_idx = [[4 * i + k for k in range(4)] for i in range(16)]
    mix_bit = gf_matrix_to_bit_matrix(MIX, 0x13, 4)             # 16x16 binary
    mix_idx = [[16 * c + k for k in range(16)] for c in range(4)]
    sr_bits = cell_perm_to_bit_perm(SR, 4)
    swap = [64 + j for j in range(64)] + [j for j in range(64)]
    rot = bit_rotation_perm(64, 5, "l")
    rot_low = [rot[j] for j in range(64)] + [64 + j for j in range(64)]
    # row 0 = the (skipped) whitening round; rows 1..10 = RC_1..RC_10
    rc_table = [[0] * 64] + [_to_bits(rc, 64) for rc in RC_HEX]
    return CipherSpec(
        name="FUTUREbs", cipher_type="blockcipher",
        block_size=64, word_bitsize=1, nbr_words=64, nbr_rounds=10,
        key_size=128, key_word_bitsize=1, key_nbr_words=128,
        key_extract_indices=list(range(64)),
        pre_whitening=True,
        sbox_tables={"S": SBOX},
        key_schedule=[
            LayerSpec("permutation", {"table": swap}),
            LayerSpec("permutation", {"table": rot_low}, except_rounds=[1]),
        ],
        round_structure=[
            LayerSpec("sbox", {"sbox_name": "S", "index": sbox_idx}),
            LayerSpec("matrix", {"matrix": mix_bit, "indices": mix_idx}, except_rounds=[-1]),
            LayerSpec("permutation", {"table": sr_bits}),
            LayerSpec("add_round_key", {"operator": "xor", "mask": [1] * 64}),
            LayerSpec("add_constant", {"add_type": "xor", "constant_mask": [1] * 64,
                                       "constant_table": rc_table}),
        ],
    )


def _future_cell_layout_spec():
    """Same FUTURE, but the DATA PATH is described with high-level CELL layers and a
    cell_layout; expand_cell_sliced derives the bit-level S-box groups, MixColumn matrix
    and ShiftRow permutation. The key schedule is still bit-level (helper-built)."""
    swap = [64 + j for j in range(64)] + [j for j in range(64)]
    rot = bit_rotation_perm(64, 5, "l")
    rot_low = [rot[j] for j in range(64)] + [64 + j for j in range(64)]
    rc_table = [[0] * 64] + [_to_bits(rc, 64) for rc in RC_HEX]
    return CipherSpec(
        name="FUTUREcell", cipher_type="blockcipher", nbr_rounds=10,
        cell_layout={"cell_bits": 4, "nbr_cells": 16},
        key_size=128, key_word_bitsize=1, key_nbr_words=128,
        key_extract_indices=list(range(64)), pre_whitening=True,
        sbox_tables={"S": SBOX},
        key_schedule=[
            LayerSpec("permutation", {"table": swap}),
            LayerSpec("permutation", {"table": rot_low}, except_rounds=[1]),
        ],
        round_structure=[
            LayerSpec("subcell_sbox", {"sbox_name": "S"}),
            LayerSpec("mixcolumn", {"matrix": MIX, "polynomial": "0x3",
                                    "columns": [[0, 1, 2, 3], [4, 5, 6, 7],
                                                [8, 9, 10, 11], [12, 13, 14, 15]]},
                      except_rounds=[-1]),
            LayerSpec("cell_shiftrow", {"table": SR}),
            LayerSpec("add_round_key", {"operator": "xor", "mask": [1] * 64}),
            LayerSpec("add_constant", {"add_type": "xor", "constant_mask": [1] * 64,
                                       "constant_table": [[0] * 64] + [_to_bits(rc, 64) for rc in RC_HEX]}),
        ],
    )


def _run_kats(spec):
    assert spec.validate() == []
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)
        fd = get_files_dir(); fd.mkdir(parents=True, exist_ok=True)
        imp.generate_implementation(cipher, fd / f"{cipher.name}.py", "python",
                                    _spec_needs_unroll(spec))
    for P, K, C in KATS:
        with redirect_stdout(io.StringIO()):
            out = imp.evaluate_python(cipher, [_to_bits(P, 64), _to_bits(K, 128)], output_len=64)
        got = int("".join(str(b) for b in out), 2)
        assert got == C, f"P={P:016x} K={K:032x}: got {got:016x} want {C:016x}"


def test_future_bitsliced_matches_designer_kats():
    _run_kats(_future_bitsliced_spec())


def test_future_cell_layout_expander_matches_designer_kats():
    # The data-path expander (cell_layout + subcell_sbox/mixcolumn/cell_shiftrow) must
    # reproduce the same designer KATs as the hand-written bit-level spec.
    _run_kats(_future_cell_layout_spec())


def test_expand_cell_sliced_lowers_data_path_layers():
    conc = _future_cell_layout_spec().expand_cell_sliced()
    assert conc.word_bitsize == 1 and conc.nbr_words == 64
    types = [l.layer_type for l in conc.round_structure]
    assert types == ["sbox", "matrix", "permutation", "add_round_key", "add_constant"]
    # cell ShiftRow lowered to the bit permutation
    assert conc.round_structure[2].params["table"] == cell_perm_to_bit_perm(SR, 4)
    # MixColumn kept its round-dependent scope through expansion
    assert conc.round_structure[1].except_rounds == [-1]


def _future_facts_dict():
    """The facts an LLM would extract for FUTURE using the high-level abstractions."""
    swap = [64 + j for j in range(64)] + [j for j in range(64)]
    rot = bit_rotation_perm(64, 5, "l")
    rot_low = [rot[j] for j in range(64)] + [64 + j for j in range(64)]
    rc = [[0] * 64] + [_to_bits(x, 64) for x in RC_HEX]
    return {
        "name": "FUTURE", "primitive_type": "blockcipher",
        "cell_layout": {"cell_bits": 4, "nbr_cells": 16},
        "rounds": {"nbr_rounds": 10}, "pre_whitening": True,
        "operations": [
            {"type": "subcell_sbox", "params": {"sbox_name": "S"}},
            {"type": "mixcolumn", "params": {"matrix": MIX, "polynomial": "0x3",
                "columns": [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]},
                "except_rounds": [-1]},
            {"type": "cell_shiftrow", "params": {"table": SR}},
            {"type": "add_round_key", "params": {"operator": "xor", "mask": [1] * 64}},
            {"type": "add_constant", "params": {"add_type": "xor", "constant_mask": [1] * 64,
                "constant_table": rc}},
        ],
        "tables": {"sbox_tables": {"S": SBOX}},
        "key_schedule": {"key_size": 128, "key_word_bitsize": 1, "key_nbr_words": 128,
            "key_extract_indices": list(range(64)),
            "round_structure": [
                {"type": "permutation", "params": {"table": swap}},
                {"type": "permutation", "params": {"table": rot_low}, "except_rounds": [1]},
            ]},
    }


def test_future_via_facts_layer_transfers_and_matches_kats():
    # The text-first FACTS layer must carry cell_layout, whitening and round-dependent scope
    # through to the spec, so an LLM that extracts these high-level facts gets a correct FUTURE.
    from agent.skills.cipher_text_input import CipherFacts, cipher_spec_payload_from_facts
    facts = CipherFacts.from_dict(_future_facts_dict())
    assert facts.validate()[0] == []
    payload = cipher_spec_payload_from_facts(facts)
    assert payload.get("cell_layout") == {"cell_bits": 4, "nbr_cells": 16}
    assert payload.get("pre_whitening") is True
    assert [l["layer_type"] for l in payload["round_structure"]][:3] == \
        ["subcell_sbox", "mixcolumn", "cell_shiftrow"]
    assert payload["round_structure"][1].get("except_rounds") == [-1]  # not dropped
    _run_kats(CipherSpec.from_dict(payload))


def test_verify_cipher_test_vectors_works_for_cell_layout_spec():
    # regression: verify_cipher_test_vectors must use the CIPHER's natural output length, not the
    # declarative spec.nbr_words (a cell_layout spec carries a placeholder until expansion). A
    # regression there rejected every 64-bit vector as "64 != 2" and reported 0/N.
    import io as _io
    from contextlib import redirect_stdout as _rs
    from agent.skills.cipher_definition import build_blockcipher_from_spec, verify_cipher_test_vectors
    spec = _future_cell_layout_spec()
    spec.test_vectors = [[[_to_bits(P, 64), _to_bits(K, 128)], _to_bits(C, 64)] for P, K, C in KATS]
    with _rs(_io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)
        res = verify_cipher_test_vectors(cipher, spec)
    assert res["all_passed"] and res["passed"] == len(KATS)
