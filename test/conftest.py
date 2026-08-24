from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_addoption(parser):
    parser.addoption(
        "--run-legacy-operators",
        action="store_true",
        default=False,
        help=(
            "deprecated: test/operators contains script-style experiments and "
            "is skipped under pytest; run those files directly instead"
        ),
    )
    parser.addoption(
        "--run-solver",
        action="store_true",
        default=False,
        help="run tests that require external MILP/SAT solver backends",
    )
    parser.addoption(
        "--run-implementations",
        action="store_true",
        default=False,
        help="run generated implementation tests, which may compile or execute generated files",
    )


def pytest_collection_modifyitems(config, items):
    skip_legacy = pytest.mark.skip(
        reason=(
            "legacy script-style operator experiment; run directly with "
            "`python test/operators/<file>.py`"
        )
    )
    skip_solver = pytest.mark.skip(
        reason="external solver-dependent test; pass --run-solver to run"
    )
    skip_implementations = pytest.mark.skip(
        reason="generated implementation test; pass --run-implementations to run"
    )

    for item in items:
        # `item.path` (pathlib.Path) exists on pytest >= 7.0; older pytest only has
        # `item.fspath` (py.path.local). Support both so the suite collects on either.
        raw = getattr(item, "path", None)
        if raw is None:
            raw = item.fspath
        try:
            rel_parts = Path(str(raw)).resolve().relative_to(ROOT).parts
        except ValueError:
            rel_parts = Path(str(raw)).parts
        if rel_parts[:2] == ("test", "operators"):
            item.add_marker(pytest.mark.legacy_script)
            item.add_marker(skip_legacy)
            continue
        if rel_parts[:2] == ("test", "differential_cryptanalysis") and not config.getoption("--run-solver"):
            item.add_marker(pytest.mark.solver)
            item.add_marker(skip_solver)
        if rel_parts[:2] == ("test", "implementations") and not config.getoption("--run-implementations"):
            item.add_marker(pytest.mark.implementation)
            item.add_marker(skip_implementations)
