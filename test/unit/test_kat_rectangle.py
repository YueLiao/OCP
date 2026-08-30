"""RECTANGLE: fast, default-run known-answer test on the generated Python (unrolled)
implementation, across ALL versions. Versions that ship no test vectors are skipped
(visible), not silently passed. The heavy matrix (+ C backend, + rolled code) lives in the
gated test/implementations/ suite.
"""
import io
from contextlib import redirect_stdout

import pytest

import implementations.implementations as imp
from tools.paths import get_files_dir

from primitives.rectangle import RECTANGLE_PERMUTATION, RECTANGLE_BLOCKCIPHER


def _kat(cipher):
    if not cipher.test_vectors:
        pytest.skip(f"{cipher.name} ships no test vectors")
    with redirect_stdout(io.StringIO()):
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        for tv in cipher.test_vectors:
            assert imp.evaluate_python(cipher, tv[0], output_len=len(tv[1])) == tv[1]


def test_rectangle_permutation_kat():
    _kat(RECTANGLE_PERMUTATION(r=None))


@pytest.mark.parametrize("v", [[64, 80], [64, 128]])
def test_rectangle_blockcipher_kat(v):
    _kat(RECTANGLE_BLOCKCIPHER(r=None, version=v))
