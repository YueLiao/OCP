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

## Local Output Isolation

```bash
OCP_FILES_DIR=/tmp/ocp-files python -m pytest --run-implementations
```

This prevents generated models, trails, and implementation files from mixing
with tracked repository content.
