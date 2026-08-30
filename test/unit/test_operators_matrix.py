"""Matrix operators in matrix.py: binary/word matrices, GF(2) helpers, MDS PMR
generation, polynomial matrices, and GF2 linear transforms - code generation and SAT/MILP
model generation. (The MDS-PMR mutable-copy test was moved here from
test_performance_regressions.)
"""
import shutil

import pytest

import variables.variables as var
from operators.matrix import (
    GF2Linear_Trans,
    Matrix,
    gf2_inv,
    gf2_multiply,
    gf2_pow,
    generate_binary_matrix_2,
    generate_pmr_for_mds,
    matrix_multiply_mod2,
)


def test_gf2_matrix_helpers_are_stable_and_return_mutable_copies():
    assert gf2_multiply(0x57, 0x83, 0x11B, 8) == 0xC1
    assert gf2_pow(2, 3, 0x11B, 8) == 8
    assert gf2_inv(0x53, 0x11B, 8) == 0xCA
    assert matrix_multiply_mod2([[1, 1], [0, 1]], [[1, 0], [1, 1]]) == [[0, 1], [1, 1]]

    pmr = generate_pmr_for_mds([[2, 3], [1, 1]], "0x1b", 8)
    pmr[0][0] = 99
    regenerated = generate_pmr_for_mds([[2, 3], [1, 1]], "0x1b", 8)

    assert len(regenerated) == 16
    assert len(regenerated[0]) == 16
    assert regenerated[0][0] != 99


def test_pmr_generation_populates_each_mds_block():
    degree = 8
    mod_poly = "0x1b"
    pmr = generate_pmr_for_mds([[2, 3], [1, 1]], mod_poly, degree)

    matrix2 = generate_binary_matrix_2(0x11B, degree)
    # multiply-by-3 = multiply-by-2 XOR identity (3 == 2 ^ 1 over GF(2))
    matrix3 = [[matrix2[i][j] ^ (1 if i == j else 0) for j in range(degree)] for i in range(degree)]

    assert pmr[0][:degree] == matrix2[0]
    assert pmr[0][degree:] == matrix3[0]


def test_matrix_implementation_headers_and_zero_star_patterns_are_stable():
    inputs = [var.Variable(4, ID=f"in{i}") for i in range(2)]
    outputs = [var.Variable(4, ID=f"out{i}") for i in range(2)]
    op = Matrix("tiny_matrix", inputs, outputs, [[1, 1], [0, 1]], ID="M")

    assert op.generate_implementation("python", unroll=True) == ["(out0, out1) = tiny_matrix(in0, in1)"]
    assert op.generate_implementation("c", unroll=True) == ["tiny_matrix(in0, in1, out0, out1);"]
    with pytest.raises(ValueError, match="unknown implementation type"):
        op.generate_implementation("rust")
    assert op.generate_implementation_header("python") == [
        "#Matrix Macro ",
        "def tiny_matrix(x0, x1):",
        "\ty0 = x0 ^ x1",
        "\ty1 = x1",
        "\treturn (y0, y1)",
    ]
    assert op.generate_implementation_header("c") == [
        "//Matrix Macro ",
        "#define tiny_matrix(x0, x1, y0, y1)  { \\",
        "\ty0 = x0 ^ x1; \\",
        "\ty1 = x1; \\",
        "} ",
    ]
    assert op.zero_star_io_patterns() == [
        (0, 0, 0, 0),
        (0, "*", "*", "*"),
        ("*", 0, "*", 0),
        ("*", "*", "*", "*"),
    ]

    forced_patterns = op.patterns_where_a_star_is_forced_zero()
    assert len(forced_patterns) == 15
    assert ((0, "*"), ("*", "*"), "0") in forced_patterns
    assert (("*", "*"), ("*", "*"), "0") in forced_patterns


def test_polynomial_matrix_headers_are_stable():
    inputs = [var.Variable(8, ID=f"in{i}") for i in range(2)]
    outputs = [var.Variable(8, ID=f"out{i}") for i in range(2)]
    op = Matrix("aes_matrix", inputs, outputs, [[2, 3], [1, 1]], polynomial="0x1b", ID="AESM")

    assert op.generate_implementation_header("python") == [
        "#Matrix Macro ",
        "def aes_matrix(x0, x1):",
        "\ty0 = GMUL(x0,2,0x1b,8) ^ GMUL(x1,3,0x1b,8)",
        "\ty1 = x0 ^ x1",
        "\treturn (y0, y1)",
    ]
    assert op.generate_implementation_header_unique("python")[0] == "#Galois Field Multiplication Macro"
    assert op.generate_implementation_header_unique("c")[0] == "//Galois Field Multiplication Macro"


