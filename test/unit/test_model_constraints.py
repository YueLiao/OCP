import os
import subprocess
import sys

import pytest

import variables.variables as var
from tools.model_constraints import (
    gen_round_model_constraint_obj_fun,
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


def test_model_constraints_defers_pysat_cardinality_import():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import tools.model_constraints as m; print(m.CardEnc is None)",
        ],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "True"


class FakeInputConstraint:
    def generate_model(self, model_type):
        return ["input"]


class FakeOutputConstraint:
    def generate_model(self, model_type):
        return ["output"]


class FakeRoundConstraint:
    weight = ["w0"]

    def generate_model(self, model_type):
        return ["round_a", "round_b"]


class FakeFunction:
    nbr_rounds = 1
    nbr_layers = 0

    def __init__(self):
        self.constraints = {1: {0: [FakeRoundConstraint()]}}


class FakeCipher:
    inputs_constraints = [FakeInputConstraint()]
    outputs_constraints = [FakeOutputConstraint()]

    def __init__(self):
        self.functions = {"PERMUTATION": FakeFunction()}


def test_round_model_generation_can_record_profile():
    config_model = {
        "functions": ["PERMUTATION"],
        "rounds": {"PERMUTATION": [1]},
        "layers": {"PERMUTATION": {1: [0]}},
        "positions": {"PERMUTATION": {1: {0: [0]}}},
        "profile_model_generation": True,
    }

    constraints, obj_fun = gen_round_model_constraint_obj_fun(
        FakeCipher(),
        "DIFFERENTIAL_SBOXCOUNT",
        "milp",
        config_model,
    )

    assert constraints == ["input", "output", "round_a", "round_b"]
    assert obj_fun == [["w0"]]
    profile = config_model["model_generation_profile"]
    assert profile["total_constraints"] == 4
    assert profile["operators"]["FakeInputConstraint"]["calls"] == 1
    assert profile["operators"]["FakeRoundConstraint"]["constraints"] == 2
    assert profile["total_time_s"] >= 0
