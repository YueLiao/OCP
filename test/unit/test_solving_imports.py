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


def test_solver_name_normalization_is_explicit():
    assert solving.normalize_milp_solver_name("default") == "GUROBI"
    assert solving.normalize_milp_solver_name("scip") == "SCIP"
    assert solving.normalize_sat_solver_name("default") == "DEFAULT"
    assert solving.normalize_sat_solver_name("glucose3") == "Glucose3"
    assert solving.normalize_sat_solver_name("ortools") == "ORTools"

    for normalizer, solver_name in (
        (solving.normalize_milp_solver_name, "not-milp"),
        (solving.normalize_sat_solver_name, "not-sat"),
    ):
        try:
            normalizer(solver_name)
        except ValueError as exc:
            assert "Unsupported solver" in str(exc)
        else:
            raise AssertionError("Expected unsupported solver to raise ValueError")


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


def test_pysat_solver_is_released_when_solving_raises(monkeypatch):
    class FakeCNF:
        clauses = [[1]]

        def __init__(self, filename):
            self.filename = filename

    class FailingSolver:
        deleted = False

        def append_formula(self, clauses):
            self.clauses = clauses

        def solve(self):
            raise RuntimeError("boom")

        def delete(self):
            type(self).deleted = True

    monkeypatch.setattr(solving, "_load_pysat", lambda: (FakeCNF, FailingSolver))

    try:
        solving.solve_sat_pysat("model.cnf", {"x": 1}, {"verbose": False})
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("Expected PySAT solve error to propagate")

    assert FailingSolver.deleted is True


def test_solve_sat_passes_normalized_solver_name_to_pysat(monkeypatch):
    class FakeCNF:
        clauses = []

        def __init__(self, filename):
            self.filename = filename

    class RecordingSolver:
        name = None

        def __init__(self, name=None):
            type(self).name = name

        def append_formula(self, clauses):
            self.clauses = clauses

        def solve(self):
            return False

        def delete(self):
            return None

    monkeypatch.setattr(solving, "_load_pysat", lambda: (FakeCNF, RecordingSolver))

    config_solver = {"solver": "glucose3", "verbose": False}
    assert solving.solve_sat("model.cnf", {}, config_solver) == []
    assert config_solver["solver"] == "Glucose3"
    assert RecordingSolver.name == "Glucose3"


def test_solver_wrappers_preserve_empty_config_dicts(monkeypatch):
    monkeypatch.setattr(solving, "solve_milp_gurobi", lambda filename, config_solver: [])
    monkeypatch.setattr(solving, "solve_sat_pysat", lambda filename, variable_map, config_solver: [])

    milp_config = {}
    sat_config = {}

    assert solving.solve_milp("model.lp", milp_config) == []
    assert solving.solve_sat("model.cnf", {}, sat_config) == []

    assert milp_config["solver"] == "GUROBI"
    assert "resource_usage" in milp_config
    assert sat_config["solver"] == "DEFAULT"
    assert "resource_usage" in sat_config


def test_solver_wrappers_reject_invalid_config_solver_types():
    for solver_fn, args in (
        (solving.solve_milp, ("model.lp", [])),
        (solving.solve_sat, ("model.cnf", {}, [])),
    ):
        try:
            solver_fn(*args)
        except ValueError as exc:
            assert "Invalid config_solver" in str(exc)
        else:
            raise AssertionError("Expected invalid config_solver to raise ValueError")


def test_scip_solver_errors_return_empty_solution_list(monkeypatch):
    class FailingModel:
        def readProblem(self, filename):
            raise RuntimeError("solver failed")

    monkeypatch.setattr(solving, "_load_scip_model", lambda: FailingModel)
    monkeypatch.setattr(solving, "_scip_error_types", lambda: (RuntimeError,))

    assert solving.solve_milp_scip("model.lp", {"verbose": False}) == []


def test_scip_programming_errors_are_not_suppressed(monkeypatch):
    class BrokenModel:
        def readProblem(self, filename):
            raise TypeError("programming error")

    monkeypatch.setattr(solving, "_load_scip_model", lambda: BrokenModel)
    monkeypatch.setattr(solving, "_scip_error_types", lambda: (RuntimeError,))

    try:
        solving.solve_milp_scip("model.lp", {"verbose": False})
    except TypeError as exc:
        assert str(exc) == "programming error"
    else:
        raise AssertionError("Expected unexpected SCIP programming error to propagate")
