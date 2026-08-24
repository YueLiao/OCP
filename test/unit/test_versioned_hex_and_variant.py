"""Versioned families: hex test vectors must split with the DEFAULT VERSION's word sizes
(top-level sizes are 0 until the builder instantiates), and a family paper's other-variant
KATs (Midori128 on a Midori64 build) must be dropped, not left to fail an unrepairable KAT.
"""
from types import SimpleNamespace

from agent.skills.cipher_definition import (
    _effective_word_sizes, _effective_state_counts, _drop_cross_variant_vectors,
    _normalize_test_vectors,
)


def _midori_family():
    # Top-level sizes 0 (a versioned spec), real sizes under versions.
    return SimpleNamespace(
        word_bitsize=0, key_word_bitsize=0, nbr_words=0, key_nbr_words=0,
        default_version="Midori64",
        versions={
            "Midori64": {"word_bitsize": 4, "nbr_words": 16,
                         "key_word_bitsize": 4, "key_nbr_words": 32},
            "Midori128": {"word_bitsize": 8, "nbr_words": 16,
                          "key_word_bitsize": 8, "key_nbr_words": 16},
        },
    )


class TestEffectiveSizes:
    def test_word_sizes_from_default_version(self):
        assert _effective_word_sizes(_midori_family()) == (4, 4)

    def test_state_counts_from_default_version(self):
        assert _effective_state_counts(_midori_family()) == (16, 32)

    def test_params_nested_sizes(self):
        spec = SimpleNamespace(
            word_bitsize=0, key_word_bitsize=None, nbr_words=0, key_nbr_words=None,
            default_version="A", versions={"A": {"params": {"word_bitsize": 8, "nbr_words": 4}}})
        assert _effective_word_sizes(spec) == (8, 8)
        assert _effective_state_counts(spec)[0] == 4

    def test_concrete_sizes_win(self):
        spec = SimpleNamespace(word_bitsize=16, key_word_bitsize=16, nbr_words=8,
                               key_nbr_words=8, default_version=None, versions=None)
        assert _effective_word_sizes(spec) == (16, 16)


class TestVersionedHexNormalize:
    def test_midori64_hex_splits_with_effective_sizes(self):
        wb, kwb = _effective_word_sizes(_midori_family())
        tvs = [{"plaintext": "0000000000000000", "key": "0" * 32, "output": "3c9cceda2bbd449a"}]
        out = _normalize_test_vectors(tvs, "blockcipher", wb, kwb)
        assert out[0][1] == [3, 12, 9, 12, 12, 14, 13, 10, 2, 11, 11, 13, 4, 4, 9, 10]
        assert len(out[0][0][0]) == 16 and len(out[0][0][1]) == 32


class TestDropCrossVariant:
    def test_drops_midori128_keeps_midori64(self):
        # Two 16-word 64-bit outputs (Midori64) + one 32-word 128-bit output (Midori128 split
        # into 4-bit cells at Midori64 sizing).
        v64a = [[[[0] * 16, [0] * 32], [1] * 16]]
        vectors = [
            [[[0] * 16, [0] * 32], [1] * 16],       # Midori64 shape
            [[[0] * 16, [0] * 32], list(range(16))],  # Midori64 shape
            [[[0] * 32, [0] * 32], [2] * 32],       # Midori128 plaintext+output shape
        ]
        kept, dropped = _drop_cross_variant_vectors(vectors, 16, 32, "blockcipher")
        assert dropped == 1 and len(kept) == 2
        assert all(len(tv[1]) == 16 for tv in kept)

    def test_keeps_all_when_none_match(self):
        vectors = [[[[0] * 32], [2] * 32], [[[0] * 32], [3] * 32]]
        kept, dropped = _drop_cross_variant_vectors(vectors, 16, 32, "blockcipher")
        assert dropped == 0 and len(kept) == 2

    def test_no_expected_size_is_noop(self):
        vectors = [[[[0] * 8], [1] * 8]]
        assert _drop_cross_variant_vectors(vectors, 0, 0, "blockcipher") == (vectors, 0)
