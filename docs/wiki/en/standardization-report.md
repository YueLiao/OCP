# Standardization Report

Language: **English** | [中文](../zh-CN/standardization-report.md)

This page records the repository standardization pass. The guiding rule was to
preserve cryptanalysis behavior while making the project easier to run, test,
document, and extend.

## Diagnosis Checklist

| Area | Status | Notes |
|---|---:|---|
| Repository structure | Needs work | Core engine, tests, agent, docs, and generated files are clearer; deeper module boundaries still need work. |
| Architecture boundaries | Needs work | Agent provider creation, output paths, attack helpers, operator helpers, primitive layer/link helpers, verbose-aware diagnostics, and solver capability reporting were tightened. |
| Public interfaces | Needs work | `OCPAgent` and provider launchers are clearer; operator/model APIs still need typed contracts over time. |
| Readability | Needs work | Low-risk cleanup completed across operators and primitive scaffolding; attack modules and solver/modeling boundaries remain complex. |
| Style tooling | Pass | `pyproject.toml` defines package metadata and pytest settings. |
| Error handling | Needs work | Optional dependency failures and tool diagnostics are less noisy; broad exception handling remains in some paths. |
| Configuration | Pass | Output location is centralized through `tools.paths.get_files_dir()` and supports `OCP_FILES_DIR`. |
| Tests | Pass | Core smoke tests are deterministic; solver/generated tests are guarded by explicit pytest flags. |
| Documentation | Pass | README/wiki pages now use language switch links instead of mixed bilingual pages. |
| Packaging | Pass | Editable install and `ocp-agent` console entry point are configured. |
| Performance | Needs work | Optional backend imports are lazier; S-box, matrix, and primitive layer lookup helpers have focused optimizations. |

## Completed Changes

- Added packaging metadata, optional dependency groups, and the `ocp-agent` console script.
- Added CI smoke tests for Python 3.10 and 3.11.
- Added deterministic unit tests around Agent APIs, paths, providers, search I/O, operator core behavior, and text input normalization.
- Centralized runtime output paths with `OCP_FILES_DIR`.
- Reduced import-time optional dependency noise for solver/modeling backends.
- Added DeepSeek and generic OpenAI-compatible provider support.
- Added text-first cipher input dataclasses, Markdown/LaTeX normalization, deterministic fact validation, prompt/parse boundaries, and draft-to-spec conversion helpers.
- Added direct `OCPAgent` APIs for text-first fact extraction, draft creation, and explicit confirmation before building.
- Expanded the text-first Agentic roadmap into a reviewable implementation contract for schemas, web flow, providers, safety gates, and tests.
- Optimized S-box and GF(2) matrix helpers, and fixed PMR block assembly.
- Consolidated repeated operator model helpers across Boolean, modular, S-box, and matrix operators.
- Refined S-box weighted truth-table generation, matrix bit-model generation, explicit modular arithmetic, and unfinished operator abstractions.
- Consolidated primitive layer Equal constraints, graph iteration, input/output link helpers, and faster layer output lookups.
- Routed attack/solver progress messages through verbose-aware logging and converted tool diagnostics to Python warnings.
- Added explicit solver capability reporting for optional MILP/SAT backends and documented the current solver fallbacks.
- Replaced repeated constraint/objective list concatenation in attack/model generation paths with explicit in-place extension.
- Clarified legacy operator scripts as manual experiments.
- Split documentation into English and Chinese pages with language switch links.

## Validation

```bash
conda run -n ocp python -m compileall agent primitives attacks solving tools operators web run_agent.py
conda run -n ocp python -m pytest
conda run -n ocp ocp-agent --help
git diff --check
```

Latest default pytest status: `83 passed, 106 skipped`.

## Next Work

1. Add CLI confirmation flow for text-first cipher drafts.
2. Profile model generation before deeper performance rewrites.
3. Continue narrowing broad exception handling in solver/model generation paths.
