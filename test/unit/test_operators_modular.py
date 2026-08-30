"""Modular arithmetic operators in modular_operators.py: ModAdd, ModMul, ConstantAdd -
code generation and SAT/MILP model generation.
"""
import pytest

import variables.variables as var
from operators.modular_operators import ConstantAdd, ModAdd, ModMul


def test_modular_implementation_generation_is_stable():
    left = var.Variable(4, ID="in0")
    right = var.Variable(4, ID="in1")
    out = var.Variable(4, ID="out")
    modadd = ModAdd([left, right], [out], ID="ADD")

    assert modadd.generate_implementation("python", unroll=True) == [
        "out = (in0 + in1) & 0xf",
    ]
    assert modadd.generate_implementation("c", unroll=True) == [
        "out = (in0 + in1) & 0xf;",
    ]

    const_add = ConstantAdd([left], [out], [[3]], round=1, index=0, ID="CADD")
    assert const_add.generate_implementation("python", unroll=True) == [
        "out = (in0 + 0x3) & 0xf",
    ]
    assert const_add.generate_implementation("verilog", unroll=True) == [
        "assign out = in0 + 0x3;",
    ]


def test_modular_implementation_respects_explicit_non_word_modulo():
    left = var.Variable(4, ID="in0")
    right = var.Variable(4, ID="in1")
    out = var.Variable(4, ID="out")

    modadd = ModAdd([left, right], [out], modulo=5, ID="ADD")
    assert modadd.generate_implementation("python", unroll=True) == ["out = (in0 + in1) % 5"]
    assert modadd.generate_implementation("c", unroll=True) == ["out = (in0 + in1) % 5;"]

    modmul = ModMul([left, right], [out], modulo=5, ID="MUL")
    assert modmul.generate_implementation("python", unroll=True) == ["out = (in0 * in1) % 5"]
    assert modmul.generate_implementation("c", unroll=True) == ["out = (in0 * in1) % 5;"]


def test_constant_add_generates_headers_and_non_word_modulo_code():
    left = var.Variable(3, ID="in")
    out = var.Variable(3, ID="out")
    op = ConstantAdd([left], [out], [[1, 2], [3, 4]], round=2, index=1, modulo=5, ID="CADD")

    assert op.generate_implementation("python", unroll=True) == ["out = (in + 0x4) % 5"]
    assert op.generate_implementation("c", unroll=True) == ["out = (in + 0x4) % 5;"]
    assert op.generate_implementation("verilog", unroll=True) == ["assign out = (in + 0x4) % 5;"]
    assert op.generate_implementation("python", unroll=False) == ["out = (in + RC[i][1]) % 5"]
    assert op.generate_implementation_header("python") == ["#Constraints List\nRC=[[1, 2], [3, 4]]"]
    assert op.generate_implementation_header("c") == [
        "// Constraints List\nuint8_t RC[][2] = {\n    { 1, 2 }, { 3, 4 }\n};",
    ]
    assert op.generate_implementation_header("verilog") == [
        "// Constraints List\nreg [2:0] RC [0:1][0:1];",
        "initial begin",
        "    RC[0][0] = 3'h1;",
        "    RC[0][1] = 3'h2;",
        "    RC[1][0] = 3'h3;",
        "    RC[1][1] = 3'h4;",
        "end",
    ]