@pytest.mark.skipif(shutil.which("espresso") is None, reason="espresso CLI not on PATH")
def test_gf2_linear_trans_code_generation_and_models_are_stable():
    op = GF2Linear_Trans(
        [var.Variable(3, ID="x")],
        [var.Variable(3, ID="y")],
        [[1, 1, 0], [0, 1, 1], [1, 0, 1]],
        ID="L",
        constants=[1, 0, 1],
    )

    assert op.generate_implementation("python", unroll=True) == [
        "y = ((((x >> 2) & 1) ^ ((x >> 1) & 1) ^ 1) << 2) | ((((x >> 1) & 1) ^ ((x >> 0) & 1)) << 1) | ((((x >> 2) & 1) ^ ((x >> 0) & 1) ^ 1) << 0)",
    ]
    assert op.generate_implementation("c", unroll=True) == [
        "y = (((x >> 2) & 1) ^ ((x >> 1) & 1) ^ 1) << 2 | (((x >> 1) & 1) ^ ((x >> 0) & 1)) << 1 | (((x >> 2) & 1) ^ ((x >> 0) & 1) ^ 1) << 0;",
    ]

    op.model_version = "GF2Linear_Trans_XORDIFF"
    assert op.generate_model("sat")[:4] == [
        "x_0 x_1 -y_0",
        "x_0 -x_1 y_0",
        "-x_0 x_1 y_0",
        "-x_0 -x_1 -y_0",
    ]
    assert op.generate_model("milp")[:5] == [
        "x_0 + x_1 - y_0 >= 0",
        "x_1 + y_0 - x_0 >= 0",
        "x_0 + y_0 - x_1 >= 0",
        "x_0 + x_1 + y_0 <= 2",
        "x_1 + x_2 - y_1 >= 0",
    ]

    op.model_version = "GF2Linear_Trans_LINEAR"
    assert op.generate_model("sat")[:4] == [
        "y_0 y_2 -x_0",
        "y_0 -y_2 x_0",
        "-y_0 y_2 x_0",
        "-y_0 -y_2 -x_0",
    ]


def test_gf2_linear_trans_rejects_non_square_matrix():
    with pytest.raises(ValueError, match="matrix should be square"):
        GF2Linear_Trans(
            [var.Variable(2, ID="x")],
            [var.Variable(2, ID="y")],
            [[1, 0, 1], [0, 1, 0]],
            ID="L",
        )


@pytest.mark.skipif(shutil.which("espresso") is None, reason="espresso CLI not on PATH")
def test_matrix_bit_models_share_stable_constraint_generation():
    inputs = [var.Variable(1, ID="x0"), var.Variable(1, ID="x1")]
    outputs = [var.Variable(1, ID="y0"), var.Variable(1, ID="y1")]
    op = Matrix("M", inputs, outputs, [[1, 1], [0, 1]], ID="M")

    op.model_version = "Matrix_XORDIFF"
    assert op.generate_model("sat") == [
        "x0 x1 -y0",
        "x0 -x1 y0",
        "-x0 x1 y0",
        "-x0 -x1 -y0",
        "-x1 y1",
        "x1 -y1",
    ]

    op.model_version = "Matrix_LINEAR"
    assert op.generate_model("sat") == [
        "-y0 x0",
        "y0 -x0",
        "y0 y1 -x1",
        "y0 -y1 x1",
        "-y0 y1 x1",
        "-y0 -y1 -x1",
    ]


def test_matrix_branch_number_placeholders_fail_explicitly():
    inputs = [var.Variable(1, ID="x0"), var.Variable(1, ID="x1")]
    outputs = [var.Variable(1, ID="y0"), var.Variable(1, ID="y1")]
    op = Matrix("M", inputs, outputs, [[1, 1], [0, 1]], ID="M")

    with pytest.raises(NotImplementedError, match="differential branch number"):
        op.differential_branch_number()

    with pytest.raises(NotImplementedError, match="linear branch number"):
        op.linear_branch_number()


def test_matrix_unknown_model_type_error_is_readable():
    inputs = [var.Variable(1, ID="x0"), var.Variable(1, ID="x1")]
    outputs = [var.Variable(1, ID="y0"), var.Variable(1, ID="y1")]
    op = Matrix("M", inputs, outputs, [[1, 1], [0, 1]], ID="M")
    op.model_version = "Matrix_XORDIFF"

    with pytest.raises(ValueError, match="unknown model type 'unknown' for Matrix_XORDIFF"):
        op.generate_model("unknown")


@pytest.mark.skipif(shutil.which("espresso") is None, reason="espresso CLI not on PATH")
def test_matrix_truncated_fallback_warns_and_uses_runtime_files_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    inputs = [var.Variable(1, ID="x0"), var.Variable(1, ID="x1")]
    outputs = [var.Variable(1, ID="y0"), var.Variable(1, ID="y1")]
    op = Matrix("M", inputs, outputs, [[1, 1], [0, 1]], ID="M")
    op.model_version = "Matrix_TRUNCATEDDIFF"

    # No branch-number model exists, so generate_model prints a fallback notice and models the exact
    # valid patterns (the _2 variant) without mutating self.model_version.
    model = op.generate_model("sat", tool_type="minimize_logic")

    assert model
    assert op.model_filename.startswith(str(tmp_path / "matrix_modeling"))
    assert op.model_version == "Matrix_TRUNCATEDDIFF"


def test_pmr_generation_cache_returns_mutable_copies():
    mds = [[2, 3], [1, 1]]

    pmr = generate_pmr_for_mds(mds, "0x1b", 8)
    pmr[0][0] = 99

    assert generate_pmr_for_mds(mds, "0x1b", 8)[0][0] != 99
