import os
import subprocess
import sys
import builtins

import pytest

import variables.variables as var
import tools.model_constraints as model_constraints
from tools.model_constraints import (
    MODEL_GENERATION_PROFILE_ENABLED_KEY,
    MODEL_GENERATION_PROFILE_KEY,
    gen_constraints_obj_func_from_template,
    gen_constraints_sum_at_most,
    gen_matrix_constraints,
    gen_predefined_constraints,
    gen_round_model_constraint_obj_fun,
    gen_sequential_encoding_sat,
    load_constraints_template,
)
from tools.bit_constraints import gen_nxor_constraints, gen_xor_constraints, gen_word_matrix_constraints
from tools.model_templates import generate_and_save_constraints
from tools.predefined_constraints import gen_constraints_sum_exactly
from tools.objective_targets import gen_sat_constraints_from_objective_target
from tools.search_constraints import (
    gen_matsui_constraints_milp,
    gen_matsui_constraints_sat,
    gen_matsui_partial_cardinality_sat,
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


def test_matsui_constraint_builders_raise_value_errors_for_invalid_inputs():
    with pytest.raises(ValueError, match="Round = 1"):
        gen_matsui_constraints_milp(1, [], [["w0"]])

    with pytest.raises(ValueError, match="best_obj"):
        gen_matsui_constraints_sat(3, [1], 2, [["w0"], ["w1"], ["w2"]])

    with pytest.raises(ValueError, match="GroupConstraintChoice"):
        gen_matsui_constraints_sat(2, [1], 2, [["w0"], ["w1"]], GroupConstraintChoice=2)

    with pytest.raises(ValueError, match="non-empty list"):
        gen_matsui_partial_cardinality_sat([], [], 1, 0, 0, 0)


def test_sat_objective_target_rejects_invalid_decimal_and_matsui_configs():
    with pytest.raises(ValueError, match="Length mismatch"):
        gen_sat_constraints_from_objective_target(
            [["0.5 d0"]],
            {"atmost_encoding_sat": "SEQUENTIAL"},
            "SUM_AT_MOST",
            1,
            obj_val_decimal=[0, 1],
        )

    with pytest.raises(ValueError, match="Matsui constraints only support"):
        gen_sat_constraints_from_objective_target(
            [["w0"], ["w1"]],
            {"matsui_constraint": {"Round": 2, "best_obj": [1]}},
            "SUM_EXACTLY",
            1,
        )


def test_matrix_constraints_preserve_xor_special_cases():
    assert gen_matrix_constraints(["a"], "b", "sat") == ["a -b", "-a b"]
    assert gen_matrix_constraints(["a", "b"], "c", "sat") == [
        "a b -c",
        "a -b c",
        "-a b c",
        "-a -b -c",
    ]


def test_bit_constraint_helpers_reject_invalid_variable_shapes():
    with pytest.raises(TypeError, match="must be strings"):
        gen_xor_constraints("a", 1, "b", "sat")

    with pytest.raises(TypeError, match="list of strings"):
        gen_nxor_constraints(["a", 1], "b", "sat")

    with pytest.raises(TypeError, match="list of strings"):
        gen_word_matrix_constraints("a", "b", "sat")


def test_predefined_and_template_helpers_raise_value_errors_for_invalid_options():
    with pytest.raises(ValueError, match="Invalid encoding"):
        gen_constraints_sum_exactly(
            "sat",
            ["a"],
            1,
            encoding=99,
            pysat_available=lambda: True,
            require_cardenc=lambda: object(),
            cardinality_constraints=lambda *args, **kwargs: [],
        )

    with pytest.raises(ValueError, match="Unsupported tool type bad"):
        generate_and_save_constraints("milp", "bad", "diff", [], ["x"], ["y"])


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
    ID = "IN_LINK_EQ_0"

    def generate_model(self, model_type):
        return ["input"]


class FakeOutputConstraint:
    ID = "OUT_LINK_EQ_0"

    def generate_model(self, model_type):
        return ["output"]


class FakeRoundConstraint:
    ID = "FakeRound_1_0_0"
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
        MODEL_GENERATION_PROFILE_ENABLED_KEY: True,
    }

    constraints, obj_fun = gen_round_model_constraint_obj_fun(
        FakeCipher(),
        "DIFFERENTIAL_SBOXCOUNT",
        "milp",
        config_model,
    )

    assert constraints == ["input", "output", "round_a", "round_b"]
    assert obj_fun == [["w0"]]
    profile = config_model[MODEL_GENERATION_PROFILE_KEY]
    assert profile["total_constraints"] == 4
    assert profile["operators"]["FakeInputConstraint"]["calls"] == 1
    assert profile["operators"]["FakeRoundConstraint"]["constraints"] == 2
    assert profile["operator_prefixes"]["FakeInputConstraint:IN_LINK_EQ"]["calls"] == 1
    assert profile["operator_prefixes"]["FakeRoundConstraint:FakeRound"]["constraints"] == 2
    assert profile["total_time_s"] >= 0


