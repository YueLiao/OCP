import variables.variables as var
import pytest
from operators.boolean_operators import AND, ConstantXOR, NOT, N_XOR, OR, XOR
from operators.modular_operators import ConstantAdd, ModAdd, ModMul
from operators.operators import Equal, Rot
from operators.Sbox import PRESENT_Sbox, Sbox
from operators.matrix import (
    Matrix,
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
