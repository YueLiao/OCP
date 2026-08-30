"""ASCON: fast, default-run known-answer test on the generated Python (unrolled)
implementation, across ALL versions. Versions that ship no test vectors are skipped
(visible), not silently passed. The heavy matrix (+ C backend, + rolled code) lives in the
gated test/implementations/ suite.
"""
import io
from contextlib import redirect_stdout

import pytest

import implementations.implementations as imp
from tools.paths import get_files_dir

from primitives.ascon import ASCON_PERMUTATION


def _kat(cipher):
    if not cipher.test_vectors:
        pytest.skip(f"{cipher.name} ships no test vectors")
    with redirect_stdout(io.StringIO()):
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        for tv in cipher.test_vectors:
            assert imp.evaluate_python(cipher, tv[0], output_len=len(tv[1])) == tv[1]


@pytest.mark.parametrize("v", [(3, 0), (3, 1), (12, 0), (12, 1)])
def test_ascon_permutation_kat(v):
    _kat(ASCON_PERMUTATION(r=v[0], represent_mode=v[1]))
