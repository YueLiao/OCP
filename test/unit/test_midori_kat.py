"""Midori64 and Midori128 built end to end from primitives/midori_claude.py and verified against
the designer's Appendix A test vectors (Banik et al., ASIACRYPT 2015).

Exercises the LED-style key handling for whitened ciphers: a static key (KEY_SCHEDULE
identity), and subkeys produced inside the SUBKEYS function. Midori64 alternates K0/K1 as
a round-dependent extraction and computes WK = K0 (+) K1 with an in-SUBKEYS XOR; Midori128
uses WK = K and RK_i = K (+) beta_i with four position-dependent 8-bit SSb S-boxes. Round
constants come from gen_rounds_constant_table (fractional hex of pi). The layout needs
unrolled code generation because the whitening and final rounds differ from the middle ones.
"""
import io
from contextlib import redirect_stdout

import pytest

import implementations.implementations as imp
import primitives.midori_claude as m
from tools.paths import get_files_dir


def _pack(cells, w):
    x = 0
    for v in cells:
        x = (x << w) | (v & ((1 << w) - 1))
    return x


def _build_and_eval(version, tv):
    w, out_len = (4, 64) if version == 64 else (8, 128)
    with redirect_stdout(io.StringIO()):
        cipher = m.MIDORI_BLOCKCIPHER(version=version)
        fd = get_files_dir(); fd.mkdir(parents=True, exist_ok=True)
        imp.generate_implementation(cipher, fd / f"Midori{version}.py", "python", True)  # round-dependent -> unroll
        out = imp.evaluate(cipher, [tv['plaintext'], tv['key']], output_len=out_len)
    return _pack(out[:16], w)


@pytest.mark.parametrize("version", [64, 128])
def test_midori_matches_designer_kats(version):
    w = 4 if version == 64 else 8
    with redirect_stdout(io.StringIO()):
        cipher = m.MIDORI_BLOCKCIPHER(version=version)
    tvs = cipher.test_vectors
    assert len(tvs) == 2
    for tv in tvs:
        got = _build_and_eval(version, tv)
        want = _pack(tv['output'], w)
        assert got == want, f"Midori{version}: got {got:x} want {want:x}"


def test_midori64_zero_vector_is_famous_value():
    got = _build_and_eval(64, {'plaintext': [0] * 16, 'key': [0] * 32})
    assert got == 0x3c9cceda2bbd449a  # paper Appendix A


def test_midori128_zero_vector_is_famous_value():
    got = _build_and_eval(128, {'plaintext': [0] * 16, 'key': [0] * 16})
    assert got == 0xc055cbb95996d14902b60574d5e728d6  # paper Appendix A
