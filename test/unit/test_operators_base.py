"""Base operator classes in operators.py: Equal, Copy, None, Rot, Shift, and the
Operator.display base method. (Boolean/arithmetic/matrix/S-box families live in the
sibling test_operators_* files.)
"""
import pytest

import variables.variables as var
from operators.operators import CopyOperator, Equal, NoneOperator, Rot, Shift
from operators.boolean_operators import XOR  # a vehicle for the base Operator.display test


def test_operator_display_can_be_captured_without_printing(capsys):
    left = var.Variable(2, ID="in0")
    right = var.Variable(2, ID="in1")
    out = var.Variable(2, ID="out")
    op = XOR([left, right], [out], ID="XOR")
    captured = []

    assert left.format_display() == "ID: in0 / bitsize: 2 / value: None"
    assert op.display(output_func=captured.append) == "XOR"

    assert "ID: XOR" in captured[0]
    assert "ID: in0" in captured[0]
    assert "ID: out" in captured[0]
    assert capsys.readouterr().out == ""


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

    with pytest.raises(Exception, match="unknown in_out type"):
        op.get_var_model("bad", 0)


def test_equal_generates_implementation_and_milp_equivalence_model():
    left = var.Variable(2, ID="in0")
    out = var.Variable(2, ID="out")
    op = Equal([left], [out], ID="EQ")

    assert op.generate_implementation("python", unroll=True) == ["out = in0"]
    assert op.generate_implementation("c", unroll=True) == ["out = in0;"]

    op.model_version = "Equal_XORDIFF"
    assert op.generate_model("milp") == [
        "in0_0 - out_0 = 0",
        "in0_1 - out_1 = 0",
        "Binary\nin0_0 in0_1 out_0 out_1",
    ]


def test_copy_operator_generates_implementation_and_models():
    left = var.Variable(2, ID="in")
    outputs = [var.Variable(2, ID=f"out{i}") for i in range(3)]
    op = CopyOperator([left], outputs, ID="COPY")

    assert op.generate_implementation("python", unroll=True) == ["out0 = in", "out1 = in", "out2 = in"]
    assert op.generate_implementation("c", unroll=True) == ["out0 = in;", "out1 = in;", "out2 = in;"]
    assert op.generate_implementation("verilog", unroll=True) == [
        "assign out0 = in;",
        "assign out1 = in;",
        "assign out2 = in;",
    ]

    op.model_version = "CopyOperator_XORDIFF"
    assert op.generate_model("sat")[:6] == [
        "-out0_0 in_0",
        "out0_0 -in_0",
        "-out0_1 in_1",
        "out0_1 -in_1",
        "-out1_0 in_0",
        "out1_0 -in_0",
    ]
    assert op.generate_model("milp") == [
        "out0_0 - in_0 = 0",
        "out0_1 - in_1 = 0",
        "out1_0 - in_0 = 0",
        "out1_1 - in_1 = 0",
        "out2_0 - in_0 = 0",
        "out2_1 - in_1 = 0",
        "Binary\nin_0 in_1 out0_0 out0_1 out1_0 out1_1 out2_0 out2_1",
    ]

    op.model_version = "CopyOperator_TRUNCATEDDIFF"
    assert op.generate_model("sat") == [
        "-out0 in",
        "out0 -in",
        "-out1 in",
        "out1 -in",
        "-out2 in",
        "out2 -in",
    ]
    assert op.generate_model("milp") == [
        "out0 - in = 0",
        "out1 - in = 0",
        "out2 - in = 0",
        "Binary\nin out0 out1 out2",
    ]


def test_none_operator_is_empty_placeholder():
    op = NoneOperator([], [], ID="NONE")

    assert op.generate_implementation("python", unroll=True) == []
    assert op.generate_model("sat") == []


def test_rot_generates_implementation_and_sat_model():
    left = var.Variable(2, ID="in0")
    out = var.Variable(2, ID="out")
    op = Rot([left], [out], "r", 1, ID="ROT")

    assert op.generate_implementation("python", unroll=True) == ["out = ROTR(in0, 1, 2)"]
    assert op.generate_implementation("c", unroll=True) == ["out = ROTR(in0, 1, 2);"]
    assert op.generate_implementation("verilog", unroll=True) == ["assign out = `ROTR(in0, 1, 2);"]

    op.model_version = "Rot_XORDIFF"
    assert op.generate_model("sat") == [
        "-in0_0 out_1",
        "in0_0 -out_1",
        "-in0_1 out_0",
        "in0_1 -out_0",
    ]


