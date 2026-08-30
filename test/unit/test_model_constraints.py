import os
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

import variables.variables as var
import tools.model_constraints as model_constraints
from tools.model_constraints import (
    gen_constraints_sum_at_most,
    gen_constraints_sum_exactly,
    gen_matsui_constraints_milp,
    gen_matsui_constraints_sat,
    gen_matsui_partial_cardinality_sat,
    gen_predefined_constraints,
    gen_sequential_encoding_sat,
)
from tools.operator_constraints import (
    gen_matrix_row_constraints,
    gen_nxor_constraints,
    gen_word_matrix_row_constraints,
    gen_xor_constraints,
)
from tools.model_templates import (
    gen_constraints_obj_func_from_template,
    generate_and_save_constraints,
    instantiate_constraints_template,
    load_constraints_template,
)
from tools.sat_search import gen_sat_constraints_from_objective_target


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


def test_matsui_constraints_do_not_mutate_input_obj_lists():
    # The trailing empty round is trimmed internally; the caller's list must stay intact.
    obj_fun = [["w0"], ["w1"], []]
    gen_matsui_constraints_milp(2, [1], obj_fun, "ALL")
    assert obj_fun == [["w0"], ["w1"], []]

    obj_var = [["w0"], ["w1"], []]
    gen_matsui_constraints_sat(2, [1], 2, obj_var)
    assert obj_var == [["w0"], ["w1"], []]


def test_matsui_milp_happy_path_bounds_each_partial_objective_against_total():
    # valid config: each partial-round objective is bounded against the total `obj` by the
    # best-known value (best_obj), i.e. `<round terms> - obj <= -best_obj`.
    cons = gen_matsui_constraints_milp(2, [1], [["w0"], ["w1"]], "ALL")
    assert set(cons) == {"w0 - obj <= -1", "w1 - obj <= -1"}


