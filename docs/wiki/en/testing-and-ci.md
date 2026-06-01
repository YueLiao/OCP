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

The solver suite includes an identity-elision SAT smoke test when PySAT is
available. It builds an elided Forro model, solves it, and verifies that trail
extraction can recover values for variables removed by the alias pass:

```bash
python -m pytest test/unit/test_performance_regressions.py::test_identity_elision_sat_solver_smoke_preserves_trail_lookup --run-solver
```

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

## Source Distribution

The source distribution is expected to include:

- Root README and license files.
- `requirements*.txt` dependency sets.
- Wiki-ready Markdown documentation under `docs/`.
- Tracked S-box and matrix modeling templates under `files/*_modeling/`.

`MANIFEST.in` records this explicitly so release archives contain the runtime
templates needed by source-tree workflows.

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

Attack configuration is normalized at the shared frontend boundary:

- `config_model["model_type"]` accepts `milp` or `sat` and is normalized to
  lowercase.
- An explicit `config_model["filename"]` is preserved. If omitted, OCP writes to
  the runtime `OCP_FILES_DIR` location.
- `config_solver["solver"]` defaults to `DEFAULT`.
- `config_solver["solution_number"]`, when provided, must be a positive integer.

Solver wrappers expose `normalize_milp_solver_name()` and
`normalize_sat_solver_name()` for explicit validation, while
`is_solver_available()` remains a quiet capability check and returns `False` for
unknown solver names.

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

For a repeatable local snapshot without solving:

```bash
python -m tools.profile_model_generation present:1 forro:1
python -m tools.profile_model_generation chacha:1 salsa:1 forro:1 --identity-elision
```

Profile cases use `name` or `name:rounds`; rounds and `--top-limit` must be
positive integers.

The command emits JSON with primitive build time, model generation time,
constraint counts, and per-operator hotspots. It is intended for comparing
small optimization changes before running heavier solver workflows.
