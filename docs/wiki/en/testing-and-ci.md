# Testing and CI

Language: **English** | [中文](../zh-CN/testing-and-ci.md)

## Fast Default

```bash
python -m pytest
```

The default suite runs standardized lightweight tests and skips:

- Legacy script-style operator experiments.
- Generated implementation tests.
- Solver-dependent cryptanalysis tests.

## Optional Suites

```bash
python -m pytest --run-implementations
python -m pytest --run-solver
```

Use these suites when touching the corresponding subsystem and after installing
the matching optional backends.

Legacy operator files under `test/operators/` are manual experiment scripts and
are intentionally skipped under pytest:

```bash
python test/operators/test_xor.py
```

## CI

GitHub Actions runs:

```bash
python -m pip install -e ".[test]"
python -m compileall agent primitives attacks solving tools operators
python -m pytest
```

CI intentionally avoids optional solver dependencies. Solver-backed tests should
be added as a separate workflow after backend setup is stable.

## Solver Capability Checks

Optional solver backends can be checked without importing native solver modules:

```python
from solving.solving import is_solver_available, solver_capabilities

solver_capabilities()
is_solver_available("milp", "DEFAULT")
is_solver_available("sat", "Glucose3")
```

`DEFAULT` MILP maps to Gurobi. `DEFAULT` SAT and named PySAT engines map to the
PySAT backend. The OR-Tools SAT route is reserved but not implemented yet, so it
is reported as unavailable for execution even when its Python packages are
installed.

## Local Output Isolation

```bash
OCP_FILES_DIR=/tmp/ocp-files python -m pytest --run-implementations
```

This prevents generated models, trails, and implementation files from mixing
with tracked repository content.

## Model Generation Profiling

For focused performance work, enable opt-in model generation profiling through
`config_model`:

```python
config_model = {"profile_model_generation": True}
```

After model construction, `config_model["model_generation_profile"]` contains
per-operator call counts, generated constraint counts, and elapsed time.
Parsed constraint templates are cached by filename and modification time, so
template regeneration invalidates the cache automatically.
