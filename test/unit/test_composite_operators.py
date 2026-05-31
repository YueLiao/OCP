import variables.variables as var
from operators.AESround import AESround


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
