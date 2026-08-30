"""Bitwise boolean operators in boolean_operators.py: XOR / n-XOR / AND / OR / NOT /
ANDXOR / ConstantXOR - their code generation and SAT/MILP model generation.
"""
import pytest

import variables.variables as var
from operators.boolean_operators import AND, ANDXOR, ConstantXOR, NOT, N_XOR, OR, XOR
from operators.Sbox import Sbox  # NOT's DDT/LAT is checked via a 1-bit S-box


def test_xor_generates_implementation_and_sat_xordiff_model():
    left = var.Variable(2, ID="in0")
    right = var.Variable(2, ID="in1")
    out = var.Variable(2, ID="out")
    op = XOR([left, right], [out], ID="XOR")

    assert op.generate_implementation("python", unroll=True) == ["out = in0 ^ in1"]
    assert op.generate_implementation("c", unroll=True) == ["out = in0 ^ in1;"]
    assert op.generate_implementation("verilog", unroll=True) == ["assign out = in0 ^ in1;"]

    op.model_version = "XOR_XORDIFF"
    assert op.generate_model("sat") == [
        "in0_0 in1_0 -out_0",
        "in0_0 -in1_0 out_0",
        "-in0_0 in1_0 out_0",
        "-in0_0 -in1_0 -out_0",
        "in0_1 in1_1 -out_1",
        "in0_1 -in1_1 out_1",
        "-in0_1 in1_1 out_1",
        "-in0_1 -in1_1 -out_1",
    ]


def test_xor_additional_differential_versions_have_stable_dummy_variables():
    left = var.Variable(2, ID="in0")
    right = var.Variable(2, ID="in1")
    out = var.Variable(2, ID="out")
    op = XOR([left, right], [out], ID="XOR")

    op.model_version = "XOR_XORDIFF_1"
    version_1 = op.generate_model("milp")
    assert "XOR_d_0" in "\n".join(version_1)
    assert "Binary\nin0_0 in0_1 in1_0 in1_1 out_0 out_1 XOR_d_0 XOR_d_1" in version_1

    op.model_version = "XOR_XORDIFF_2"
    version_2 = op.generate_model("milp")
    assert "XOR_d_1" in "\n".join(version_2)
    assert "in0_0 + in1_0 + out_0 - 2 XOR_d_0 = 0" in version_2
    assert "Binary\nin0_0 in0_1 in1_0 in1_1 out_0 out_1 XOR_d_0 XOR_d_1" in version_2


def test_nxor_generates_implementation_and_linear_models():
    inputs = [var.Variable(2, ID=f"in{i}") for i in range(3)]
    out = var.Variable(2, ID="out")
    op = N_XOR(inputs, [out], ID="2N_XOR")

    assert op.generate_implementation("python", unroll=True) == ["out = in0 ^ in1 ^ in2"]
    assert op.generate_implementation("c", unroll=True) == ["out = in0 ^ in1 ^ in2;"]
    assert op.generate_implementation("verilog", unroll=True) == ["assign out = in0 ^ in1 ^ in2;"]

    op.model_version = "N_XOR_LINEAR"
    assert op.generate_model("sat")[:6] == [
        "-out_0 in0_0",
        "out_0 -in0_0",
        "-out_1 in0_1",
        "out_1 -in0_1",
        "-out_0 in1_0",
        "out_0 -in1_0",
    ]
    assert op.generate_model("milp") == [
        "out_0 - in0_0 = 0",
        "out_1 - in0_1 = 0",
        "out_0 - in1_0 = 0",
        "out_1 - in1_1 = 0",
        "out_0 - in2_0 = 0",
        "out_1 - in2_1 = 0",
        "Binary\nin0_0 in0_1 in1_0 in1_1 in2_0 in2_1 out_0 out_1",
    ]

    op.model_version = "N_XOR_TRUNCATEDLINEAR"
    assert op.generate_model("sat") == [
        "-out in0",
        "out -in0",
        "-out in1",
        "out -in1",
        "-out in2",
        "out -in2",
    ]
    assert op.generate_model("milp") == [
        "out - in0 = 0",
        "out - in1 = 0",
        "out - in2 = 0",
        "Binary\nin0 in1 in2 out",
    ]

    op.model_version = "N_XOR_XORDIFF"  # differential = parity relation (sum of inputs + output is even)
    assert op.generate_model("sat")[:6] == [
        "-out_0 in0_0 in1_0 in2_0",
        "out_0 -in0_0 in1_0 in2_0",
        "out_0 in0_0 -in1_0 in2_0",
        "out_0 in0_0 in1_0 -in2_0",
        "-out_0 -in0_0 -in1_0 in2_0",
        "-out_0 -in0_0 in1_0 -in2_0",
    ]
    assert op.generate_model("milp") == [
        "in0_0 + in1_0 + in2_0 + out_0 - 2 2N_XOR_d_0 = 0",
        "2N_XOR_d_0 >= 0",
        "2N_XOR_d_0 <= 2",
        "in0_1 + in1_1 + in2_1 + out_1 - 2 2N_XOR_d_1 = 0",
        "2N_XOR_d_1 >= 0",
        "2N_XOR_d_1 <= 2",
        "Binary\nin0_0 in0_1 in1_0 in1_1 in2_0 in2_1 out_0 out_1",
        "Integer\n2N_XOR_d_0 2N_XOR_d_1",
    ]


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

        name = operator_cls.__name__
        op.model_version = f"{name}_XORDIFF"
        assert op.generate_model("sat") == [
            f"-in0_0 {name}_p_0",
            f"-in1_0 {name}_p_0",
            f"-{name}_p_0 in0_0 in1_0",
            f"-out_0 {name}_p_0",
            f"-in0_1 {name}_p_1",
            f"-in1_1 {name}_p_1",
            f"-{name}_p_1 in0_1 in1_1",
            f"-out_1 {name}_p_1",
        ]
        assert op.weight == [f"{name}_p_0", f"{name}_p_1"]

        op.model_version = f"{operator_cls.__name__}_LINEAR"
        milp_model = op.generate_model("milp")
        assert f"{operator_cls.__name__}_p_0 - in0_0 >= 0" in milp_model
        assert f"{operator_cls.__name__}_p_1 - out_1 = 0" in milp_model
        assert op.weight == [f"{operator_cls.__name__}_p_0 + {operator_cls.__name__}_p_1"]


