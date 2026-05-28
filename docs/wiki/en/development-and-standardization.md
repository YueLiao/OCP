# Development and Standardization

Language: **English** | [中文](../zh-CN/development-and-standardization.md)

## Project Shape

OCP is a mixed research/library/tooling repository. Public usage currently flows
through direct module imports, scripts, the Agent API, and the web UI.

## Behavioral Invariants

When refactoring, preserve:

- Existing primitive factory names such as `SPECK_BLOCKCIPHER`.
- Existing package/module import paths.
- Operator model-version semantics.
- MILP/SAT objective names and constraint formats.
- Default output behavior under `files/`, unless `OCP_FILES_DIR` is set.
- Test vector behavior for generated implementations.

## Recommended Cleanup Phases

### Phase 1: Safe Hygiene

- Keep dependency metadata and generated-output ignore rules current.
- Improve optional dependency errors at API boundaries.
- Reduce import-time side effects from optional solver/modeling backends.
- Keep README/wiki pages language-separated with switch links.
- Run compile and smoke checks after each coherent change.

### Phase 2: Interfaces and Tests

- Centralize output directories and solver defaults.
- Add focused tests for Agent direct API behavior.
- Split LLM parsing tests from skill execution tests using fake providers.
- Make web UI session management explicit.
- Keep optional solver/generated tests behind explicit pytest flags.

### Phase 3: Deeper Architecture

- Move generated modeling templates out of tracked runtime output only through a dedicated migration.
- Continue centralizing solver capability detection.
- Profile constraint generation before deeper performance rewrites.
- Split large operator/model files only under focused regression tests.

## Performance Opportunities

Potential acceleration points:

1. Cache S-box DDT/LAT-derived constraints across identical S-box classes and model versions.
2. Reuse generated S-box and matrix template constraints across equivalent operators.
3. Avoid repeated complete `functions/rounds/layers/positions` expansion for identical attack scopes.
4. Keep optional backend imports lazy.
5. Prefer text-first extraction over whole-document LLM prompts.

## Validation Commands

```bash
python -m pip install -e ".[agent,test]"
python -m compileall agent primitives attacks solving tools operators
python -m pytest

# Optional suites:
python -m pytest --run-implementations
python -m pytest --run-solver

# Manual legacy operator experiments:
python test/operators/test_xor.py
```
