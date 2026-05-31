from pathlib import Path

import pytest

from tools.milp_search import write_milp_model
from tools.objective_targets import (
    decimal_objective_combinations,
    parse_optimal_sat_search_strategy,
)
import tools.sat_search as sat_search
from tools.sat_search import create_numerical_cnf, parse_objective_target, write_sat_model
from tools.search_reporting import is_verbose, log_search_summary


def test_parse_objective_target():
    assert parse_objective_target("OPTIMAL") == ("OPTIMAL", None)
    assert parse_objective_target("AT MOST 3") == ("AT MOST", 3.0)
    assert parse_objective_target("EXACTLY 2.5") == ("EXACTLY", 2.5)


def test_parse_optimal_sat_search_strategy():
    plan = parse_optimal_sat_search_strategy("DECREASING FROM EXACTLY 7")

    assert plan.constraint_strategy == "EXACTLY"
    assert plan.start_value == 7
    assert plan.step == -1
    assert plan.end_value == -1
    assert plan.mode == "DECREASING"


def test_decimal_objective_combinations_requires_sbox_table():
    with pytest.raises(ValueError, match="Missing Sbox or table"):
        decimal_objective_combinations({}, 0, 1)


def test_at_most_decimal_search_skips_solutions_without_objective(monkeypatch):
    solution_batches = iter([[{}], []])

    monkeypatch.setattr(sat_search, "gen_sat_constraints_from_objective_target", lambda *args, **kwargs: [])
    monkeypatch.setattr(sat_search, "modeling_solving", lambda *args, **kwargs: next(solution_batches))
    monkeypatch.setattr(sat_search, "decimal_objective_combinations", lambda *args, **kwargs: [])

    solutions = sat_search.modeling_solving_at_most(
        [],
        [],
        {"decimal_objective_function": True, "verbose": False},
        {},
        1,
    )

    assert solutions == []


def test_create_numerical_cnf_assigns_stable_sorted_variable_ids():
    num_vars, variable_map, clauses = create_numerical_cnf(["b -a", "-b c"])

    assert num_vars == 3
    assert variable_map == {"a": 1, "b": 2, "c": 3}
    assert clauses == ["2 -1", "-2 3"]


def test_write_sat_model_accepts_missing_constraints(tmp_path):
    filename = tmp_path / "empty.cnf"

    metadata = write_sat_model(filename=str(filename))

    assert metadata == {"variable_map": {}}
    assert filename.read_text() == "p cnf 0 0\n"


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


def test_search_reporting_can_be_silenced(capsys):
    assert not is_verbose({"verbose": False})

    log_search_summary("Title", [], {"verbose": False, "filename": "x"}, {})

    assert capsys.readouterr().out == ""
