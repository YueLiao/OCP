from types import SimpleNamespace

import pytest

from tools import model_objective
from tools.model_objective import (
    cal_round_obj_fun_values_from_solution,
    detect_Sbox,
    gen_obj_fun_variables,
    linear_combinations_bounds,
    parse_objective_term,
)


def test_parse_objective_term_supports_common_forms():
    assert parse_objective_term("x") == (1.0, "x")
    assert parse_objective_term("2 x") == (2.0, "x")
    assert parse_objective_term("0.5000 p0") == (0.5, "p0")
    assert parse_objective_term("2x") == (2.0, "x")
    assert parse_objective_term("not valid!") is None


def test_gen_obj_fun_variables_separates_integer_and_decimal_terms():
    obj_fun = [
        ["p0 + 2 p1 + 0.5000 p2"],
        ["p3 + 0.2500 p4 + 0.5000 p5"],
    ]

    int_vars, decimal_vars = gen_obj_fun_variables(obj_fun, obj_fun_decimal=True)

    assert int_vars == [["p0", "p1"], ["p3"]]
    assert decimal_vars == [
        [["p2"], ["p5"]],
        [[], ["p4"]],
    ]


def test_cal_round_obj_fun_values_from_solution_uses_coefficients():
    obj_fun = [["x + 2 y + 0.5 z"], ["missing + 3 w"]]
    solution = {"x": 1, "y": 0, "z": 1, "w": 2}

    assert cal_round_obj_fun_values_from_solution(obj_fun, solution) == [1.5, 6.0]


def test_cal_round_obj_fun_values_reports_unparseable_terms(capsys):
    assert cal_round_obj_fun_values_from_solution([["not valid!"]], {}) == [0]

    assert "Unable to parse objective term" in capsys.readouterr().out


# ===================== decimal-weight detection (moved from test_attack_common) =====================
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


# ===================== linear_combinations_bounds (pure enumeration) =====================
def test_linear_combinations_bounds_enumerates_within_bounds():
    # every integer combination of [1, 2] whose sum is in (-1, 3]
    assert linear_combinations_bounds([1, 2], 3) == [
        (0.0, (0, 0)),
        (1.0, (1, 0)),
        (2.0, (0, 1)),
        (2.0, (2, 0)),
        (3.0, (1, 1)),
        (3.0, (3, 0)),
    ]


def test_linear_combinations_bounds_respects_lower_bound():
    assert linear_combinations_bounds([2], 5, lower_bound=0) == [(0.0, (0,)), (2.0, (1,)), (4.0, (2,))]


@pytest.mark.parametrize("bad_weights", [[1, 0], [-1], [2, -3]])
def test_linear_combinations_bounds_rejects_non_positive_weights(bad_weights):
    # a zero/negative weight would make the enumeration unbounded -> guarded with ValueError
    with pytest.raises(ValueError, match="strictly positive weights"):
        linear_combinations_bounds(bad_weights, 3)


# ===================== detect_Sbox =====================
def test_detect_sbox_returns_first_sbox_operator_or_none():
    class XOR:
        pass

    class AES_Sbox:  # class name contains "Sbox"
        pass

    xor, sbox = XOR(), AES_Sbox()
    with_sbox = SimpleNamespace(
        functions={"P": SimpleNamespace(nbr_rounds=1, nbr_layers=0, constraints={1: {0: [xor, sbox]}})}
    )
    assert detect_Sbox(with_sbox) is sbox  # the first S-box operator, skipping the XOR

    without_sbox = SimpleNamespace(
        functions={"P": SimpleNamespace(nbr_rounds=1, nbr_layers=0, constraints={1: {0: [XOR()]}})}
    )
    assert detect_Sbox(without_sbox) is None
