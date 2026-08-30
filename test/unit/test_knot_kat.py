"""KNOT permutation KATs. `primitives/knot.py` now ships real per-version test vectors
(from files/knot_test_vectors.json, bit-exact vs the designer NIST-LWC reference C) instead
of `gen_test_vectors: pass`, so each width verifies end to end. This also locks in the KNOT-512
round-constant LFSR (d=7, taps [6,5]); an earlier build used d=8 and silently produced a wrong
512-bit permutation because no KAT ran.
"""
import io
from contextlib import redirect_stdout

import pytest
import implementations.implementations as imp
from tools.paths import get_files_dir

from primitives.knot import KNOT_PERMUTATION, KNOT_PERMUTATION_VERSIONS


@pytest.mark.parametrize("version", [256, 384, 512])
def test_knot_permutation_matches_designer_vectors(version):
    with redirect_stdout(io.StringIO()):
        cipher = KNOT_PERMUTATION(version=version)
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        vectors = cipher.test_vectors
        results = [(imp.evaluate_python(cipher, tv[0], output_len=None), tv[1]) for tv in vectors]

    assert vectors, f"KNOT-{version} carries no test vectors"
    for got, want in results:
        assert got == want


def test_knot_512_uses_7bit_round_constant_lfsr():
    # 2^7 = 128 covers the 100 rounds; d=8 was the bug the missing KAT hid.
    lfsr = KNOT_PERMUTATION_VERSIONS[512]["lfsr"]
    assert KNOT_PERMUTATION_VERSIONS[512]["d"] == 7
    assert lfsr["width"] == 7 and lfsr["taps"] == [6, 5]
