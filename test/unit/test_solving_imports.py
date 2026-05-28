import os
import subprocess
import sys

import solving.solving as solving


def test_solver_capabilities_are_queryable_without_importing_backends(monkeypatch):
    available_modules = {"gurobipy", "pysat"}

    monkeypatch.setattr(
        solving,
        "find_spec",
        lambda module_name: object() if module_name in available_modules else None,
    )

    capabilities = solving.solver_capabilities()

    assert capabilities["default"] == {"milp": "GUROBI", "sat": "PySAT"}
    assert capabilities["milp"]["GUROBI"]["available"] is True
    assert capabilities["milp"]["SCIP"]["available"] is False
    assert capabilities["sat"]["PySAT"]["available"] is True
    assert capabilities["sat"]["ORTools"]["available"] is False
    assert capabilities["sat"]["ORTools"]["implemented"] is False


def test_is_solver_available_respects_defaults_and_implemented_backends(monkeypatch):
    available_modules = {"gurobipy", "pysat", "ortools", "ortoolslpparser"}

    monkeypatch.setattr(
        solving,
        "find_spec",
        lambda module_name: object() if module_name in available_modules else None,
    )

    assert solving.is_solver_available("milp", "DEFAULT") is True
    assert solving.is_solver_available("milp", "SCIP") is False
    assert solving.is_solver_available("sat", "DEFAULT") is True
    assert solving.is_solver_available("sat", "Glucose3") is True
    assert solving.is_solver_available("sat", "ORTools") is False
    assert solving.is_solver_available("sat", "UnknownSAT") is False


def test_is_solver_available_rejects_unknown_solver_kind():
    try:
        solving.is_solver_available("cp", "DEFAULT")
    except ValueError as exc:
        assert "Unsupported solver kind" in str(exc)
    else:
        raise AssertionError("Expected unknown solver kind to raise ValueError")


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
