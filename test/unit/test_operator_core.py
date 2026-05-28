import variables.variables as var
from operators.boolean_operators import XOR
from operators.operators import Equal, Rot
from operators.Sbox import PRESENT_Sbox
from operators.matrix import (
    generate_binary_matrix_2,
    generate_binary_matrix_3,
    generate_pmr_for_mds,
    matrix_multiply_mod2,
    matrix_power_mod2,
)


def test_xor_generates_implementation_and_sat_xordiff_model():
    left = var.Variable(2, ID="in0")
    right = var.Variable(2, ID="in1")
    out = var.Variable(2, ID="out")
    op = XOR([left, right], [out], ID="XOR")

    assert op.generate_implementation("python", unroll=True) == ["out = in0 ^ in1"]

    op.model_version = "XOR_XORDIFF"
    model = op.generate_model("sat")

    assert "in0_0 in1_0 -out_0" in model
    assert "-in0_1 -in1_1 -out_1" in model


def test_xor_generates_milp_linear_model():
    left = var.Variable(2, ID="in0")
    right = var.Variable(2, ID="in1")
    out = var.Variable(2, ID="out")
    op = XOR([left, right], [out], ID="XOR")
    op.model_version = "XOR_LINEAR"

    model = op.generate_model("milp")

    assert "in0_0 - out_0 = 0" in model
    assert "in1_1 - out_1 = 0" in model
    assert any(line.startswith("Binary\n") for line in model)


def test_equal_generates_sat_equivalence_model():
    left = var.Variable(2, ID="in0")
    out = var.Variable(2, ID="out")
    op = Equal([left], [out], ID="EQ")
    op.model_version = "Equal_XORDIFF"

    assert op.generate_model("sat") == [
        "-in0_0 out_0",
        "in0_0 -out_0",
        "-in0_1 out_1",
        "in0_1 -out_1",
    ]


def test_rot_generates_implementation_and_sat_model():
    left = var.Variable(2, ID="in0")
    out = var.Variable(2, ID="out")
    op = Rot([left], [out], "r", 1, ID="ROT")

    assert op.generate_implementation("python", unroll=True) == ["out = ROTR(in0, 1, 2)"]

    op.model_version = "Rot_XORDIFF"
    assert op.generate_model("sat") == [
        "-in0_0 out_1",
        "in0_0 -out_1",
        "-in0_1 out_0",
        "in0_1 -out_0",
    ]


def test_present_sbox_ddt_lat_and_truth_tables_are_stable():
    op = PRESENT_Sbox([var.Variable(4, ID="in")], [var.Variable(4, ID="out")], ID="S")

    assert op.computeDDT()[0] == [16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    assert op.computeDDT()[1] == [0, 0, 0, 4, 0, 0, 0, 4, 0, 4, 0, 0, 0, 4, 0, 0]
    assert op.computeLAT()[0] == [16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    assert op.computeLAT()[1] == [0, 0, 0, 0, 0, -8, 0, -8, 0, 0, 0, 0, 0, -8, 0, 8]

    ddt_truth = op.star_ddt_to_truthtable()
    lat_truth = op.star_lat_to_truthtable()

    assert len(ddt_truth) == 256
    assert ddt_truth.count("1") == 97
    assert len(lat_truth) == 256
    assert lat_truth.count("1") == 133


def test_gf2_matrix_helpers_are_stable_and_return_mutable_copies():
    assert matrix_multiply_mod2([[1, 1], [0, 1]], [[1, 0], [1, 1]]) == [[0, 1], [1, 1]]
    assert matrix_power_mod2([[0, 1], [1, 1]], 3) == [[1, 0], [0, 1]]

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
    matrix3 = generate_binary_matrix_3(0x11B, degree)

    assert pmr[0][:degree] == matrix2[0]
    assert pmr[0][degree:] == matrix3[0]
