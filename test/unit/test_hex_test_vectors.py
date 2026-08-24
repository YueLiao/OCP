"""Deterministic hex -> word splitting for test vectors.

The LLM copies a paper's hex string verbatim; _hex_to_words does the mechanical split so
a miscount (Midori's 31/32-word outputs, a doubled variant) is impossible. These tests pin
that behavior and its wiring through _normalize_test_vectors.
"""
import pytest

from agent.skills.cipher_definition import _hex_to_words, _normalize_test_vectors


class TestHexToWords:
    def test_4bit_cells_midori(self):
        # Midori64 all-zero ciphertext, 16 four-bit cells.
        assert _hex_to_words("3c9cceda2bbd449a", 4) == \
            [3, 12, 9, 12, 12, 14, 13, 10, 2, 11, 11, 13, 4, 4, 9, 10]

    def test_8bit_words(self):
        assert _hex_to_words("00ff10", 8) == [0, 255, 16]

    def test_16bit_words_msb_first(self):
        assert _hex_to_words("0102aabb", 16) == [0x0102, 0xaabb]

    def test_32bit_words(self):
        assert _hex_to_words("0000000112345678", 32) == [1, 0x12345678]

    def test_1bit_lanes(self):
        assert _hex_to_words("a", 1) == [1, 0, 1, 0]

    def test_strips_prefix_whitespace_separators(self):
        assert _hex_to_words("0x00 ff_10", 8) == [0, 255, 16]

    def test_uppercase(self):
        assert _hex_to_words("ABCD", 16) == [0xABCD]

    def test_passthrough_non_string(self):
        # An already-split integer word list is returned unchanged.
        assert _hex_to_words([1, 2, 3], 8) == [1, 2, 3]

    def test_reject_non_hex(self):
        with pytest.raises(ValueError, match="not a hex string"):
            _hex_to_words("12zz", 8)

    def test_reject_empty(self):
        with pytest.raises(ValueError, match="empty"):
            _hex_to_words("0x", 8)

    def test_reject_ragged_length(self):
        # 3 hex digits = 12 bits is not a whole number of 8-bit words.
        with pytest.raises(ValueError, match="whole number"):
            _hex_to_words("abc", 8)


class TestNormalizeWithHex:
    def test_block_cipher_hex_fields(self):
        tvs = [{"plaintext": "00000000", "key": "0000000000000000", "output": "0102"}]
        out = _normalize_test_vectors(tvs, "blockcipher", word_bitsize=16, key_word_bitsize=16)
        assert out == [[[[0, 0], [0, 0, 0, 0]], [0x0102]]]

    def test_key_uses_its_own_word_size(self):
        # State words are 8-bit, key words are 16-bit; each field split by its own size.
        tvs = [{"plaintext": "0102", "key": "aabbccdd", "output": "0304"}]
        out = _normalize_test_vectors(tvs, "blockcipher", word_bitsize=8, key_word_bitsize=16)
        assert out == [[[[1, 2], [0xaabb, 0xccdd]], [3, 4]]]

    def test_permutation_hex(self):
        tvs = [{"input": "ff00", "output": "00ff"}]
        out = _normalize_test_vectors(tvs, "permutation", word_bitsize=8)
        assert out == [[[[255, 0]], [0, 255]]]

    def test_list_form_still_works(self):
        tvs = [[[[1, 2], [3, 4]], [5, 6]]]
        out = _normalize_test_vectors(tvs, "blockcipher", word_bitsize=8, key_word_bitsize=8)
        assert out == [[[[1, 2], [3, 4]], [5, 6]]]

    def test_malformed_hex_raises_not_dropped(self):
        # A bad KAT must be reported, never silently dropped.
        tvs = [{"plaintext": "00", "key": "00", "output": "zz"}]
        with pytest.raises(ValueError, match="Test vector 1"):
            _normalize_test_vectors(tvs, "blockcipher", word_bitsize=8, key_word_bitsize=8)

    def test_no_word_size_leaves_lists_untouched(self):
        # Backward compatible: without sizes, integer-list vectors pass through unchanged.
        tvs = [[[[1, 2]], [3, 4]]]
        assert _normalize_test_vectors(tvs, "permutation") == [[[[1, 2]], [3, 4]]]

    def test_bitsliced_word_size_1_splits_hex_into_bits(self):
        # A bit-sliced layout cipher (word_bitsize == 1) DOES split a hex vector into its bits
        # (MSB-first) - "ff" -> 8 ones, "00" -> 8 zeros.
        tvs = [{"input": "ff", "output": "00"}]
        out = _normalize_test_vectors(tvs, "permutation", word_bitsize=1)
        assert out == [[[[1] * 8], [0] * 8]]
