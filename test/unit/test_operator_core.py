import variables.variables as var
import pytest
from operators.boolean_operators import AND, ConstantXOR, NOT, N_XOR, OR, XOR
from operators.modular_operators import ConstantAdd, ModAdd, ModMul
from operators.operators import CopyOperator, Equal, NoneOperator, Rot, Shift
from operators.Sbox import AES_Sbox, PRESENT_Sbox, Sbox
from operators.matrix import (
    Matrix,
    gf2_inv,
    gf2_multiply,
    gf2_pow,
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
    assert op.generate_implementation("c", unroll=True) == ["out = in0 ^ in1;"]
    assert op.generate_implementation("verilog", unroll=True) == ["assign out = in0 ^ in1;"]

    op.model_version = "XOR_XORDIFF"
    model = op.generate_model("sat")

    assert "in0_0 in1_0 -out_0" in model
    assert "-in0_1 -in1_1 -out_1" in model


def test_xor_additional_differential_versions_have_stable_dummy_variables():
    left = var.Variable(2, ID="in0")
    right = var.Variable(2, ID="in1")
    out = var.Variable(2, ID="out")
    op = XOR([left, right], [out], ID="XOR")

    op.model_version = "XOR_XORDIFF_1"
    version_1 = op.generate_model("milp")
    assert "XOR_d_0" in "\n".join(version_1)
    assert "Binary\nin0_0 in1_0 out_0 XOR_d_0" in version_1
    assert "Binary\nin0_1 in1_1 out_1 XOR_d_1" in version_1

    op.model_version = "XOR_XORDIFF_2"
    version_2 = op.generate_model("milp")
    assert "XOR_d_1" in "\n".join(version_2)
    assert "in0_0 + in1_0 + out_0 - 2 XOR_d_0 = 0" in version_2
    assert "Binary\nin0_1 in1_1 out_1 XOR_d_1" in version_2


def test_nxor_generates_implementation_and_linear_models():
    inputs = [var.Variable(2, ID=f"in{i}") for i in range(3)]
    out = var.Variable(2, ID="out")
    op = N_XOR(inputs, [out], ID="2N_XOR")

    assert op.generate_implementation("python", unroll=True) == ["out = in0 ^ in1 ^ in2"]
    assert op.generate_implementation("c", unroll=True) == ["out = in0 ^ in1 ^ in2;"]
    assert op.generate_implementation("verilog", unroll=True) == ["assign out = in0 ^ in1 ^ in2;"]

    op.model_version = "N_XOR_LINEAR"
    assert op.generate_model("sat")[:6] == [
        "out_0 -in0_0",
        "-out_0 in0_0",
        "out_0 -in1_0",
        "-out_0 in1_0",
        "out_0 -in2_0",
        "-out_0 in2_0",
    ]
    assert op.generate_model("milp") == [
        "out_0 - in0_0 = 0",
        "out_0 - in1_0 = 0",
        "out_0 - in2_0 = 0",
        "out_1 - in0_1 = 0",
        "out_1 - in1_1 = 0",
        "out_1 - in2_1 = 0",
        "Binary\nin0_0 in0_1 in1_0 in1_1 in2_0 in2_1 out_0 out_1",
    ]

    op.model_version = "N_XOR_TRUNCATEDLINEAR"
    assert op.generate_model("sat") == [
        "out -in0",
        "-out in0",
        "out -in1",
        "-out in1",
        "out -in2",
        "-out in2",
    ]
    assert op.generate_model("milp") == [
        "out - in0 = 0",
        "out - in1 = 0",
        "out - in2 = 0",
        "Binary\nin0 in1 in2 out",
    ]


def test_operator_display_can_be_captured_without_printing(capsys):
    left = var.Variable(2, ID="in0")
    right = var.Variable(2, ID="in1")
    out = var.Variable(2, ID="out")
    op = XOR([left, right], [out], ID="XOR")
    captured = []

    assert left.format_display() == "ID: in0 / bitsize: 2 / value: Invalid representation"
    assert op.display(output_func=captured.append) == "XOR"

    assert "ID: XOR" in captured[0]
    assert "ID: in0" in captured[0]
    assert "ID: out" in captured[0]
    assert capsys.readouterr().out == ""


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


def test_and_or_share_stable_active_weight_models():
    for operator_cls in (AND, OR):
        left = var.Variable(2, ID="in0")
        right = var.Variable(2, ID="in1")
        out = var.Variable(2, ID="out")
        op = operator_cls([left, right], [out], ID=operator_cls.__name__)

        op.model_version = f"{operator_cls.__name__}_XORDIFF"
        sat_model = op.generate_model("sat")
        assert sat_model[:4] == [
            "in0_0 in1_0 -out_0",
            f"in0_0 in1_0 -{operator_cls.__name__}_p_0",
            f"-in0_0 {operator_cls.__name__}_p_0",
            f"-in1_0 {operator_cls.__name__}_p_0",
        ]
        assert op.weight == [f"{operator_cls.__name__}_p_0", f"{operator_cls.__name__}_p_1"]

        op.model_version = f"{operator_cls.__name__}_LINEAR"
        milp_model = op.generate_model("milp")
        assert f"{operator_cls.__name__}_p_0 - in0_0 >= 0" in milp_model
        assert f"{operator_cls.__name__}_p_1 - out_1 = 0" in milp_model
        assert op.weight == [f"{operator_cls.__name__}_p_0 + {operator_cls.__name__}_p_1"]


def test_bitwise_or_as_sbox_has_stable_ddt_and_lat():
    op = Sbox(
        [var.Variable(2, ID="in")],
        [var.Variable(1, ID="out")],
        input_bitsize=2,
        output_bitsize=1,
        ID="or_sbox",
    )
    op.table = [0, 1, 1, 1]

    assert op.computeDDT() == [[4, 0], [2, 2], [2, 2], [2, 2]]
    assert op.computeLAT() == [[4, -2], [0, 2], [0, 2], [0, 2]]


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
    sat_model = op.generate_model("sat")
    assert len(sat_model) == 17
    assert sat_model[:2] == [
        "in0_0 in1_0 -out_0 in0_1 in1_1 out_1",
        "in0_0 -in1_0 out_0 in0_1 in1_1 out_1",
    ]
    assert sat_model[-1] == "-in0_1 -in1_1 -out_1 -ADD_p_0"
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
        "out0_0 -in_0",
        "-out0_0 in_0",
        "out1_0 -in_0",
        "-out1_0 in_0",
        "out2_0 -in_0",
        "-out2_0 in_0",
    ]
    assert op.generate_model("milp") == [
        "out0_0 - in_0 = 0",
        "out1_0 - in_0 = 0",
        "out2_0 - in_0 = 0",
        "out0_1 - in_1 = 0",
        "out1_1 - in_1 = 0",
        "out2_1 - in_1 = 0",
        "Binary\nin_0 in_1 out0_0 out0_1 out1_0 out1_1 out2_0 out2_1",
    ]

    op.model_version = "CopyOperator_TRUNCATEDDIFF"
    assert op.generate_model("sat") == [
        "in -out0",
        "-in out0",
        "in -out1",
        "-in out1",
        "in -out2",
        "-in out2",
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


def test_unary_equivalence_operators_share_stable_models():
    left = var.Variable(2, ID="in0")
    out = var.Variable(2, ID="out")

    for op in (
        NOT([left], [out], ID="NOT"),
        ConstantXOR([left], [out], [[1]], round=1, index=0, ID="CX"),
    ):
        op.model_version = f"{op.__class__.__name__}_LINEAR"
        sat_model = op.generate_model("sat")
        assert sat_model == [
            "-in0_0 out_0",
            "in0_0 -out_0",
            "-in0_1 out_1",
            "in0_1 -out_1",
        ]

        milp_model = op.generate_model("milp")
        assert milp_model[:2] == ["in0_0 - out_0 = 0", "in0_1 - out_1 = 0"]
        assert milp_model[-1] == "Binary\nin0_0 in0_1 out_0 out_1"


def test_constant_xor_generates_stable_code_headers_and_truncated_models():
    left = var.Variable(2, ID="in")
    out = var.Variable(2, ID="out")
    op = ConstantXOR([left], [out], [[1, 2], [3, 4]], round=2, index=1, ID="CX")

    assert op.generate_implementation("python", unroll=True) == ["out = in ^ 0x4"]
    assert op.generate_implementation("c", unroll=True) == ["out = in ^ 0x4;"]
    assert op.generate_implementation("verilog", unroll=True) == ["assign out = in ^ 0x4;"]
    assert op.generate_implementation("python", unroll=False) == ["out = in ^ RC[i][1]"]
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

    op.model_version = "ConstantXOR_TRUNCATEDDIFF"
    assert op.generate_model("sat") == ["-in out", "in -out"]
    assert op.generate_model("milp") == ["in - out = 0", "Binary\nin out"]


def test_not_generates_stable_code_and_sbox_tables():
    left = var.Variable(2, ID="in")
    out = var.Variable(2, ID="out")
    op = NOT([left], [out], ID="NOT")

    assert op.generate_implementation("python", unroll=True) == ["out = in ^ 0x3"]
    assert op.generate_implementation("c", unroll=True) == ["out = in ^ 0x3;"]
    assert op.generate_implementation("verilog", unroll=True) == ["assign out = ~in;"]

    not_sbox = Sbox(
        [var.Variable(1, ID="in")],
        [var.Variable(1, ID="out")],
        input_bitsize=1,
        output_bitsize=1,
        ID="not_sbox",
    )
    not_sbox.table = [1, 0]

    assert not_sbox.computeDDT() == [[2, 0], [0, 2]]
    assert not_sbox.computeLAT() == [[2, 0], [0, -2]]


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
        "in_0 - in_0 = 0",
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
        "in_3 - in_3 = 0",
        "Binary\nin_0 in_1 in_2 in_3 out_0 out_1 out_2 out_3",
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


def test_present_sbox_code_generation_and_branch_numbers_are_stable():
    op = PRESENT_Sbox([var.Variable(4, ID="in")], [var.Variable(4, ID="out")], ID="S")

    assert op.is_bijective()
    assert op.differential_branch_number() == 3
    assert op.linear_branch_number() == 2
    assert op.generate_implementation("python", unroll=True) == ["out = PRESENT_Sbox[in]"]
    assert op.generate_implementation("c", unroll=True) == ["out = PRESENT_Sbox[in];"]
    assert op.generate_implementation_header("python") == [
        "PRESENT_Sbox = [12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2]",
    ]
    assert op.generate_implementation_header("c") == [
        "uint8_t PRESENT_Sbox[16] = {12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2};",
    ]


def test_present_sbox_bitsliced_code_generation_is_stable():
    op = PRESENT_Sbox(
        [var.Variable(1, ID=f"in{i}") for i in range(4)],
        [var.Variable(1, ID=f"out{i}") for i in range(4)],
        ID="Sbits",
    )

    assert op.generate_implementation("python", unroll=True) == [
        "x = (in0 << 3) | (in1 << 2) | (in2 << 1) | (in3 << 0)",
        "y = PRESENT_Sbox[x]",
        "out0, out1, out2, out3 = (y >> 3) & 1, (y >> 2) & 1, (y >> 1) & 1, (y >> 0) & 1",
    ]
    assert op.generate_implementation("c", unroll=True) == [
        "x = (in0 << 3) | (in1 << 2) | (in2 << 1) | (in3 << 0);",
        "y = PRESENT_Sbox[x];",
        "out0 = (y >> 3) & 1;",
        "out1 = (y >> 2) & 1;",
        "out2 = (y >> 1) & 1;",
        "out3 = (y >> 0) & 1;",
    ]
    assert op.generate_implementation_header("c") == [
        "uint8_t PRESENT_Sbox[16] = {12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2};",
        "uint8_t x;",
        "uint8_t y;",
    ]


def test_present_sbox_weighted_truth_tables_are_stable():
    op = PRESENT_Sbox([var.Variable(4, ID="in")], [var.Variable(4, ID="out")], ID="S")

    expected = {
        "ddt_to_truthtable_milp": (1024, 97, "10000000000000000000000000000000", "00000000000000000000000001000100"),
        "ddt_to_truthtable_sat": (2048, 97, "10000000000000000000000000000000", "00000000000000000001000000010000"),
        "lat_to_truthtable_milp": (1024, 133, "10000000000000000000000000000000", "00100010010000000010001000000000"),
        "lat_to_truthtable_sat": (1024, 133, "10000000000000000000000000000000", "00010001010000000001000100000000"),
    }

    for method_name, (length, active_count, prefix, suffix) in expected.items():
        truth_table = getattr(op, method_name)()
        assert len(truth_table) == length
        assert truth_table.count("1") == active_count
        assert truth_table[:32] == prefix
        assert truth_table[-32:] == suffix


def test_sbox_weight_helpers_and_aes_header_are_stable():
    present = PRESENT_Sbox([var.Variable(4, ID="in")], [var.Variable(4, ID="out")], ID="S")
    aes = AES_Sbox([var.Variable(8, ID="ain")], [var.Variable(8, ID="aout")], ID="AES")

    assert present.gen_weights(present.computeDDT()) == [3.0, 2.0]
    assert present.gen_integer_float_weight(present.computeLAT()) == ([1, 2], [])
    assert present.gen_weight_pattern_sat([1, 2], [0.5], 2.5) == [1, 1, 1]
    assert aes.is_bijective()
    assert aes.differential_branch_number() == 2
    assert aes.linear_branch_number() == 2
    assert aes.generate_implementation_header("c")[0].startswith(
        "uint8_t AES_Sbox[256] = {99, 124, 119, 123",
    )


def test_gf2_matrix_helpers_are_stable_and_return_mutable_copies():
    assert gf2_multiply(0x57, 0x83, 0x11B, 8) == 0xC1
    assert gf2_pow(2, 3, 0x11B, 8) == 8
    assert gf2_inv(0x53, 0x11B, 8) == 0xCA
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


def test_matrix_implementation_headers_and_zero_star_patterns_are_stable():
    inputs = [var.Variable(4, ID=f"in{i}") for i in range(2)]
    outputs = [var.Variable(4, ID=f"out{i}") for i in range(2)]
    op = Matrix("tiny_matrix", inputs, outputs, [[1, 1], [0, 1]], ID="M")

    assert op.generate_implementation("python", unroll=True) == ["(out0, out1) = tiny_matrix(in0, in1)"]
    assert op.generate_implementation("c", unroll=True) == ["tiny_matrix(in0, in1, out0, out1);"]
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
        "x1 -y1",
        "-x1 y1",
    ]

    op.model_version = "Matrix_LINEAR"
    assert op.generate_model("sat") == [
        "y0 -x0",
        "-y0 x0",
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


def test_matrix_truncated_fallback_warns_and_uses_runtime_files_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    inputs = [var.Variable(1, ID="x0"), var.Variable(1, ID="x1")]
    outputs = [var.Variable(1, ID="y0"), var.Variable(1, ID="y1")]
    op = Matrix("M", inputs, outputs, [[1, 1], [0, 1]], ID="M")
    op.model_version = "Matrix_TRUNCATEDDIFF"

    with pytest.warns(RuntimeWarning, match="differential branch number"):
        model = op.generate_model("sat", tool_type="minimize_logic")

    assert model
    assert op.model_filename.startswith(str(tmp_path / "matrix_modeling"))
    assert op.model_version == "Matrix_TRUNCATEDDIFF_2"
