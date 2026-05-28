import os
import subprocess
import sys

import solving.solving as solving


def test_solving_module_import_is_quiet():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    result = subprocess.run(
        [sys.executable, "-c", "import solving.solving"],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "[WARNING]" not in result.stdout
    assert "[WARNING]" not in result.stderr


def test_solver_missing_backend_messages_can_be_silenced(monkeypatch, capsys):
    monkeypatch.setattr(solving, "_load_gurobi", lambda: None)
    monkeypatch.setattr(solving, "_load_pysat", lambda: (None, None))

    assert solving.solve_milp_gurobi("missing.lp", {"verbose": False}) == []
    assert solving.solve_sat_pysat("missing.cnf", {}, {"verbose": False}) is None

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_solver_missing_backend_messages_are_verbose_by_default(monkeypatch, capsys):
    monkeypatch.setattr(solving, "_load_gurobi", lambda: None)

    assert solving.solve_milp_gurobi("missing.lp", {}) == []

    assert "gurobipy module can't be loaded" in capsys.readouterr().out