def test_rot_left_and_right_models_are_stable_for_word_size_four():
    left = var.Variable(4, ID="in")
    out = var.Variable(4, ID="out")

    left_rot = Rot([left], [out], "l", 1, ID="Rot")
    assert left_rot.generate_implementation("python", unroll=True) == ["out = ROTL(in, 1, 4)"]
    left_rot.model_version = "Rot_XORDIFF"
    assert left_rot.generate_model("milp") == [
        "in_1 - out_0 = 0",
        "in_2 - out_1 = 0",
        "in_3 - out_2 = 0",
        "in_0 - out_3 = 0",
        "Binary\nin_0 in_1 in_2 in_3 out_0 out_1 out_2 out_3",
    ]

    right_rot = Rot([left], [out], "r", 1, ID="Rot")
    assert right_rot.generate_implementation("python", unroll=True) == ["out = ROTR(in, 1, 4)"]
    right_rot.model_version = "Rot_XORDIFF"
    assert right_rot.generate_model("milp") == [
        "in_0 - out_1 = 0",
        "in_1 - out_2 = 0",
        "in_2 - out_3 = 0",
        "in_3 - out_0 = 0",
        "Binary\nin_0 in_1 in_2 in_3 out_0 out_1 out_2 out_3",
    ]


def test_shift_left_and_right_models_are_stable_for_word_size_four():
    left = var.Variable(4, ID="in")
    out = var.Variable(4, ID="out")

    left_shift = Shift([left], [out], "l", 1, ID="Shift")
    assert left_shift.generate_implementation("python", unroll=True) == ["out = (in << 1) & (2**4 - 1)"]
    assert left_shift.generate_implementation("c", unroll=True) == ["out = (in << 1) & ((1<<4) - 1);"]
    assert left_shift.generate_implementation("verilog", unroll=True) == [
        "assign out = (in << 1) & ((1<<4) - 1);",
    ]
    left_shift.model_version = "Shift_XORDIFF"
    assert left_shift.generate_model("sat") == [
        "in_0 -in_0",
        "-in_1 out_0",
        "in_1 -out_0",
        "-in_2 out_1",
        "in_2 -out_1",
        "-in_3 out_2",
        "in_3 -out_2",
        "-out_3",
    ]
    assert left_shift.generate_model("milp") == [
        "in_1 - out_0 = 0",
        "in_2 - out_1 = 0",
        "in_3 - out_2 = 0",
        "out_3 = 0",
        "Binary\nin_0 in_1 in_2 in_3 out_0 out_1 out_2 out_3",
    ]

    right_shift = Shift([left], [out], "r", 1, ID="Shift")
    assert right_shift.generate_implementation("python", unroll=True) == ["out = (in >> 1) & (2**4 - 1)"]
    right_shift.model_version = "Shift_XORDIFF"
    assert right_shift.generate_model("sat") == [
        "-out_0",
        "-in_0 out_1",
        "in_0 -out_1",
        "-in_1 out_2",
        "in_1 -out_2",
        "-in_2 out_3",
        "in_2 -out_3",
        "in_3 -in_3",
    ]
    assert right_shift.generate_model("milp") == [
        "out_0 = 0",
        "in_0 - out_1 = 0",
        "in_1 - out_2 = 0",
        "in_2 - out_3 = 0",
        "Binary\nin_0 in_1 in_2 in_3 out_0 out_1 out_2 out_3",
    ]

    left_shift.model_version = "Shift_LINEAR"
    assert left_shift.generate_model("sat") == [
        "-in_0",
        "-in_1 out_0",
        "in_1 -out_0",
        "-in_2 out_1",
        "in_2 -out_1",
        "-in_3 out_2",
        "in_3 -out_2",
        "out_3 -out_3",
    ]
    assert left_shift.generate_model("milp") == [
        "in_0 = 0",
        "in_1 - out_0 = 0",
        "in_2 - out_1 = 0",
        "in_3 - out_2 = 0",
        "Binary\nin_0 in_1 in_2 in_3 out_0 out_1 out_2 out_3",
    ]

    right_shift.model_version = "Shift_LINEAR"
    assert right_shift.generate_model("sat") == [
        "out_0 -out_0",
        "-in_0 out_1",
        "in_0 -out_1",
        "-in_1 out_2",
        "in_1 -out_2",
        "-in_2 out_3",
        "in_2 -out_3",
        "-in_3",
    ]
    assert right_shift.generate_model("milp") == [
        "in_0 - out_1 = 0",
        "in_1 - out_2 = 0",
        "in_2 - out_3 = 0",
        "in_3 = 0",
        "Binary\nin_0 in_1 in_2 in_3 out_0 out_1 out_2 out_3",
    ]
