from types import SimpleNamespace

import pytest

import variables.variables as var
from attacks import common
from attacks import differential_cryptanalysis as diff
from attacks import linear_cryptanalysis as linear
from tools import model_objective


def _boundary_cipher():
    inputs = [var.Variable(4, ID="x"), var.Variable(4, ID="y")]
    outputs = [var.Variable(4, ID="z")]
    return SimpleNamespace(
        inputs={"plaintext": inputs},
        outputs={"ciphertext": outputs},
        inputs_constraints=[SimpleNamespace(input_vars=inputs)],
    )


def test_fixed_input_constraints_expand_bits_consistently_for_diff_and_linear_sat():
    cipher = _boundary_cipher()
    config = {"model_type": "sat"}

    expected = ["-x_0", "-x_1", "-x_2", "x_3", "-y_0", "-y_1", "y_2", "-y_3"]

    assert diff.gen_fixed_input_output_constraints("input", "0x12", cipher, config) == expected
    assert linear.gen_fixed_input_output_constraints("input", "0x12", cipher, config) == expected


def test_fixed_output_constraints_generate_milp_binary_declarations():
    cipher = _boundary_cipher()

    assert common.gen_fixed_input_output_constraints(
        "output", "0b1010", cipher, {"model_type": "milp"}, value_name="fix_value"
    ) == [
        "z_0 = 1",
        "Binary\nz_0",
        "z_1 = 0",
        "Binary\nz_1",
        "z_2 = 1",
        "Binary\nz_2",
        "z_3 = 0",
        "Binary\nz_3",
    ]


def test_fixed_value_rejects_too_many_bits():
    with pytest.raises(ValueError, match="5 bits"):
        common.normalize_fixed_value_bits("0b10000", 4, "fix_value")


def test_input_non_zero_constraints_use_word_ids_for_truncated_goals():
    cipher = _boundary_cipher()

    assert diff.gen_input_non_zero_constraints(
        cipher, "TRUNCATEDDIFF_SBOXCOUNT", {"model_type": "sat"}
    ) == ["x y"]
    assert linear.gen_input_non_zero_constraints(
        cipher, "TRUNCATEDLINEAR_SBOXCOUNT", {"model_type": "sat"}
    ) == ["x y"]


def test_decimal_weight_detection_uses_lat_for_linear_goals():
    class FakeSbox:
        def __init__(self):
            self.ddt_called = False
            self.lat_called = False

        def computeDDT(self):
            self.ddt_called = True
            return [[1]]

        def computeLAT(self):
            self.lat_called = True
            return [[1]]

        def gen_weights(self, table):
            return [1.5]

    fake_sbox = FakeSbox()
    cipher_function = SimpleNamespace(
        nbr_rounds=1,
        nbr_layers=0,
        constraints={1: {0: [fake_sbox]}},
    )
    cipher = SimpleNamespace(functions={"PERMUTATION": cipher_function})

    assert model_objective.has_Sbox_with_decimal_weights(cipher, "LINEARPATH_CORR")
    assert fake_sbox.lat_called
    assert not fake_sbox.ddt_called
