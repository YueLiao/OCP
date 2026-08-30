import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # this file -> test -> <ROOT>
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from itertools import product

import variables.variables as var
from operators.matrix import Matrix, generate_pmr_for_mds, generate_bin_matrix, gf2_multiply, _normalize_mod_poly
import tools.milp_search as milp_search
import tools.sat_search as sat_search
import solving.solving as solving

FILES_DIR = ROOT / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)

_LOG = sys.stdout

# Expected expanded binary matrices, keyed by operator ID.
EXPECTED_BINARY_MATRIX = {
    "Matrix_AES": [
        [0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
        [1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1],
        [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
        [1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        [1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        [1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
    ],
    "Matrix_FUTURE": [
        [1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1],
        [1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0],
        [0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0],
        [0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0],
        [1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
        [0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        [1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0],
        [1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1],
        [0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
        [0, 0, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0],
        [1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0],
        [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1],
        [0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0],
        [1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0],
        [0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0],
        [0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1],
    ],
    "Matrix_SKINNY64": [
        [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    ],
    "Matrix_SKINNY128": [
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
    ],
}


def log(*args):
    print(*args, file=_LOG)


def gen_aes_matrix_operator():
    # AES's 4x4 polynomial (GF(2^8)) MDS matrix.
    my_input = [var.Variable(8, ID="in" + str(i)) for i in range(4)]
    my_output = [var.Variable(8, ID="out" + str(i)) for i in range(4)]
    mat_aes = [[2, 3, 1, 1], [1, 2, 3, 1], [1, 1, 2, 3], [3, 1, 1, 2]]
    return Matrix("aes_matrix", my_input, my_output, mat=mat_aes, polynomial="0x1b", ID='Matrix_AES')


def gen_skinny64_matrix_operator():
    # SKINNY's 4x4 binary cell matrix (GF(2)) for 4-bit cells.
    my_input = [var.Variable(4, ID="in" + str(i)) for i in range(4)]
    my_output = [var.Variable(4, ID="out" + str(i)) for i in range(4)]
    mat_skinny = [[1, 0, 1, 1], [1, 0, 0, 0], [0, 1, 1, 0], [1, 0, 1, 0]]
    return Matrix("skinny64_matrix", my_input, my_output, mat=mat_skinny, ID='Matrix_SKINNY64')


def gen_skinny128_matrix_operator():
    # SKINNY's 4x4 binary cell matrix (GF(2)) for 8-bit cells.
    my_input = [var.Variable(8, ID="in" + str(i)) for i in range(4)]
    my_output = [var.Variable(8, ID="out" + str(i)) for i in range(4)]
    mat_skinny = [[1, 0, 1, 1], [1, 0, 0, 0], [0, 1, 1, 0], [1, 0, 1, 0]]
    return Matrix("skinny128_matrix", my_input, my_output, mat=mat_skinny, ID='Matrix_SKINNY128')


def gen_future_matrix_operator():
    # A FUTURE-style 4x4 polynomial (GF(2^4)) matrix.
    my_input = [var.Variable(4, ID="in" + str(i)) for i in range(4)]
    my_output = [var.Variable(4, ID="out" + str(i)) for i in range(4)]
    mat_future = [[8, 9, 1, 8], [3, 2, 9, 9], [2, 3, 8, 9], [9, 9, 8, 1]]
    return Matrix("mat_future", my_input, my_output, mat=mat_future, polynomial="0x3", ID='Matrix_FUTURE')


def expanded_matrix(op):
    """The bit-level GF(2) matrix, selected the same way Matrix._binary_matrix_representation does."""
    bitsize = op.input_vars[0].bitsize
    if op.polynomial is not None:
        m = generate_pmr_for_mds(op.mat, op.polynomial, bitsize)
    elif len(op.input_vars) == len(op.mat):
        m = generate_bin_matrix(op.mat, bitsize)
    else:
        m = op.mat
    return [[int(x) for x in row] for row in m]


def check_binary_matrix(op):
    # Assert the expanded binary matrix (see expanded_matrix) matches the expected baseline.
    binary_matrix = expanded_matrix(op)
    log("binary_matrix:")
    for row in binary_matrix:
        log(" ", row)
    expected = EXPECTED_BINARY_MATRIX.get(op.ID)
    assert expected is not None, f"no expected binary-matrix baseline for {op.ID}"
    assert binary_matrix == expected, f"{op.ID}: binary matrix mismatch\n got={binary_matrix}\n exp={expected}"


def _bit_name(word_var, bit, bitsize):
    # Matches _generate_bit_matrix_constraints: the '_l' suffix appears only when a word has >1 bit.
    return word_var.ID + ('_' + str(bit) if bitsize > 1 else '')


# --- implementation code -------------------------------------------------------------

def test_implementation(op):
    in_args = ", ".join(f"in{i}" for i in range(len(op.input_vars)))
    out_args = ", ".join(f"out{i}" for i in range(len(op.output_vars)))
    py = op.generate_implementation("python", unroll=True)
    c = op.generate_implementation("c", unroll=True)
    log("python:", py)
    log("c     :", c)
    assert py == [f"({out_args}) = {op.name}({in_args})"], f"python implementation: {py}"
    assert c == [f"{op.name}({in_args}, {out_args});"], f"c implementation: {c}"


# --- inverse over GF(2^m):  M * M^-1 == I --------------------------------------------

def test_inverse_over_gf2m(op):
    inv = op.inverse_over_gf2m()
    n = len(op.mat)
    degree = op.input_vars[0].bitsize
    mod = _normalize_mod_poly(op.polynomial, degree)
    product_mat = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            acc = 0
            for k in range(n):
                acc ^= gf2_multiply(op.mat[i][k], inv[k][j], mod, degree)
            product_mat[i][j] = acc
    identity = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    log("M^-1:", inv)
    assert product_mat == identity, f"{op.ID}: M * M^-1 != I, got {product_mat}"


# --- solution checks -----------------------------------------------------------------
# XORDIFF/LINEAR: each solution must satisfy the expanded binary matrix (out = M . in, or in = M^T . out).
# The full model has 2**(#bits) solutions, so those versions are solved to a capped sample.
# TRUNCATED_2: word-level, fully enumerable; the feasible pattern set is defined PER MATRIX.

_DIFF_LINEAR_SAMPLE = 2 ** 10


# SKINNY MixColumns is NOT MDS, so there is no simple branch-number rule; the feasible truncated
# word-activity patterns are enumerated explicitly below (34 per direction). Note this is the true
# model count for 4/8-bit cells (SKINNY-64 and -128 share the 4x4 word matrix); a naive 1-bit-per-cell
# enumeration would give only 16 and miss the cancellation freedom that wider cells allow.
# Each entry is (input_word_activity, output_word_activity).
SKINNY_TRUNCATEDDIFF = {
    ((0, 0, 0, 0), (0, 0, 0, 0)),
    ((0, 0, 0, 1), (1, 0, 0, 0)),
    ((0, 0, 1, 0), (1, 0, 1, 1)),
    ((0, 0, 1, 1), (0, 0, 1, 1)),
    ((0, 0, 1, 1), (1, 0, 1, 1)),
    ((0, 1, 0, 0), (0, 0, 1, 0)),
    ((0, 1, 0, 1), (1, 0, 1, 0)),
    ((0, 1, 1, 0), (1, 0, 0, 1)),
    ((0, 1, 1, 0), (1, 0, 1, 1)),
    ((0, 1, 1, 1), (0, 0, 0, 1)),
    ((0, 1, 1, 1), (0, 0, 1, 1)),
    ((0, 1, 1, 1), (1, 0, 0, 1)),
    ((0, 1, 1, 1), (1, 0, 1, 1)),
    ((1, 0, 0, 0), (1, 1, 0, 1)),
    ((1, 0, 0, 1), (0, 1, 0, 1)),
    ((1, 0, 0, 1), (1, 1, 0, 1)),
    ((1, 0, 1, 0), (0, 1, 1, 0)),
    ((1, 0, 1, 0), (1, 1, 1, 1)),
    ((1, 0, 1, 1), (0, 1, 1, 1)),
    ((1, 0, 1, 1), (1, 1, 1, 0)),
    ((1, 0, 1, 1), (1, 1, 1, 1)),
    ((1, 1, 0, 0), (1, 1, 1, 1)),
    ((1, 1, 0, 1), (0, 1, 1, 1)),
    ((1, 1, 0, 1), (1, 1, 1, 1)),
    ((1, 1, 1, 0), (0, 1, 0, 0)),
    ((1, 1, 1, 0), (0, 1, 1, 0)),
    ((1, 1, 1, 0), (1, 1, 0, 1)),
    ((1, 1, 1, 0), (1, 1, 1, 1)),
    ((1, 1, 1, 1), (0, 1, 0, 1)),
    ((1, 1, 1, 1), (0, 1, 1, 1)),
    ((1, 1, 1, 1), (1, 1, 0, 0)),
    ((1, 1, 1, 1), (1, 1, 0, 1)),
    ((1, 1, 1, 1), (1, 1, 1, 0)),
    ((1, 1, 1, 1), (1, 1, 1, 1)),
}

SKINNY_TRUNCATEDLINEAR = {
    ((0, 0, 0, 0), (0, 0, 0, 0)),
    ((0, 0, 0, 1), (1, 0, 0, 1)),
    ((0, 0, 1, 0), (0, 1, 0, 1)),
    ((0, 0, 1, 1), (1, 1, 0, 0)),
    ((0, 0, 1, 1), (1, 1, 0, 1)),
    ((0, 1, 0, 0), (0, 1, 1, 1)),
    ((0, 1, 0, 1), (1, 1, 1, 0)),
    ((0, 1, 0, 1), (1, 1, 1, 1)),
    ((0, 1, 1, 0), (0, 0, 1, 0)),
    ((0, 1, 1, 0), (0, 1, 1, 1)),
    ((0, 1, 1, 1), (1, 0, 1, 1)),
    ((0, 1, 1, 1), (1, 1, 1, 0)),
    ((0, 1, 1, 1), (1, 1, 1, 1)),
    ((1, 0, 0, 0), (0, 1, 0, 0)),
    ((1, 0, 0, 1), (1, 1, 0, 1)),
    ((1, 0, 1, 0), (0, 0, 0, 1)),
    ((1, 0, 1, 0), (0, 1, 0, 1)),
    ((1, 0, 1, 1), (1, 0, 0, 0)),
    ((1, 0, 1, 1), (1, 0, 0, 1)),
    ((1, 0, 1, 1), (1, 1, 0, 0)),
    ((1, 0, 1, 1), (1, 1, 0, 1)),
    ((1, 1, 0, 0), (0, 0, 1, 1)),
    ((1, 1, 0, 0), (0, 1, 1, 1)),
    ((1, 1, 0, 1), (1, 0, 1, 0)),
    ((1, 1, 0, 1), (1, 0, 1, 1)),
    ((1, 1, 0, 1), (1, 1, 1, 0)),
    ((1, 1, 0, 1), (1, 1, 1, 1)),
    ((1, 1, 1, 0), (0, 0, 1, 1)),
    ((1, 1, 1, 0), (0, 1, 1, 0)),
    ((1, 1, 1, 0), (0, 1, 1, 1)),
    ((1, 1, 1, 1), (1, 0, 1, 0)),
    ((1, 1, 1, 1), (1, 0, 1, 1)),
    ((1, 1, 1, 1), (1, 1, 1, 0)),
    ((1, 1, 1, 1), (1, 1, 1, 1)),
}


def truncated_feasible(op, model_version):
    """Expected feasible truncated word-activity patterns for this matrix and direction.

    AES / FUTURE MixColumns are MDS (branch number 5): feasible iff total active weight is 0 or >= 5.
    SKINNY MixColumns is not MDS: the feasible set is listed explicitly (SKINNY_TRUNCATED* above).
    """
    if op.ID in ("Matrix_AES", "Matrix_FUTURE"):
        n, m = len(op.input_vars), len(op.output_vars)
        return {(x, y) for x in product([0, 1], repeat=n) for y in product([0, 1], repeat=m)
                if (sum(x) + sum(y)) == 0 or (sum(x) + sum(y)) >= 5}
    if op.ID in ("Matrix_SKINNY64", "Matrix_SKINNY128"):
        return SKINNY_TRUNCATEDDIFF if "DIFF" in model_version else SKINNY_TRUNCATEDLINEAR
    raise AssertionError(f"no truncated reference defined for {op.ID}")


def _check_bit_relation(op, model_version, sol_list):
    mat = expanded_matrix(op)
    if "XORDIFF" in model_version:  # _XORDIFF: diffs propagate through the matrix
        source_vars, target_vars, M = op.input_vars, op.output_vars, mat
    else:  # _LINEAR: masks propagate through the transpose
        source_vars, target_vars, M = op.output_vars, op.input_vars, [list(r) for r in zip(*mat)]
    bps, bpt = source_vars[0].bitsize, target_vars[0].bitsize
    for sol in sol_list:
        for i in range(len(target_vars)):
            for j in range(bpt):
                row = M[bpt * i + j]
                acc = 0
                for k in range(len(source_vars)):
                    for l in range(bps):
                        if row[bps * k + l] == 1:
                            acc ^= round(float(sol[_bit_name(source_vars[k], l, bps)]))
                tgt = round(float(sol[_bit_name(target_vars[i], j, bpt)]))
                assert tgt == acc, f"{model_version}: target bit ({i},{j}) = {tgt}, expected {acc}"


def _check_truncated_patterns(op, model_version, sol_list):
    n, m = len(op.input_vars), len(op.output_vars)
    expected = truncated_feasible(op, model_version)
    got = set()
    for sol in sol_list:
        x = tuple(round(float(sol[op.get_var_model('in', i, bitwise=False)[0]])) for i in range(n))
        y = tuple(round(float(sol[op.get_var_model('out', i, bitwise=False)[0]])) for i in range(m))
        got.add((x, y))
    assert len(sol_list) == len(expected), f"{model_version}: {len(sol_list)} solutions, expected {len(expected)}"
    assert got == expected, f"{model_version}: solution set != expected feasible patterns"


def check_solutions(op, model_version, sol_list):
    # Auto-detect the analysis from the model_version.
    if "TRUNCATED" in model_version:
        _check_truncated_patterns(op, model_version, sol_list)
    else:  # bit-level XORDIFF / LINEAR
        assert sol_list, f"{model_version}: no solutions"
        _check_bit_relation(op, model_version, sol_list)


def _model_versions(op):
    name = op.__class__.__name__
    return [name + "_XORDIFF", name + "_LINEAR", name + "_TRUNCATEDDIFF_2", name + "_TRUNCATEDLINEAR_2"]


def test_milp_model(op):
    for model_version in _model_versions(op):
        op.model_version = model_version
        cap = 100000 if "TRUNCATED" in model_version else _DIFF_LINEAR_SAMPLE
        milp_constraints = op.generate_model(model_type='milp')
        log(f"MILP constraints with model_version={model_version}: \n", "\n".join(milp_constraints))
        filename = str(FILES_DIR / f"milp_{op.ID}_{model_version}.lp")
        milp_search.write_milp_model(constraints=milp_constraints, filename=filename)
        sol_list = solving.solve_milp(filename, {"solution_number": cap})
        log(f"Number of solutions: {len(sol_list)}")
        check_solutions(op, model_version, sol_list)


def test_sat_model(op):
    for model_version in _model_versions(op):
        op.model_version = model_version
        cap = 100000 if "TRUNCATED" in model_version else _DIFF_LINEAR_SAMPLE
        sat_constraints = op.generate_model(model_type='sat')
        log(f"SAT constraints with model_version={model_version}: \n", "\n".join(sat_constraints))
        filename = str(FILES_DIR / f"sat_{op.ID}_{model_version}.cnf")
        model = sat_search.write_sat_model(constraints=sat_constraints, filename=filename)
        sol_list = solving.solve_sat(filename, model["variable_map"], {"solution_number": cap})
        log(f"Number of solutions: {len(sol_list)}")
        check_solutions(op, model_version, sol_list)


def test_matrix(op):
    log(f"\n===== {op.ID} =====")
    op.display()
    test_implementation(op)
    check_binary_matrix(op)
    if op.polynomial is not None:
        test_inverse_over_gf2m(op)
    test_milp_model(op)
    test_sat_model(op)


if __name__ == '__main__':
    log_path = FILES_DIR / "test_aes_matrix_log.txt"
    with open(log_path, "w") as log_file:
        _LOG = log_file
        log("=== Matrix operator test log ===")
        test_matrix(gen_aes_matrix_operator())
        log("All matrix tests completed!")
    print(f"log written to {log_path}")


    log_path = FILES_DIR / "test_future_matrix_log.txt"
    with open(log_path, "w") as log_file:
        _LOG = log_file
        log("=== Matrix operator test log ===")
        test_matrix(gen_future_matrix_operator())
        log("All matrix tests completed!")
    print(f"log written to {log_path}")


    log_path = FILES_DIR / "test_skinny_matrix_log.txt"
    with open(log_path, "w") as log_file:
        _LOG = log_file
        log("=== Matrix operator test log ===")
        test_matrix(gen_skinny64_matrix_operator())
        test_matrix(gen_skinny128_matrix_operator())
        log("All matrix tests completed!")
    print(f"log written to {log_path}")
