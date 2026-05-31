import pytest

import variables.variables as var
from operators.AESround import AESround
from operators.SHACAL2BooleanFunctions import (
    SHACAL2_Ch,
    SHACAL2_Maj,
    SHACAL2_Sigma0,
    SHACAL2_Sigma1,
    SHACAL2_Sum0,
    SHACAL2_Sum1,
)


def _aes_round_inputs_outputs():
    inputs = [var.Variable(8, ID=f"in{i}") for i in range(16)]
    outputs = [var.Variable(8, ID=f"out{i}") for i in range(16)]
    return inputs, outputs


def test_aesround_builds_expected_internal_layers_without_subkey():
    inputs, outputs = _aes_round_inputs_outputs()
    op = AESround(inputs, outputs, ID="AESR")

    assert [len(layer) for layer in op.layers] == [16, 16, 1, 1, 1, 1]
    assert [len(group) for group in op.vars] == [16, 16, 16, 16]
    assert [constraint.__class__.__name__ for constraint in op.layers[0][:2]] == ["AES_Sbox", "AES_Sbox"]
    assert [constraint.__class__.__name__ for constraint in op.layers[1][:2]] == ["Equal", "Equal"]
    assert [[constraint.__class__.__name__ for constraint in layer] for layer in op.layers[2:]] == [
        ["Matrix"],
        ["Matrix"],
        ["Matrix"],
        ["Matrix"],
    ]


def test_aesround_python_implementation_keeps_shiftrows_and_mixcolumns_order():
    inputs, outputs = _aes_round_inputs_outputs()
    op = AESround(inputs, outputs, ID="AESR")
    code = op.generate_implementation("python", unroll=True)

    assert code[:4] == [
        "in0_SB = AES_Sbox[in0]",
        "in1_SB = AES_Sbox[in1]",
        "in2_SB = AES_Sbox[in2]",
        "in3_SB = AES_Sbox[in3]",
    ]
    assert code[16:20] == [
        "in0_SR = in0_SB",
        "in1_SR = in5_SB",
        "in2_SR = in10_SB",
        "in3_SR = in15_SB",
    ]
    assert code[-4:] == [
        "(out0, out1, out2, out3) = aes_matrix(in0_SR, in1_SR, in2_SR, in3_SR)",
        "(out4, out5, out6, out7) = aes_matrix(in4_SR, in5_SR, in6_SR, in7_SR)",
        "(out8, out9, out10, out11) = aes_matrix(in8_SR, in9_SR, in10_SR, in11_SR)",
        "(out12, out13, out14, out15) = aes_matrix(in12_SR, in13_SR, in14_SR, in15_SR)",
    ]


def test_aesround_c_implementation_declares_intermediates_and_adds_round_key():
    inputs, outputs = _aes_round_inputs_outputs()
    keys = [var.Variable(8, ID=f"k{i}") for i in range(16)]
    op = AESround(inputs, outputs, subkey=keys, ID="AESRK")
    code = op.generate_implementation("c", unroll=True)

    assert [len(layer) for layer in op.layers] == [16, 16, 1, 1, 1, 1, 16]
    assert code[0].startswith("uint8_t in0_SB, in1_SB")
    assert "in15_MC" in code[0]
    assert code[1:4] == [
        "in0_SB = AES_Sbox[in0];",
        "in1_SB = AES_Sbox[in1];",
        "in2_SB = AES_Sbox[in2];",
    ]
    assert code[-4:] == [
        "out12 = in12_MC ^ k12;",
        "out13 = in13_MC ^ k13;",
        "out14 = in14_MC ^ k14;",
        "out15 = in15_MC ^ k15;",
    ]


def test_aesround_headers_include_sbox_and_matrix_macros_once():
    inputs, outputs = _aes_round_inputs_outputs()
    op = AESround(inputs, outputs, ID="AESR")
    header = op.generate_implementation_header("python")

    assert header[0].startswith("AES_Sbox = [99, 124, 119, 123")
    assert header.count("#Matrix Macro ") == 1
    assert "def aes_matrix(x0, x1, x2, x3):" in header
    assert "\ty0 = GMUL(x0,2,0x1B,8) ^ GMUL(x1,3,0x1B,8) ^ x2 ^ x3" in header


def test_shacal2_sigma_and_sum_composition_generates_expected_rotations():
    x = [var.Variable(32, ID="x")]
    y = [var.Variable(32, ID="y")]

    sigma0 = SHACAL2_Sigma0(x, y, ID="SIG0")
    assert [len(layer) for layer in sigma0.layers] == [3, 1]
    assert sigma0.generate_implementation("python", unroll=True) == [
        "x_0 = ROTR(x, 7, 32)",
        "x_1 = ROTR(x, 18, 32)",
        "x_2 = (x >> 3) & (2**32 - 1)",
        "y = x_0 ^ x_1 ^ x_2",
    ]
    assert sigma0.generate_implementation("c", unroll=True)[:3] == [
        "uint8_t x_0, x_1, x_2;",
        "x_0 = ROTR(x, 7, 32);",
        "x_1 = ROTR(x, 18, 32);",
    ]

    sum0 = SHACAL2_Sum0(x, y, ID="SUM0")
    assert [len(layer) for layer in sum0.layers] == [3, 1]
    assert sum0.generate_implementation("python", unroll=True) == [
        "x_0 = ROTR(x, 2, 32)",
        "x_1 = ROTR(x, 13, 32)",
        "x_2 = ROTR(x, 22, 32)",
        "y = x_0 ^ x_1 ^ x_2",
    ]