def test_identity_alias_rewrite_preserves_model_token_boundaries():
    aliases = {
        "v_1_2_3": "v_1_1_3",
        "v_1_2_30": "v_1_1_30",
    }

    assert model_constraints._apply_identity_aliases(
        [
            "-v_1_2_3_0 v_1_2_30_0",
            "v_1_2_3_0 - v_1_2_30_0 = 0",
            "Binary\nv_1_2_3_0 v_1_2_30_0",
        ],
        aliases,
    ) == [
        "-v_1_1_3_0 v_1_1_30_0",
        "v_1_1_3_0 - v_1_1_30_0 = 0",
        "Binary\nv_1_1_3_0 v_1_1_30_0",
    ]


def test_constraints_template_loading_is_cached(monkeypatch, tmp_path):
    template = tmp_path / "template.txt"
    template.write_text(
        "Input: a0; msb: a0\n"
        "Output: b0; msb: b0\n"
        "Constraints: ['a0 - b0 = 0']\n"
        "Weight: p0\n",
        encoding="utf-8",
    )

    real_open = builtins.open
    open_calls = []

    def counting_open(*args, **kwargs):
        if args and args[0] == str(template):
            open_calls.append(args[0])
        return real_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", counting_open)

    assert load_constraints_template(str(template)) == (["a0 - b0 = 0"], "p0")
    assert load_constraints_template(str(template)) == (["a0 - b0 = 0"], "p0")

    assert open_calls == [str(template)]


def test_template_variable_replacement_preserves_token_boundaries(tmp_path):
    template = tmp_path / "template.txt"
    template.write_text(
        "Input: a0; msb: a0\n"
        "Output: b0; msb: b0\n"
        "Constraints: ['a0 + a10 - b0 >= 0', 'pa0 + a0 - p0 >= 0']\n"
        "Weight: 2 p0 + p10\n",
        encoding="utf-8",
    )

    var_in = [f"x{i}" for i in range(11)]
    var_p = [f"w{i}" for i in range(11)]

    constraints, objective_fun = gen_constraints_obj_func_from_template(
        str(template),
        var_in,
        ["y0"],
        var_p,
    )

    assert constraints == [
        "x0 + x10 - y0 >= 0",
        "pa0 + x0 - w0 >= 0",
    ]
    assert objective_fun == "2 w0 + w10"


def test_pysat_cardinality_errors_warn_and_return_empty(monkeypatch):
    def failing_encoder(**kwargs):
        raise ValueError("unsupported encoding")

    monkeypatch.setattr(model_constraints, "_load_pysat_cardinality_backend", lambda: (object(), object()))
    monkeypatch.setattr(model_constraints, "_pysat_cardinality_error_types", lambda: (ValueError,))

    with pytest.warns(RuntimeWarning, match="does not support encoding"):
        constraints = model_constraints._pysat_cardinality_constraints(
            ["a", "b"],
            1,
            99,
            failing_encoder,
            "atmost",
        )

    assert constraints == []


def test_pysat_cardinality_programming_errors_are_not_suppressed(monkeypatch):
    def broken_encoder(**kwargs):
        raise TypeError("programming error")

    monkeypatch.setattr(model_constraints, "_load_pysat_cardinality_backend", lambda: (object(), object()))
    monkeypatch.setattr(model_constraints, "_pysat_cardinality_error_types", lambda: (ValueError,))

    with pytest.raises(TypeError, match="programming error"):
        model_constraints._pysat_cardinality_constraints(
            ["a", "b"],
            1,
            1,
            broken_encoder,
            "atmost",
        )
