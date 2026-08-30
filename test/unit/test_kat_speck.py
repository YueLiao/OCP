"""SPECK: fast, default-run known-answer test on the generated Python (unrolled)
implementation, across ALL versions. Versions that ship no test vectors are skipped
(visible), not silently passed. The heavy matrix (+ C backend, + rolled code) lives in the
gated test/implementations/ suite.
"""
import io
from contextlib import redirect_stdout

import pytest

import implementations.implementations as imp
from tools.paths import get_files_dir

from primitives.speck import SPECK_PERMUTATION, SPECK_BLOCKCIPHER


def _kat(cipher):
    if not cipher.test_vectors:
        pytest.skip(f"{cipher.name} ships no test vectors")
    with redirect_stdout(io.StringIO()):
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        for tv in cipher.test_vectors:
            assert imp.evaluate_python(cipher, tv[0], output_len=len(tv[1])) == tv[1]


@pytest.mark.parametrize("v", [32, 48, 64, 96, 128])
def test_speck_permutation_kat(v):
    _kat(SPECK_PERMUTATION(r=None, version=v))


@pytest.mark.parametrize("v", [[32, 64], [48, 72], [48, 96], [64, 96], [64, 128], [96, 96], [96, 144], [128, 128], [128, 192], [128, 256]])
def test_speck_blockcipher_kat(v):
    _kat(SPECK_BLOCKCIPHER(r=None, version=v))
