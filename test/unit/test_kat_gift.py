"""GIFT: fast, default-run known-answer test on the generated Python (unrolled)
implementation, across ALL versions. Versions that ship no test vectors are skipped
(visible), not silently passed. The heavy matrix (+ C backend, + rolled code) lives in the
gated test/implementations/ suite.
"""
import io
from contextlib import redirect_stdout

import pytest

import implementations.implementations as imp
from tools.paths import get_files_dir

from primitives.gift import GIFT_PERMUTATION, GIFT_BLOCKCIPHER


def _kat(cipher):
    if not cipher.test_vectors:
        pytest.skip(f"{cipher.name} ships no test vectors")
    with redirect_stdout(io.StringIO()):
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        for tv in cipher.test_vectors:
            assert imp.evaluate_python(cipher, tv[0], output_len=len(tv[1])) == tv[1]


@pytest.mark.parametrize("v", [64, 128])
def test_gift_permutation_kat(v):
    _kat(GIFT_PERMUTATION(r=None, version=v))


@pytest.mark.parametrize("v", [[64, 128], [128, 128]])
def test_gift_blockcipher_kat(v):
    _kat(GIFT_BLOCKCIPHER(r=None, version=v))