def test_modadd_xordiff_and_linear_models_keep_weight_variables_stable():
    left = var.Variable(2, ID="in0")
    right = var.Variable(2, ID="in1")
    out = var.Variable(2, ID="out")
    op = ModAdd([left, right], [out], ID="ADD")

    op.model_version = "ModAdd_XORDIFF"
    assert op.generate_model("sat") == [
        "in0_0 in1_0 -out_0 in0_1 in1_1 out_1",
        "in0_0 -in1_0 out_0 in0_1 in1_1 out_1",
        "-in0_0 in1_0 out_0 in0_1 in1_1 out_1",
        "-in0_0 -in1_0 -out_0 in0_1 in1_1 out_1",
        "in0_0 in1_0 out_0 -in0_1 -in1_1 -out_1",
        "in0_0 -in1_0 -out_0 -in0_1 -in1_1 -out_1",
        "-in0_0 in1_0 -out_0 -in0_1 -in1_1 -out_1",
        "-in0_0 -in1_0 out_0 -in0_1 -in1_1 -out_1",
        "in0_1 in1_1 -out_1",
        "in0_1 -in1_1 out_1",
        "-in0_1 in1_1 out_1",
        "-in0_1 -in1_1 -out_1",
        "-in0_1 out_1 ADD_p_0",
        "in1_1 -out_1 ADD_p_0",
        "in0_1 -in1_1 ADD_p_0",
        "in0_1 in1_1 out_1 -ADD_p_0",
        "-in0_1 -in1_1 -out_1 -ADD_p_0",
    ]
    assert op.weight == ["ADD_p_0"]

    milp_model = op.generate_model("milp")
    assert len(milp_model) == 19
    assert milp_model[0] == "in1_1 - out_1 + ADD_p_0 >= 0"
    assert milp_model[-1] == "Binary\nin0_0 in0_1 in1_0 in1_1 out_0 out_1 ADD_p_0 ADD_d"
    assert op.weight == ["ADD_p_0"]

    op.model_version = "ModAdd_LINEAR"
    linear_sat = op.generate_model("sat")
    assert len(linear_sat) == 17
    assert linear_sat[:2] == ["-ADD_p_0", "in0_0 in1_0 out_0 -ADD_p_1"]
    assert linear_sat[-1] == "-in1_1 out_1 ADD_p_1"
    assert op.weight == ["ADD_p_0", "ADD_p_1"]

    linear_milp = op.generate_model("milp")
    assert len(linear_milp) == 18
    assert linear_milp[0] == "ADD_p_0 = 0"
    assert linear_milp[-1] == "Binary\nin0_0 in0_1 in1_0 in1_1 out_0 out_1 ADD_p_0 ADD_p_1 ADD_p_2"
    assert op.weight == ["ADD_p_0 + ADD_p_1"]


def test_modadd_non_power_of_two_modulo_is_modelled():
    left = var.Variable(4, ID="in0")
    right = var.Variable(4, ID="in1")
    out = var.Variable(4, ID="out")
    op = ModAdd([left, right], [out], modulo=5, ID="A5")
    op.model_version = "ModAdd_XORDIFF"

    model = op.generate_model("sat")  # a non-power-of-two modulus is modelled, not just implemented
    assert isinstance(model, list) and len(model) == 43


def test_modmul_and_constant_add_have_no_differential_model():
    # ModMul and ConstantAdd generate code but have no SAT/MILP differential model implemented;
    # requesting one must fail loudly rather than silently returning an empty/wrong model.
    modmul = ModMul([var.Variable(2, ID="in0"), var.Variable(2, ID="in1")], [var.Variable(2, ID="out")], ID="MUL")
    modmul.model_version = "ModMul_XORDIFF"
    with pytest.raises(ValueError, match="not existing"):
        modmul.generate_model("sat")

    const_add = ConstantAdd([var.Variable(2, ID="in")], [var.Variable(2, ID="out")], [[1]], round=1, index=0, ID="CADD")
    const_add.model_version = "ConstantAdd_XORDIFF"
    with pytest.raises(ValueError, match="not existing"):
        const_add.generate_model("sat")


def test_modadd_rejects_unknown_model_version():
    op = ModAdd([var.Variable(2, ID="in0"), var.Variable(2, ID="in1")], [var.Variable(2, ID="out")], ID="ADD")
    op.model_version = "ModAdd_BOGUS"
    with pytest.raises(ValueError, match="not existing"):
        op.generate_model("sat")