def test_predefined_constraints_sat_value_branches():
    # Trivially-satisfied bounds emit no clause.
    assert gen_predefined_constraints("sat", "AT_MOST", ["a", "b"], 1, bitwise=False) == []
    assert gen_predefined_constraints("sat", "AT_LEAST", ["a", "b"], 0, bitwise=False) == []
    # value 0/1 force each variable false/true.
    assert gen_predefined_constraints("sat", "EXACTLY", ["a", "b"], 1, bitwise=False) == ["a", "b"]
    assert gen_predefined_constraints("sat", "EXACTLY", ["a", "b"], 0, bitwise=False) == ["-a", "-b"]
    assert gen_predefined_constraints("sat", "AT_LEAST", ["a", "b"], 1, bitwise=False) == ["a", "b"]
    assert gen_predefined_constraints("sat", "AT_MOST", ["a", "b"], 0, bitwise=False) == ["-a", "-b"]
    # SUM_AT_LEAST 1 is a single disjunction; SUM_EXACTLY 0 forces each variable false.
    assert gen_predefined_constraints("sat", "SUM_AT_LEAST", ["a", "b"], 1, bitwise=False) == ["a b"]
    assert gen_predefined_constraints("sat", "SUM_EXACTLY", ["a", "b"], 0, bitwise=False) == ["-a", "-b"]
    # EXACTLY only supports value 0/1 in SAT.
    with pytest.raises(ValueError, match="EXACTLY"):
        gen_predefined_constraints("sat", "EXACTLY", ["a", "b"], 2, bitwise=False)


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
    assert gen_matrix_row_constraints(["a"], "b", "sat") == ["-a b", "a -b"]
    assert gen_matrix_row_constraints(["a", "b"], "c", "sat") == [
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
        gen_word_matrix_row_constraints("a", "b", "sat")


def test_predefined_and_template_helpers_raise_value_errors_for_invalid_options(monkeypatch):
    # Force the PySAT branch so the encoding guard is reached without a real PySAT backend;
    # the invalid encoding is rejected before any backend call.
    monkeypatch.setattr(model_constraints, "pysat_import", True)
    with pytest.raises(ValueError, match="Invalid encoding"):
        gen_constraints_sum_exactly("sat", ["a"], 1, encoding=99)

    with pytest.raises(ValueError, match="unsupported tool type 'bad' for milp model"):
        generate_and_save_constraints("milp", "bad", "diff", [], ["x"], ["y"])


@pytest.mark.skipif(shutil.which("espresso") is None, reason="espresso CLI not on PATH")
def test_generate_and_save_constraints_returns_generated_template(tmp_path):
    ttable = "1001"
    model_file = tmp_path / "xor_template.txt"

    constraints, objective_fun = generate_and_save_constraints(
        "sat",
        "minimize_logic",
        0,
        ttable,
        ["a0"],
        ["b0"],
        model_filename=model_file,
    )

    assert isinstance(constraints, list)
    assert constraints
    assert objective_fun is None
    assert load_constraints_template(model_file) == (constraints, None)


@pytest.mark.skipif(shutil.which("espresso") is None, reason="espresso CLI not on PATH")
def test_in_memory_template_instantiation_matches_loaded_template(tmp_path):
    model_file = tmp_path / "template.txt"
    constraints, objective_fun = generate_and_save_constraints(
        "sat",
        "minimize_logic",
        0,
        "1001",
        ["a0"],
        ["b0"],
        objective_fun="p0",
        model_filename=model_file,
    )

    in_memory = instantiate_constraints_template(
        constraints,
        objective_fun,
        ["x_0"],
        ["y_0"],
        ["w_0"],
    )
    from_file = gen_constraints_obj_func_from_template(
        model_file,
        ["x_0"],
        ["y_0"],
        ["w_0"],
    )

    assert in_memory == from_file


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


def test_pysat_cardinality_errors_are_reported_and_return_empty(capsys, monkeypatch):
    def failing_encoder(**kwargs):
        raise ValueError("unsupported encoding")

    monkeypatch.setattr(model_constraints, "_load_pysat_cardinality_backend", lambda: (object(), object()))
    monkeypatch.setattr(model_constraints, "_pysat_cardinality_error_types", lambda: (ValueError,))

    constraints = model_constraints._pysat_cardinality_constraints(
        ["a", "b"],
        1,
        99,
        failing_encoder,
        "atmost",
    )

    assert constraints == []
    assert "does not support encoding" in capsys.readouterr().out


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


# ===================== fixed input/output boundary constraints (moved from test_attack_common) =====================
def _boundary_cipher():
    inputs = [var.Variable(4, ID="x"), var.Variable(4, ID="y")]
    outputs = [var.Variable(4, ID="z")]
    return SimpleNamespace(
        inputs={"plaintext": inputs},
        outputs={"ciphertext": outputs},
        inputs_constraints=[SimpleNamespace(input_vars=inputs)],
    )


def test_fixed_input_constraints_expand_bits_for_sat():
    cipher = _boundary_cipher()

    expected = ["-x_0", "-x_1", "-x_2", "x_3", "-y_0", "-y_1", "y_2", "-y_3"]

    assert model_constraints.gen_fixed_input_output_constraints(
        "input", "0x12", cipher, "sat", value_name="fix_diff"
    ) == expected


def test_fixed_output_constraints_generate_milp_binary_declarations():
    cipher = _boundary_cipher()

    assert model_constraints.gen_fixed_input_output_constraints(
        "output", "0b1010", cipher, "milp", value_name="fix_value"
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
        model_constraints.normalize_fixed_value_bits("0b10000", 4, "fix_value")


def test_fixed_value_rejects_malformed_hex_with_readable_error():
    with pytest.raises(ValueError, match="Invalid input_diff format"):
        model_constraints.normalize_fixed_value_bits("0xnothex", 4, "input_diff")


def test_fixed_value_rejects_malformed_binary_with_readable_error():
    # the 0b branch must reject non-binary digits, symmetrically with the 0x branch
    with pytest.raises(ValueError, match="Invalid input_diff format"):
        model_constraints.normalize_fixed_value_bits("0b1012", 4, "input_diff")
    assert model_constraints.normalize_fixed_value_bits("0b1010", 4, "input_diff") == "1010"  # valid still works


def test_input_non_zero_constraints_use_word_ids_when_not_bitwise():
    cipher = _boundary_cipher()

    # bitwise=False -> word-level markers (truncated goals).
    assert model_constraints.gen_input_non_zero_constraints(
        cipher, {"model_type": "sat"}, bitwise=False
    ) == ["x y"]
    # bitwise=True -> per-bit markers.
    assert model_constraints.gen_input_non_zero_constraints(
        cipher, {"model_type": "sat"}, bitwise=True
    ) == ["x_0 x_1 x_2 x_3 y_0 y_1 y_2 y_3"]


def test_required_fixed_boundary_constraints_are_shared_for_diff_and_linear():
    cipher = _boundary_cipher()

    assert model_constraints.gen_required_fixed_boundary_constraints(
        cipher,
        "0x12",
        None,
        "sat",
    ) == ["-x_0", "-x_1", "-x_2", "x_3", "-y_0", "-y_1", "y_2", "-y_3"]

    with pytest.raises(ValueError, match="input or output value must be specified"):
        model_constraints.gen_required_fixed_boundary_constraints(
            cipher,
            None,
            None,
            "sat",
        )
