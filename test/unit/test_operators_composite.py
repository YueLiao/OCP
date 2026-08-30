"""Composite operator AESround (AESround.py): internal layer structure, Python/C code
generation, per-inner-operator model-version mapping, and model generation.
"""
import pytest

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


def test_aesround_inner_model_version_keeps_sbox_tag_strips_others():
    inputs, outputs = _aes_round_inputs_outputs()
    keys = [var.Variable(8, ID=f"k{i}") for i in range(16)]
    op = AESround(inputs, outputs, subkey=keys, ID="AESR")
    op.model_version = "AESround_XORDIFF_PR"

    sbox = op.layers[0][0]       # AES_Sbox
    shiftrows = op.layers[1][0]  # Equal
    mixcolumns = op.layers[2][0]  # Matrix
    addroundkey = op.layers[-1][0]  # XOR
    # The S-box keeps the full suffix; the other operators only take the base version.
    assert op._inner_model_version(sbox) == "AES_Sbox_XORDIFF_PR"
    assert op._inner_model_version(shiftrows) == "Equal_XORDIFF"
    assert op._inner_model_version(mixcolumns) == "Matrix_XORDIFF"
    assert op._inner_model_version(addroundkey) == "XOR_XORDIFF"


@pytest.mark.parametrize(
    ("round_version", "sbox_version", "base_version"),
    [
        ("AESround_XORDIFF_A", "AES_Sbox_XORDIFF_A", "Matrix_XORDIFF"),
        ("AESround_LINEAR_PR", "AES_Sbox_LINEAR_PR", "Matrix_LINEAR"),
        ("AESround_TRUNCATEDDIFF_A", "AES_Sbox_TRUNCATEDDIFF_A", "Matrix_TRUNCATEDDIFF"),
        ("AESround_XORDIFF", "AES_Sbox_XORDIFF", "Matrix_XORDIFF"),
    ],
)
def test_aesround_inner_model_version_across_versions(round_version, sbox_version, base_version):
    inputs, outputs = _aes_round_inputs_outputs()
    op = AESround(inputs, outputs, ID="AESR")
    op.model_version = round_version
    assert op._inner_model_version(op.layers[0][0]) == sbox_version
    assert op._inner_model_version(op.layers[2][0]) == base_version


def test_aesround_accepts_bitlevel_and_truncated_versions():
    inputs, outputs = _aes_round_inputs_outputs()
    op = AESround(inputs, outputs, ID="AESR")
    for model_type in ("sat", "milp"):
        for suffix in ("XORDIFF", "XORDIFF_A", "XORDIFF_PR", "LINEAR", "LINEAR_PR", "TRUNCATEDDIFF"):
            op.model_version = f"AESround_{suffix}"
            op.check_supported_model_version(model_type)  # must not raise
    op.model_version = "AESround_NOT_A_VERSION"
    with pytest.raises(Exception):
        op.check_supported_model_version("milp")


def test_aesround_generate_model_truncated_propagates_versions():
    inputs, outputs = _aes_round_inputs_outputs()
    op = AESround(inputs, outputs, ID="AESR")
    op.model_version = "AESround_TRUNCATEDDIFF_A"

    model = op.generate_model("milp")

    assert isinstance(model, list) and len(model) > 0
    # After generation the inner operators carry the propagated versions.
    assert op.layers[0][0].model_version == "AES_Sbox_TRUNCATEDDIFF_A"  # S-box keeps the tag
    assert op.layers[2][0].model_version == "Matrix_TRUNCATEDDIFF"      # non-S-box stripped
    assert isinstance(op.weight, list)
