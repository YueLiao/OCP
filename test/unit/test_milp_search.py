"""Unit tests for tools/milp_search.py - objective-target parsing, MILP constraint/objective
building, LP model writing, and the modeling+solving orchestration (with a mocked solver).
"""
import pytest

import tools.milp_search as milp_search
from tools.milp_search import write_milp_model
from tools.model_constraints import gen_predefined_constraints


# ------------------------------ parse_objective_target ------------------------------
def test_parse_objective_target_all_branches():
    assert milp_search.parse_objective_target("OPTIMAL") == ("OPTIMAL", None)
    assert milp_search.parse_objective_target("EXISTENCE") == ("EXISTENCE", None)
    assert milp_search.parse_objective_target("AT MOST 3") == ("AT MOST", 3.0)
    assert milp_search.parse_objective_target("EXACTLY 2.5") == ("EXACTLY", 2.5)
    assert milp_search.parse_objective_target("AT LEAST 1") == ("AT LEAST", 1.0)


def test_parse_objective_target_rejects_malformed_and_unknown():
    with pytest.raises(ValueError, match="Invalid format"):
        milp_search.parse_objective_target("AT MOST x")
    with pytest.raises(ValueError, match="Unsupported objective_target"):
        milp_search.parse_objective_target("NOPE")


# ------------------------------ gen_milp_constraints_from_objective_target ------------------------------
def test_gen_milp_constraints_from_objective_target_dispatch():
    assert milp_search.gen_milp_constraints_from_objective_target("OPTIMAL") == []
    assert milp_search.gen_milp_constraints_from_objective_target("EXISTENCE") == []
    assert milp_search.gen_milp_constraints_from_objective_target("AT MOST 2") == \
        gen_predefined_constraints("milp", "AT_MOST", ["obj"], 2.0)
    assert milp_search.gen_milp_constraints_from_objective_target("EXACTLY 3") == \
        gen_predefined_constraints("milp", "EXACTLY", ["obj"], 3.0)
    assert milp_search.gen_milp_constraints_from_objective_target("AT LEAST 1") == \
        gen_predefined_constraints("milp", "AT_LEAST", ["obj"], 1.0)


# ------------------------------ _milp_objective_function ------------------------------
def test_milp_objective_function_none_for_existence_else_copy():
    obj = [["w0"], ["w1"]]
    assert milp_search._milp_objective_function("EXISTENCE", obj) is None
    out = milp_search._milp_objective_function("OPTIMAL", obj)
    assert out == obj and out is not obj  # a copy, so callers cannot mutate the original


# ------------------------------ _attach_milp_solution_objectives ------------------------------
def test_attach_milp_solution_objectives_recomputes_zero_and_missing_preserves_nonzero():
    obj_fun = [["w0"], ["w1"]]
    sols = [
        {"w0": 1, "w1": 2},                        # no obj_fun_value -> recompute from rounds
        {"w0": 1, "w1": 2, "obj_fun_value": 0},    # zero -> recompute
        {"w0": 1, "w1": 2, "obj_fun_value": 99},   # nonzero -> preserved
    ]
    milp_search._attach_milp_solution_objectives(sols, obj_fun)

    assert sols[0]["rounds_obj_fun_values"] == [1.0, 2.0]
    assert sols[0]["obj_fun_value"] == sum(sols[0]["rounds_obj_fun_values"])  # recomputed (was missing)
    assert sols[1]["obj_fun_value"] == sum(sols[1]["rounds_obj_fun_values"])  # recomputed (was 0)
    assert sols[2]["obj_fun_value"] == 99                                      # nonzero preserved


