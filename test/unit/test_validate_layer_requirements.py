"""validate() must surface a READABLE error for anything the builder requires, so the build
stage never raises a bare KeyError/IndexError. These close gaps where validate() returned [] but
the build then crashed: operator layers (xor/and/or/modadd/andxor/not/equal/n_xor) missing
input_indices/output_indices, wrong operator arity, S-box outputs out of range, and key-extract
indices outside the key state. Deliberately NOT added (they'd reject valid ciphers): permutation
bijectivity (partial permutations exist) and output-source coverage (partial-state updates).
"""
from agent.skills.cipher_spec import CipherSpec, LayerSpec


def _perm(rs, **kw):
    d = dict(name="T", cipher_type="permutation", block_size=8, word_bitsize=4,
             nbr_words=2, nbr_rounds=1, round_structure=rs)
    d.update(kw)
    return CipherSpec(**d).validate()


def test_operator_missing_indices_is_flagged():
    assert any("input_indices" in e for e in _perm([LayerSpec("xor", {})]))


def test_operator_arity_is_checked():
    # xor is 2-ary; a 3-word input group is wrong
    assert any("2 word" in e or "2-ary" in e
               for e in _perm([LayerSpec("xor", {"input_indices": [[0, 1, 0]], "output_indices": [1]})]))
    # andxor is 3-ary; a 2-word group is wrong
    assert any("3 word" in e or "3-ary" in e
               for e in _perm([LayerSpec("andxor", {"input_indices": [[0, 1]], "output_indices": [1]})]))
    # n_xor takes any arity - a 2- or 3-word group is fine
    assert _perm([LayerSpec("n_xor", {"input_indices": [[0, 1]], "output_indices": [1]})]) == []


def test_output_count_must_match_input_groups():
    assert any("one per group" in e
               for e in _perm([LayerSpec("xor", {"input_indices": [[0, 1]], "output_indices": [0, 1]})]))


def test_sbox_output_out_of_range_is_flagged():
    errs = _perm([LayerSpec("sbox", {"sbox_name": "S", "index": [[0]]})],
                 sbox_tables={"S": [0, 1, 99, 3]})       # 99 >= 4 (a 2-bit S-box)
    assert any("output range" in e for e in errs)


def test_sbox_index_group_size_must_match_sbox_width():
    sb = [12, 10, 13, 3, 14, 11, 15, 7, 8, 9, 1, 5, 0, 2, 4, 6]   # a 4-bit S-box

    def mk(index, wb=4, nw=16):
        return CipherSpec(name="M", cipher_type="permutation", block_size=wb * nw, word_bitsize=wb,
                          nbr_words=nw, nbr_rounds=1, sbox_tables={"Sb0": sb},
                          round_structure=[LayerSpec("sbox", {"sbox_name": "Sb0",
                                                              "index": index})]).validate()
    # 4-bit S-box over 4-bit words -> 1 word/group. 4-word groups (the Midori mis-grouping) is wrong.
    assert any("word(s) per group" in e for e in mk([[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]))
    assert mk([[j] for j in range(16)]) == []                    # correct: 1 word/group
    # bit-sliced (word_bitsize=1): the same 4-bit S-box groups all 4 bits
    assert mk([[4 * c + k for k in range(4)] for c in range(16)], wb=1, nw=64) == []


def test_key_archetype_conflicts_are_rejected():
    # archetype + a hand-written add_round_key = double key addition (the Midori mis-draft)
    base = dict(name="M", cipher_type="blockcipher", block_size=16, word_bitsize=4, nbr_words=4,
                nbr_rounds=2, key_size=32, key_word_bitsize=4, key_nbr_words=8,
                key_archetype={"type": "static_alternating", "shares": 2, "whitening": "xor_shares"},
                sbox_tables={"S": list(range(16))})
    with_ark = CipherSpec(**base, round_structure=[
        LayerSpec("sbox", {"sbox_name": "S", "index": [[j] for j in range(4)]}),
        LayerSpec("add_round_key", {"operator": "xor"})]).validate()
    assert any("archetype" in e and "add_round_key" in e for e in with_ark)
    # archetype + a hand-written key_extract_indices is also a conflict
    with_ext = CipherSpec(**base, key_extract_indices=[[0, 1, 2, 3], [4, 5, 6, 7]],
                          round_structure=[LayerSpec("sbox", {"sbox_name": "S",
                                                              "index": [[j] for j in range(4)]})]).validate()
    assert any("archetype" in e and "key_extract_indices" in e for e in with_ext)


def test_test_vector_wrong_length_is_flagged():
    # a 31-word output for a 4-word permutation - a hallucinated vector the KAT can never match
    errs = CipherSpec(name="P", cipher_type="permutation", block_size=16, word_bitsize=4,
                      nbr_words=4, nbr_rounds=1,
                      round_structure=[LayerSpec("xor", {"input_indices": [[0, 1]],
                                                         "output_indices": [1]})],
                      test_vectors=[{"input": [0, 0, 0, 0], "output": list(range(31))}]).validate()
    assert any("word(s); this cipher outputs 4" in e for e in errs)


def test_key_extract_index_out_of_range_is_flagged():
    errs = CipherSpec(name="B", cipher_type="blockcipher", block_size=8, word_bitsize=4,
                      nbr_words=2, nbr_rounds=1, key_size=8, key_word_bitsize=4, key_nbr_words=2,
                      key_extract_indices=[0, 5],          # 5 >= key state (2)
                      round_structure=[LayerSpec("add_round_key",
                                       {"operator": "xor", "mask": [1, 0]})]).validate()
    assert any("key state" in e for e in errs)