def test_shacal2_1024_bit_sigma_and_sum_constants_are_stable():
    x = [var.Variable(64, ID="x")]
    y = [var.Variable(64, ID="y")]

    sigma1 = SHACAL2_Sigma1(x, y, keysize=1024, ID="SIG1")
    assert sigma1.generate_implementation("python", unroll=True) == [
        "x_0 = ROTR(x, 19, 64)",
        "x_1 = ROTR(x, 61, 64)",
        "x_2 = (x >> 6) & (2**64 - 1)",
        "y = x_0 ^ x_1 ^ x_2",
    ]
    assert sigma1.generate_implementation("c", unroll=True)[:4] == [
        "uint8_t x_0, x_1, x_2;",
        "x_0 = ROTR(x, 19, 64);",
        "x_1 = ROTR(x, 61, 64);",
        "x_2 = (x >> 6) & ((1<<64) - 1);",
    ]

    sum1 = SHACAL2_Sum1(x, y, keysize=1024, ID="SUM1")
    assert sum1.generate_implementation("python", unroll=True) == [
        "x_0 = ROTR(x, 14, 64)",
        "x_1 = ROTR(x, 18, 64)",
        "x_2 = ROTR(x, 41, 64)",
        "y = x_0 ^ x_1 ^ x_2",
    ]


@pytest.mark.parametrize("operator_class", [SHACAL2_Sigma0, SHACAL2_Sigma1, SHACAL2_Sum0, SHACAL2_Sum1])
def test_shacal2_sigma_and_sum_reject_unsupported_keysize(operator_class):
    x = [var.Variable(32, ID="x")]
    y = [var.Variable(32, ID="y")]

    with pytest.raises(ValueError, match="expected 512 or 1024"):
        operator_class(x, y, keysize=256)


def test_shacal2_maj_and_ch_composition_generates_expected_boolean_flow():
    inputs = [var.Variable(32, ID=name) for name in ("a", "b", "c")]
    y = [var.Variable(32, ID="y")]

    maj = SHACAL2_Maj(inputs, y, ID="MAJ")
    assert [len(layer) for layer in maj.layers] == [3, 1]
    assert maj.generate_implementation("python", unroll=True) == [
        "a_0 = a & b",
        "b_1 = a & c",
        "c_2 = b & c",
        "y = a_0 ^ b_1 ^ c_2",
    ]
    assert maj.generate_implementation("c", unroll=True) == [
        "uint8_t a_0, b_1, c_2;",
        "a_0 = a & b;",
        "b_1 = a & c;",
        "c_2 = b & c;",
        "y = a_0 ^ b_1 ^ c_2;",
    ]

    ch = SHACAL2_Ch(inputs, y, ID="CH")
    assert [len(layer) for layer in ch.layers] == [1, 2, 1]
    assert ch.generate_implementation("python", unroll=True) == [
        "a_0_0 = a ^ 0xffffffff",
        "a_1_0 = a & b",
        "b_1_1 = a_0_0 & c",
        "y = a_1_0 ^ b_1_1",
    ]
    assert ch.generate_implementation("c", unroll=True) == [
        "uint8_t a_0_0, a_1_0, b_1_1;",
        "a_0_0 = a ^ 0xffffffff;",
        "a_1_0 = a & b;",
        "b_1_1 = a_0_0 & c;",
        "y = a_1_0 ^ b_1_1;",
    ]


def test_shacal2_composite_model_generation_routes_to_child_operator_interfaces():
    x = [var.Variable(32, ID="x")]
    y = [var.Variable(32, ID="y")]
    sigma0 = SHACAL2_Sigma0(x, y, ID="SIG0")
    sigma0.model_version = "SHACAL2_Sigma0_XORDIFF"

    sigma_model = sigma0.generate_model("sat")

    assert len(sigma_model) == 448
    assert sigma_model[:4] == [
        "-x_0 x_0_7",
        "x_0 -x_0_7",
        "-x_1 x_0_8",
        "x_1 -x_0_8",
    ]
    assert sigma_model[-1] == "y_31 -x_0_31 -x_1_31 -x_2_31"

    inputs = [var.Variable(32, ID=name) for name in ("a", "b", "c")]
    maj = SHACAL2_Maj(inputs, y, ID="MAJ")
    maj.model_version = "SHACAL2_Maj_XORDIFF"

    maj_model = maj.generate_model("milp")

    assert len(maj_model) == 547
    assert maj_model[:4] == [
        "a_0 + b_0 - a_0_0 >= 0",
        "a_0 + b_0 - Maj_AND_1_p_0 >= 0",
        "- a_0 + Maj_AND_1_p_0 >= 0",
        "- b_0 + Maj_AND_1_p_0 >= 0",
    ]
    assert maj_model[-1] == "Integer\nMaj_NXOR1_d_31"