def test_andxor_generates_implementation_and_milp_versions():
    inputs = [var.Variable(2, ID=name) for name in ("a", "b", "c")]
    out = var.Variable(2, ID="out")
    op = ANDXOR(inputs, [out], ID="AX")

    assert op.generate_implementation("python", unroll=True) == ["out = (a & b) ^ c"]
    assert op.generate_implementation("c", unroll=True) == ["out = (a & b) ^ c;"]
    assert op.generate_implementation("verilog", unroll=True) == ["assign out = (a & b) ^ c;"]

    expected_prefixes = {
        "ANDXOR_XORDIFF": [
            "AX_p_0 - a_0 >= 0",
            "AX_p_0 - b_0 >= 0",
            "a_0 + b_0 - AX_p_0 >= 0",
            "a_0 + b_0 + c_0 - out_0 >= 0",
        ],
        "ANDXOR_XORDIFF_1": [
            "AX_p_0 - a_0 >= 0",
            "AX_p_0 - b_0 >= 0",
            "a_0 + b_0 - AX_p_0 >= 0",
            "out_0 - c_0 + AX_p_0 >= 0",
        ],
        "ANDXOR_XORDIFF_2": [
            "AX_p_0 = 0 -> a_0 = 0",
            "AX_p_0 = 0 -> b_0 = 0",
            "AX_p_0 = 0 -> c_0 - out_0 = 0",
            "AX_p_0 = 1 -> a_0 + b_0 >= 1",
        ],
        "ANDXOR_XORDIFF_3": [
            "AX_p_0 = 0 -> a_0 = 0",
            "AX_p_0 = 0 -> b_0 = 0",
            "AX_p_0 = 0 -> c_0 - out_0 = 0",
            "AX_p_0 - a_0 - b_0 <= 0",
        ],
    }

    for model_version, prefix in expected_prefixes.items():
        op.model_version = model_version
        model = op.generate_model("milp")

        assert model[:4] == prefix
        assert model[-1] == "Binary\na_0 a_1 b_0 b_1 c_0 c_1 out_0 out_1 AX_p_0 AX_p_1"
        assert op.weight == ["AX_p_0 + AX_p_1"]

    op.model_version = "ANDXOR_XORDIFF"
    assert op.generate_model("sat")[:5] == [
        "a_0 b_0 -AX_p_0",
        "a_0 b_0 -c_0 out_0",
        "-a_0 AX_p_0",
        "a_0 b_0 c_0 -out_0",
        "-b_0 AX_p_0",
    ]

    op.model_version = "ANDXOR_LINEAR"
    assert op.generate_model("sat")[:5] == [
        "-c_0 AX_p_0",
        "-a_0 AX_p_0",
        "-b_0 AX_p_0",
        "c_0 -out_0",
        "out_0 -AX_p_0",
    ]
    assert op.generate_model("milp")[:5] == [
        "AX_p_0 - a_0 >= 0",
        "AX_p_0 - b_0 >= 0",
        "AX_p_0 - c_0 >= 0",
        "c_0 - out_0 >= 0",
        "out_0 - AX_p_0 >= 0",
    ]

    assert ANDXOR.bit_andxor_ddt() == [
        [8, 0],
        [0, 8],
        [4, 4],
        [4, 4],
        [4, 4],
        [4, 4],
        [4, 4],
        [4, 4],
    ]
    assert ANDXOR.bit_andxor_lat() == [
        [8, 0],
        [0, 4],
        [0, 0],
        [0, 4],
        [0, 0],
        [0, 4],
        [0, 0],
        [0, -4],
    ]
    assert len(ANDXOR.bit_andxor_diff_truth_table()) == 32
    assert ANDXOR.bit_andxor_diff_truth_table().count("1") == 14
    assert len(ANDXOR.bit_andxor_linear_truth_table()) == 32
    assert ANDXOR.bit_andxor_linear_truth_table().count("1") == 5


def test_unary_equivalence_operators_share_stable_models():
    left = var.Variable(2, ID="in0")
    out = var.Variable(2, ID="out")

    for op in (
        NOT([left], [out], ID="NOT"),
        ConstantXOR([left], [out], [[1]], round=1, index=0, ID="CX"),
    ):
        # NOT and ConstantXOR are affine, so the differential propagation is equivalence,
        # identical to the linear one -> both LINEAR and XORDIFF give the same model.
        for suffix in ("LINEAR", "XORDIFF"):
            op.model_version = f"{op.__class__.__name__}_{suffix}"
            assert op.generate_model("sat") == [
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


def test_boolean_operator_rejects_unknown_model_version():
    op = XOR(
        [var.Variable(2, ID="in0"), var.Variable(2, ID="in1")],
        [var.Variable(2, ID="out")],
        ID="XOR",
    )
    op.model_version = "XOR_BOGUS"
    with pytest.raises(ValueError, match="not existing"):
        op.generate_model("sat")