# ------------------------------ write_milp_model ------------------------------
def test_write_milp_model_collects_variable_declarations(tmp_path):
    filename = tmp_path / "model.lp"

    write_milp_model(
        ["x + y >= 1", "Binary\nx y", "Integer\nz"],
        obj_fun=["2 x", "3 y"],
        filename=str(filename),
    )

    content = filename.read_text()
    assert "Minimize\n obj\nSubject To\n" in content
    assert "2 x + 3 y - obj = 0" in content
    assert "Binary\nx y\n" in content
    assert "Integer\nz\n" in content
    assert content.rstrip().endswith("End")


def test_write_milp_model_feasibility_model_when_no_objective(tmp_path):
    filename = tmp_path / "feas.lp"
    write_milp_model(["x >= 0"], obj_fun=None, filename=str(filename))
    content = filename.read_text()
    assert "Minimize\n 0\nSubject To\n" in content  # feasibility-only objective
    assert content.rstrip().endswith("End")


def test_write_milp_model_flattens_list_of_lists_objective(tmp_path):
    filename = tmp_path / "nested.lp"
    write_milp_model(["x >= 0"], obj_fun=[["2 x"], ["3 y"]], filename=str(filename))
    assert "2 x + 3 y - obj = 0" in filename.read_text()


def test_write_milp_model_writes_inline_text_before_binary_declaration(tmp_path):
    filename = tmp_path / "inline.lp"
    write_milp_model(["x + y >= 1\nBinary\nx y"], filename=str(filename))
    content = filename.read_text()
    assert "x + y >= 1\n" in content  # the constraint text preceding the inline Binary block
    assert "Binary\nx y\n" in content


def test_write_milp_model_tolerates_none_filename(monkeypatch, tmp_path):
    # regression: filename=None used to crash in os.path.dirname(None) (the write_sat_model twin)
    monkeypatch.chdir(tmp_path)
    write_milp_model(["x >= 0"], filename=None)
    assert (tmp_path / "milp.lp").exists()  # falls back to the default name, no crash


# ------------------------------ _build_milp_model_constraints ------------------------------
def test_milp_model_constraint_building_does_not_mutate_input():
    constraints = ["x >= 0"]

    model_constraints = milp_search._build_milp_model_constraints(
        "AT MOST 1",
        constraints,
        [["x"]],
        {},
    )

    assert constraints == ["x >= 0"]
    assert model_constraints is not constraints
    assert model_constraints[0] == "x >= 0"
    assert any("obj" in constraint for constraint in model_constraints[1:])


def test_milp_matsui_config_requires_round_aligned_best_objective():
    with pytest.raises(ValueError, match="Round.*best_obj"):
        milp_search._build_milp_model_constraints(
            "OPTIMAL",
            [],
            [["x"]],
            {"matsui_constraint": {"Round": 3, "best_obj": [1]}},
        )


def test_milp_matsui_happy_path_appends_constraints():
    result = milp_search._build_milp_model_constraints(
        "OPTIMAL",
        ["x >= 0"],
        [["w0"], ["w1"]],
        {"matsui_constraint": {"Round": 2, "best_obj": [1]}},  # len(best_obj) == Round - 1
    )
    assert result[0] == "x >= 0"
    assert len(result) > 1  # OPTIMAL adds no objective constraint, so the extra rows are Matsui's


# ------------------------------ modeling_solving_milp (mocked solver) ------------------------------
def test_modeling_solving_milp_orchestrates_build_write_and_solve(monkeypatch, tmp_path):
    filename = str(tmp_path / "m.lp")
    captured = {}

    def fake_solve_milp(fname, cfg):
        captured["fname"] = fname
        return [{"w0": 1}]

    monkeypatch.setattr(milp_search.solving, "solve_milp", fake_solve_milp)

    sols = milp_search.modeling_solving_milp("EXISTENCE", ["x >= 0"], [["w0"]], {"filename": filename}, {})

    assert captured["fname"] == filename          # the solver is called with the written model file
    assert (tmp_path / "m.lp").exists()           # the model was written to disk
    assert sols[0]["obj_fun_value"] == sum(sols[0]["rounds_obj_fun_values"])  # objectives attached
