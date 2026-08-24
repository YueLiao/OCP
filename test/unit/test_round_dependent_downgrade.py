"""Round-dependent layers (only_rounds/except_rounds) and the L0->L1 granularity
downgrade for ciphers whose key schedule crosses word boundaries (FUTURE class).

Covers two things that must not regress:
1. A round-dependent layer is generated UNROLLED, so the differing round is correct.
   The loop-compressed default assumes every round is identical and silently applies
   the active-round layer everywhere. We pin this with a hand-computed truth.
2. A block cipher whose key schedule rotates across word boundaries downgrades to its
   keyless word-level permutation (L1) instead of failing to build.
"""
import io
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cipher_definition import (
    build_permutation_from_spec,
    build_blockcipher_from_spec,
    verify_cipher_test_vectors,
    key_schedule_needs_bitslicing,
    build_with_downgrade,
    _spec_needs_unroll,
)


def test_spec_needs_unroll_detects_round_dependent_layers():
    plain = CipherSpec(round_structure=[LayerSpec("sbox", {"sbox_name": "S"})])
    assert _spec_needs_unroll(plain) is False
    dep = CipherSpec(round_structure=[LayerSpec("matrix", {}, except_rounds=[-1])])
    assert _spec_needs_unroll(dep) is True
    dep_key = CipherSpec(
        cipher_type="blockcipher",
        round_structure=[LayerSpec("sbox", {"sbox_name": "S"})],
        key_schedule=[LayerSpec("permutation", {"table": [0]}, only_rounds=[1])],
    )
    assert _spec_needs_unroll(dep_key) is True


def test_round_dependent_layer_is_unrolled_correctly():
    # 2 rounds, word_bitsize=4, two words. Rotate word 0 left by 1 EXCEPT the last round
    # (round 2 -> identity). Input [1, 5]:
    #   round 1: rotl(1,1) = 2  -> [2, 5]
    #   round 2: identity       -> [2, 5]
    # The buggy loop-compressed codegen would rotate every round -> rotl(1,2)=4 -> [4,5].
    spec = CipherSpec(
        name="RotExcept", cipher_type="permutation",
        block_size=8, word_bitsize=4, nbr_words=2, nbr_rounds=2,
        round_structure=[
            LayerSpec("rotation", {"direction": "l", "amount": 1, "word_index": 0},
                      except_rounds=[-1]),
        ],
        test_vectors=[[[[1, 5]], [2, 5]]],
    )
    assert spec.validate() == []
    cipher = build_permutation_from_spec(spec)
    with redirect_stdout(io.StringIO()):
        res = verify_cipher_test_vectors(cipher, spec)
    assert res["tested"] and res["all_passed"], res


def _blockcipher_with_key_rotation(amount):
    return CipherSpec(
        name="KRot", cipher_type="blockcipher",
        block_size=16, word_bitsize=4, nbr_words=4, nbr_rounds=2,
        key_size=16, key_word_bitsize=4, key_nbr_words=4,
        key_extract_indices=[0, 1, 2, 3],
        key_schedule=[LayerSpec("rotation", {"direction": "l", "amount": amount, "word_index": 0})],
        sbox_tables={"S": list(range(16))},
        round_structure=[
            LayerSpec("add_round_key", {"operator": "xor", "mask": [1, 1, 1, 1]}),
            LayerSpec("sbox", {"sbox_name": "S", "index": [[0], [1], [2], [3]]}),
        ],
    )


def test_key_schedule_needs_bitslicing_flags_cross_word_rotation():
    assert key_schedule_needs_bitslicing(_blockcipher_with_key_rotation(5))  # 5 >= 4
    assert key_schedule_needs_bitslicing(_blockcipher_with_key_rotation(2)) is None  # legal


def test_build_with_downgrade_drops_to_L1_for_cross_word_key():
    result = build_with_downgrade(_blockcipher_with_key_rotation(5))
    assert result["level"] == "L1"
    assert "permutation_spec" in result and result["permutation_spec"].cipher_type == "permutation"
    # the keyless permutation has no add_round_key layer
    assert all(l.layer_type != "add_round_key"
               for l in result["permutation_spec"].round_structure)


def test_build_with_downgrade_stays_L0_for_word_aligned_key():
    with redirect_stdout(io.StringIO()):
        result = build_with_downgrade(_blockcipher_with_key_rotation(2))
    assert result["level"] == "L0"


# --- Whitening abstraction (pre/post AddRoundKey outside the round function) ---

def _small_blockcipher(nbr_rounds, sbox_except=None, pre=False, post=False):
    return CipherSpec(
        name="Wtest", cipher_type="blockcipher",
        block_size=8, word_bitsize=4, nbr_words=2, nbr_rounds=nbr_rounds,
        key_size=8, key_word_bitsize=4, key_nbr_words=2, key_extract_indices=[0, 1],
        key_schedule=[LayerSpec("permutation", {"table": [1, 0]})],
        sbox_tables={"S": list(range(16))},
        round_structure=[
            LayerSpec("add_round_key", {"operator": "xor", "mask": [1, 1]}),
            LayerSpec("sbox", {"sbox_name": "S", "index": [[0], [1]]}, except_rounds=sbox_except),
        ],
        pre_whitening=pre, post_whitening=post,
    )


def _eval_block(spec, inputs):
    with redirect_stdout(io.StringIO()):
        c = build_blockcipher_from_spec(spec)
        fd = get_files_dir(); fd.mkdir(parents=True, exist_ok=True)
        imp.generate_implementation(c, fd / f"{c.name}.py", "python", _spec_needs_unroll(spec))
        return imp.evaluate(c, inputs, output_len=2)


