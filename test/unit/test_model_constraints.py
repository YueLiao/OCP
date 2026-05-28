import pytest

import variables.variables as var
from tools.model_constraints import (
    gen_constraints_sum_at_most,
    gen_matrix_constraints,
    gen_predefined_constraints,
    gen_sequential_encoding_sat,
)


def test_predefined_constraints_expand_bitwise_variables():
    word = var.Variable(3, ID="x")

    assert gen_predefined_constraints("sat", "EXACTLY", [word], 0) == [
        "-x_0",
        "-x_1",
        "-x_2",
    ]
    assert gen_predefined_constraints("milp", "AT_LEAST", [word], 1, bitwise=False) == [
        "x >= 1",
    ]


def test_sequential_encoding_handles_trivial_upper_bound():
    assert gen_sequential_encoding_sat(["a"], 1) == []
    assert gen_constraints_sum_at_most("sat", ["a", "b"], 2) == []
    assert gen_sequential_encoding_sat(["a", "b"], 0) == ["-a", "-b"]


def test_sequential_encoding_rejects_invalid_weight():
    with pytest.raises(ValueError):
        gen_sequential_encoding_sat(["a"], 2)


def test_matrix_constraints_preserve_xor_special_cases():
    assert gen_matrix_constraints(["a"], "b", "sat") == ["a -b", "-a b"]
    assert gen_matrix_constraints(["a", "b"], "c", "sat") == [
        "a b -c",
        "a -b c",
        "-a b c",
        "-a -b -c",
    ]
