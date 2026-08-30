import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from primitives.simeck import SIMECK_PERMUTATION, SIMECK_BLOCKCIPHER
# Alias on import: the OCP helpers start with "test_", so importing them under their own
# names makes pytest collect them as (fixture-less, erroring) test functions.
from OCP import test_python_unrolled_imp as run_python_unrolled_imp
from OCP import test_visualisation as run_visualisation

# Simeck permutation widths.
SIMECK_PERMUTATION_VERSIONS = [32, 48, 64]
# Simeck block cipher versions the constructor supports ([64, 128] is not implemented).
SIMECK_BLOCKCIPHER_VERSIONS = [[32, 64], [48, 96]]


def test_imp_simeck_permutation():
    for version in SIMECK_PERMUTATION_VERSIONS:
        cipher = SIMECK_PERMUTATION(r=None, version=version)

        run_python_unrolled_imp(cipher)

        run_visualisation(cipher)


def test_imp_simeck_blockcipher():
    for version in SIMECK_BLOCKCIPHER_VERSIONS:
        cipher = SIMECK_BLOCKCIPHER(r=None, version=version)

        run_python_unrolled_imp(cipher)

        run_visualisation(cipher)


if __name__ == "__main__":
    print(f"=== Implementation Test Log ===")

    test_imp_simeck_permutation()
    test_imp_simeck_blockcipher()

    print("All implementation tests completed!")
