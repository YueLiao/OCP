"""Bit-sliced `layout` ciphers (KNOT) accept HEX test vectors: a hex state splits into its
individual bits (word_bitsize == 1), the build path expands the layout, and every version
verifies. This regressed when the deterministic hex parser gated on word_bitsize >= 4 and only
`execute` (not the preflight / per-version build) expanded the layout.
"""
from agent.skills.cipher_definition import (
    _effective_word_sizes, _effective_state_counts, _hex_to_words,
)
from agent.skills.cipher_spec import CipherSpec


def _knot_family():
    # KNOT-256 minimal: bit-sliced 4 x 64 = 256-bit state. All-zero input -> known output.
    return {
        "name": "KNOTt", "cipher_type": "permutation",
        "layout": {"rows": 4, "cols": "$b/4"},
        "versions": {"KNOT-256": {"nbr_rounds": 52,
                                  "params": {"b": 256, "d": 6, "offsets": [0, 1, 8, 25],
                                             "taps": [5, 4]}}},
        "default_version": "KNOT-256",
        "round_structure": [
            {"layer_type": "subcolumn_sbox", "params": {"sbox_name": "S"}},
            {"layer_type": "shift_rows", "params": {"offsets": [0, 1, 8, 25], "direction": "l"}},
        ],
        "sbox_tables": {"S": [4, 0, 10, 7, 11, 14, 1, 13, 9, 15, 6, 8, 5, 2, 12, 3]},
    }


def test_hex_splits_into_bits_for_bit_sliced():
    # 4 hex digits -> 16 bits, MSB-first.
    assert _hex_to_words("a000", 1) == [1, 0, 1, 0] + [0] * 12


def test_effective_word_size_is_one_for_layout():
    cs = CipherSpec.from_dict(_knot_family())
    assert _effective_word_sizes(cs) == (1, 1)


def test_effective_state_count_is_block_bits_for_layout():
    cs = CipherSpec.from_dict(_knot_family())
    nw, _ = _effective_state_counts(cs)
    assert nw == 256   # rows*cols = 4*64, resolved from the version's b=256


def test_normalize_splits_layout_hex_vector():
    from agent.skills.cipher_definition import _normalize_test_vectors
    tvs = [{"input": "0" * 64, "output": "1" + "0" * 63}]   # 256-bit hex each
    out = _normalize_test_vectors(tvs, "permutation", 1, 1)
    assert len(out[0][0][0]) == 256 and len(out[0][1]) == 256
    assert out[0][1][0] == 0 and out[0][1][3] == 1   # "1" hex = 0001 -> bit 3 set
