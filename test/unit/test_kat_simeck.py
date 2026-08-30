"""Simeck: fast, default-run known-answer test on the generated Python (unrolled)
implementation, across ALL versions. Versions that ship no test vectors are skipped
(visible), not silently passed. The heavy matrix (+ C backend, + rolled code) lives in the
gated test/implementations/ suite.

The all-version sweep surfaced two pre-existing primitive issues the gated suite never hit
(it only exercised v32 / [32,64]): the block cipher supports only [32,64] and [48,96], and
the 64-bit permutation shipped a wrong test vector (the model was correct, cross-checked
against the official block-cipher KAT and an independent reimplementation; the vector has
since been corrected).
"""
import io
from contextlib import redirect_stdout

import pytest

import implementations.implementations as imp
from tools.paths import get_files_dir

from primitives.simeck import SIMECK_PERMUTATION, SIMECK_BLOCKCIPHER


def _kat(cipher):
    if not cipher.test_vectors:
        pytest.skip(f"{cipher.name} ships no test vectors")
    with redirect_stdout(io.StringIO()):
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        for tv in cipher.test_vectors:
            assert imp.evaluate_python(cipher, tv[0], output_len=len(tv[1])) == tv[1]


@pytest.mark.parametrize("v", [32, 48, 64])
def test_simeck_permutation_kat(v):
    _kat(SIMECK_PERMUTATION(r=None, version=v))


@pytest.mark.parametrize("v", [[32, 64], [48, 96]])  # the only versions the constructor supports
def test_simeck_blockcipher_kat(v):
    _kat(SIMECK_BLOCKCIPHER(r=None, version=v))
