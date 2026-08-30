"""Unit tests for tools/sat_search.py - objective-target parsing, decimal-objective
enumeration, the numerical-CNF encoder, and SAT model writing. (Split out of the former
test_search_io.py; the MILP counterpart lives in test_milp_search.py.)
"""
import pytest

import tools.sat_search as sat_search
from tools.sat_search import (
    create_numerical_cnf,
    decimal_objective_combinations,
    parse_objective_target,
    write_sat_model,
)


def test_parse_objective_target():
    assert parse_objective_target("OPTIMAL") == ("OPTIMAL", None)
    assert parse_objective_target("EXISTENCE") == ("EXISTENCE", None)
    assert parse_objective_target("AT MOST 3") == ("AT MOST", 3.0)
    assert parse_objective_target("EXACTLY 2.5") == ("EXACTLY", 2.5)
    assert parse_objective_target("AT LEAST 1") == ("AT LEAST", 1.0)


def test_parse_objective_target_rejects_malformed_and_unknown():
    with pytest.raises(ValueError, match="Invalid format"):
        parse_objective_target("AT MOST x")
    with pytest.raises(ValueError, match="Unsupported objective_target"):
        parse_objective_target("NOPE")


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


def test_write_sat_model_skips_empty_clauses_with_warning(tmp_path, capsys):
    filename = tmp_path / "m.cnf"
    write_sat_model(constraints=["a -b", "", "  ", "c"], filename=str(filename))
    assert "skipping 2 empty clause" in capsys.readouterr().out
    assert filename.read_text().startswith("p cnf 3 2\n")  # empties dropped: 3 vars, 2 clauses


def test_write_sat_model_tolerates_none_filename(monkeypatch, tmp_path):
    # regression: filename=None falls back to "sat.cnf" (symmetric with write_milp_model)
    monkeypatch.chdir(tmp_path)
    write_sat_model(constraints=["a"], filename=None)
    assert (tmp_path / "sat.cnf").exists()


def test_modeling_solving_normalizes_none_solutions_to_empty_list(monkeypatch, tmp_path):
    # solve_sat returns None when the backend is unavailable; modeling_solving must yield []
    monkeypatch.setattr(sat_search.solving, "solve_sat", lambda *a, **k: None)
    result = sat_search.modeling_solving([], [], {"filename": str(tmp_path / "m.cnf")}, {})
    assert result == []
