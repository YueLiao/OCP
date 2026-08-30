"""After a block cipher is verified, its keyless PERMUTATION (the round function with the key
removed) is derived and cross-checked against the block cipher run with all-zero keys. This must
work for cell_layout / bit-level ciphers like FUTURE/Midori - exactly the ones modeled bit-level
because the key schedule crosses cells - which the old derivation SILENTLY failed on (it built a
cell-layers-without-cell_layout spec and swallowed the exception, returning None). The KAT comes
from the block cipher, and failures are reported, never silent.
"""
import io
import sys
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_definition import (
    build_blockcipher_from_spec, derive_permutation, _spec_needs_unroll,
)

sys.path.insert(0, "test/unit")
from test_future_bitsliced import _future_cell_layout_spec, _to_bits  # noqa: E402


def _future_block_with_kat():
    spec = _future_cell_layout_spec()
    spec.test_vectors = [[[_to_bits(0x0123456789abcdef, 64), _to_bits(0x0, 128)],
                          _to_bits(0x298650c13199cdec, 64)]]
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python",
                                    _spec_needs_unroll(spec))
    return spec, cipher


def test_cell_layout_cipher_derives_a_verified_word_level_permutation():
    spec, cipher = _future_block_with_kat()
    perm_spec, perm_cipher, err = derive_permutation(spec, cipher)
    assert err is None                                   # not the old silent None
    assert perm_spec is not None and perm_cipher is not None
    assert perm_spec.test_vectors                        # KAT attached
    assert all(l.layer_type != "add_round_key" for l in perm_spec.round_structure)
    # FUTURE's bit-level block yields a WORD-LEVEL (4-bit cell) permutation, cross-checked
    assert perm_spec.word_bitsize == 4 and perm_spec.nbr_words == 16


def test_derived_permutation_kat_equals_block_cipher_with_zero_keys():
    spec, cipher = _future_block_with_kat()
    perm_spec, perm_cipher, err = derive_permutation(spec, cipher)
    assert err is None
    sample_in, kat_out = perm_spec.test_vectors[0]
    cb = perm_spec.word_bitsize
    with redirect_stdout(io.StringIO()):
        imp.generate_implementation(perm_cipher, get_files_dir() / f"{perm_cipher.name}.py",
                                    "python", _spec_needs_unroll(perm_spec))
        perm_out = imp.evaluate_python(perm_cipher, sample_in)
        # independent reference: the block cipher (all-zero key), plaintext repacked cells->bits
        pt_bits = [(v >> (cb - 1 - j)) & 1 for v in sample_in[0] for j in range(cb)]
        block_ref = imp.evaluate_python(cipher, [pt_bits, [0] * 128])
    out_bits = [(v >> (cb - 1 - j)) & 1 for v in perm_out for j in range(cb)]
    assert perm_out == kat_out          # perm reproduces its own KAT
    assert out_bits == block_ref        # and matches the bit-level block with zero keys


def test_derivation_failure_is_reported_not_silent():
    # a block "spec" that cannot build a permutation returns an error string, not a bare None pair
    class _Broken:
        versions = None
        def compile(self): return self          # the canonical lowering chain (no-op here)
        def to_permutation(self): raise ValueError("boom")
    result = derive_permutation(_Broken(), None)
    assert result[0] is None and isinstance(result[2], str) and "boom" in result[2]