def test_expand_whitening_adds_round_and_marks_non_key_layers():
    post = _small_blockcipher(2, post=True).expand_whitening()
    assert post.nbr_rounds == 3
    assert post.round_structure[1].except_rounds == [-1]   # sbox skipped in last round
    assert post.round_structure[0].except_rounds is None    # add_round_key runs every round
    pre = _small_blockcipher(2, pre=True).expand_whitening()
    assert pre.nbr_rounds == 3 and pre.round_structure[1].except_rounds == [1]


def test_spec_needs_unroll_true_for_whitening():
    assert _spec_needs_unroll(_small_blockcipher(2, post=True)) is True


def test_post_whitening_equals_manual_extra_round():
    # The post_whitening abstraction must equal a hand-written extra round whose sbox is
    # skipped in the last round (only the round key is added there).
    abstract = _eval_block(_small_blockcipher(2, post=True), [[3, 10], [5, 6]])
    manual = _eval_block(_small_blockcipher(3, sbox_except=[-1]), [[3, 10], [5, 6]])
    assert abstract == manual


def test_whitening_survives_dict_roundtrip():
    spec = _small_blockcipher(2, post=True)
    back = CipherSpec.from_dict(spec.to_dict())
    assert back.post_whitening is True and back.pre_whitening is False


def test_add_constant_row_length_must_match_mask():
    # constant_mask selects 16 words but each row has 4 values -> codegen would index past
    # the row end (the Midori draft bug); validate must flag it at draft time.
    bad = CipherSpec(
        name="C", cipher_type="permutation", block_size=64, word_bitsize=4,
        nbr_words=16, nbr_rounds=2,
        round_structure=[LayerSpec("add_constant", {
            "add_type": "xor", "constant_mask": [1] * 16,
            "constant_table": [[2, 4, 3, 15], [1, 2, 3, 4]]})],
    )
    assert any("add_constant" in e and "16 word" in e for e in bad.validate())
    # matching row length -> no add_constant error
    ok = CipherSpec(
        name="C", cipher_type="permutation", block_size=16, word_bitsize=4,
        nbr_words=4, nbr_rounds=2,
        round_structure=[LayerSpec("add_constant", {
            "add_type": "xor", "constant_mask": [1, 1, 1, 1],
            "constant_table": [[1, 2, 3, 4], [5, 6, 7, 8]]})],
    )
    assert not any("add_constant" in e for e in ok.validate())


def test_round_dependent_key_extraction_alternates_halves():
    # key_extract_indices as a list of lists = round-dependent: round 1 extracts K0=[0,1],
    # round 2 extracts K1=[2,3] (Midori/LED-style alternation). No key evolution, identity
    # sbox: output = [1^k0^k2, 2^k1^k3] = [1^3^5, 2^4^6] = [7, 0].
    spec = CipherSpec(
        name="AltKey", cipher_type="blockcipher",
        block_size=8, word_bitsize=4, nbr_words=2, nbr_rounds=2,
        key_size=16, key_word_bitsize=4, key_nbr_words=4,
        key_extract_indices=[[0, 1], [2, 3]], key_schedule=None,
        sbox_tables={"S": list(range(16))},
        round_structure=[
            LayerSpec("add_round_key", {"operator": "xor", "mask": [1, 1]}),
            LayerSpec("sbox", {"sbox_name": "S", "index": [[0], [1]]}),
        ],
    )
    assert _spec_needs_unroll(spec) is True   # can't loop-compress round-varying extraction
    assert spec.validate() == []
    with redirect_stdout(io.StringIO()):
        c = build_blockcipher_from_spec(spec)
        fd = get_files_dir(); fd.mkdir(parents=True, exist_ok=True)
        imp.generate_implementation(c, fd / f"{c.name}.py", "python", _spec_needs_unroll(spec))
        out = imp.evaluate(c, [[1, 2], [3, 4, 5, 6]], output_len=2)
    assert out == [7, 0], out


def test_round_dependent_extraction_phase_length_must_match():
    # phases of differing length are flagged at validate time
    spec = CipherSpec(
        name="C", cipher_type="blockcipher", block_size=8, word_bitsize=4, nbr_words=2,
        nbr_rounds=2, key_size=16, key_word_bitsize=4, key_nbr_words=4,
        key_extract_indices=[[0, 1], [2]],  # 2 vs 1
        round_structure=[LayerSpec("sbox", {"sbox_name": "S"})],
        sbox_tables={"S": list(range(16))},
    )
    assert any("differing lengths" in e for e in spec.validate())


def test_key_word_bitsize_must_equal_state_word_bitsize():
    # key modeled as 2x64-bit words over a 4-bit state (LLM reshaping to make a cross-cell
    # rotation legal) is a granularity conflict -> flagged; equal widths -> fine.
    bad = CipherSpec(
        name="C", cipher_type="blockcipher", block_size=64, word_bitsize=4, nbr_words=16,
        nbr_rounds=10, key_size=128, key_word_bitsize=64, key_nbr_words=2,
        key_extract_indices=[0, 1],
        round_structure=[LayerSpec("sbox", {"sbox_name": "S"})], sbox_tables={"S": list(range(16))})
    assert any("key_word_bitsize" in e for e in bad.validate())
    ok = CipherSpec(
        name="C", cipher_type="blockcipher", block_size=64, word_bitsize=4, nbr_words=16,
        nbr_rounds=10, key_size=64, key_word_bitsize=4, key_nbr_words=16,
        key_extract_indices=[0, 1, 2, 3],
        round_structure=[LayerSpec("sbox", {"sbox_name": "S"})], sbox_tables={"S": list(range(16))})
    assert not any("key_word_bitsize" in e for e in ok.validate())
