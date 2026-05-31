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
| Configuration | Pass | Output location is centralized through runtime `tools.paths.get_files_dir()` calls and supports `OCP_FILES_DIR`. |
| Tests | Pass | Core smoke tests are deterministic; solver/generated tests are guarded by explicit pytest flags. |
| Documentation | Pass | README/wiki pages now use language switch links instead of mixed bilingual pages. |
| Packaging | Pass | Editable install and `ocp-agent` console entry point are configured. |
| Performance | Needs work | Optional backend imports are lazier; S-box, matrix, and primitive layer lookup helpers have focused optimizations. |

## Completed Changes

- Added packaging metadata, optional dependency groups, and the `ocp-agent` console script.
- Added CI smoke tests for Python 3.10 and 3.11.
- Added deterministic unit tests around Agent APIs, paths, providers, search I/O, operator core behavior, and text input normalization.
- Centralized runtime output paths with `OCP_FILES_DIR`.
- Removed import-time attack output path snapshots so model and trail filenames honor runtime `OCP_FILES_DIR` changes.
- Removed import-time runtime path snapshots from logic minimization and default agent code generation output.
- Routed default `OCPAgent` code generation and visualization outputs through runtime `OCP_FILES_DIR`.
- Added structured pass/fail summaries to agent code generation test results while preserving legacy result entries.
- Added artifact links for agent code generation and visualization outputs.
- Wrapped agent code-generation output directory failures inside `SkillResult`.
- Wrapped agent visualization output directory failures inside `SkillResult`.
- Made artifact registry IDs deterministic across Python processes.
- Added a session-scoped web artifact download endpoint and sidebar download links.
- Deduplicated session artifact records by stable artifact ID.
- Reduced import-time optional dependency noise for solver/modeling backends.
- Added analysis skill boundary validation for unsupported model types.
- Added analysis skill boundary validation for non-positive solution counts.
- Added built-in cipher version validation at the agent instantiation boundary.
- Restricted Agent SHACAL2 instantiation to the implemented 256-bit variant and clarified Trivium catalog status.
- Added a primitive support status page for partial SHACAL2 and prototype Trivium coverage.
- Narrowed trail solution-bit error handling to numeric conversion failures.
- Added DeepSeek and generic OpenAI-compatible provider support.
- Added text-first cipher input dataclasses, Markdown/LaTeX normalization, deterministic fact validation, prompt/parse boundaries, and draft-to-spec conversion helpers.
- Reused the shared LLM JSON response parser inside `AgentCore` extraction flows.
- Added direct `OCPAgent` APIs for text-first fact extraction, draft creation, and explicit confirmation before building.
- Added a CLI `draft <cipher text>` review-and-confirm flow for text-first cipher drafts.
- Added web text draft/confirm endpoints and a `Draft` UI action for review-before-build workflows.
- Aligned web provider API-key resolution with CLI environment-variable defaults.
- Added explicit 400 responses for missing JSON bodies on web JSON endpoints.
- Returned HTTP 400 for invalid web provider configuration errors.
- Hid low-level provider setup, chat, and upload processing exception details from web API responses.
- Returned file-extraction data and artifact links from the web upload endpoint.
- Prevented missing temporary upload files from masking web upload responses during cleanup.
- Added replayable JSON job records and artifact links for text-first extraction, draft, and confirmation.
- Expanded the text-first Agentic roadmap into a reviewable implementation contract for schemas, web flow, providers, safety gates, and tests.
- Optimized S-box and GF(2) matrix helpers, and fixed PMR block assembly.
- Consolidated repeated operator model helpers across Boolean, modular, S-box, and matrix operators.
- Refined S-box weighted truth-table generation, matrix bit-model generation, explicit modular arithmetic, and unfinished operator abstractions.
- Routed matrix truncated-model fallback diagnostics through Python warnings and runtime output paths.
- Consolidated primitive layer Equal constraints, graph iteration, input/output link helpers, and faster layer output lookups.
- Centralized Forro state dimensions, default subround counts, keystream metadata, and factory variable creation.
- Routed attack/solver progress messages through verbose-aware logging and converted tool diagnostics to Python warnings.
- Added explicit solver capability reporting for optional MILP/SAT backends and documented the current solver fallbacks.
- Ensured PySAT solver instances are released even when solving raises an exception.
- Narrowed runtime resource monitor exception handling to psutil/OS failures.
- Narrowed SCIP solver failure handling so unexpected programming errors propagate.
- Narrowed PySAT cardinality fallback handling so unexpected programming errors propagate.
- Replaced assertion-based attack entry validation with shared explicit `ValueError` checks.
- Replaced repeated constraint/objective list concatenation in attack/model generation paths with explicit in-place extension.
- Added opt-in model generation profiling to record per-operator constraint counts and timings.
- Added clearer validation and CLI usage errors for model-generation profiler inputs.
- Centralized model-generation profiling config keys.
- Split model-generation profiling and identity-elision state helpers out of `tools.model_constraints` while preserving compatibility imports.
- Split PySAT cardinality backend helpers out of `tools.model_constraints` while preserving compatibility wrappers.
- Split constraint template generation, caching, and instantiation helpers out of `tools.model_constraints` while preserving public imports.
- Split Boolean XOR/NXOR and matrix constraint helpers out of `tools.model_constraints` while preserving public imports.
- Split sequential SAT encoding and Matsui search constraint helpers out of `tools.model_constraints` while preserving public imports.
- Split predefined SAT/MILP constraint builders out of `tools.model_constraints` while preserving public imports.
- Split model scope, version assignment, and round model generation helpers out of `tools.model_constraints` while preserving public imports.
- Routed internal operator imports to the new bit-constraint and model-template modules instead of the compatibility facade.
- Routed attack/search/profiler imports to the new model-configuration, predefined-constraint, search-constraint, and state modules.
- Split objective-target parsing and SAT/MILP objective constraint builders into `tools.objective_targets`.
- Split MILP search model-constraint construction, objective selection, and solution objective post-processing into focused helpers.
- Split optimal SAT search-strategy parsing into `tools.objective_targets`.
- Centralized SAT decimal-objective combination lookup in `tools.objective_targets`.
- Consolidated repeated SAT objective-constraint solve calls behind a private helper.
- Centralized SAT optimal-search strategy to `SUM_*` constraint-type mapping.
- Made decimal SAT objective filtering skip malformed solutions that lack `obj_fun_value`.
- Split SAT CNF and MILP LP model serialization helpers into `tools.model_io`.
- Reduced symbolic CNF variable extraction overhead by collecting variables per literal instead of joining the full model first.
- Cached parsed constraint templates by file modification time to reduce repeated S-box template loading.
- Replaced repeated per-variable template regex passes with single-pass token substitution during constraint template instantiation.
- Added opt-in identity elision for conservative internal Equal chains in model generation.
- Verified identity-elision trail extraction, MILP/SAT generation, and primitive-graph boundaries.
- Cleared identity-elision private state when reused model configs disable the option.
- Centralized identity-elision private config keys for model generation and trail extraction.
- Reclassified PDF/image extraction as an experimental import helper and disabled web upload auto-build.
- Added explicit page-range validation for experimental file extraction.
- Clarified legacy operator scripts as manual experiments.
- Migrated Equal implementation and MILP equivalence coverage from legacy operator scripts into focused pytest coverage.
- Split documentation into English and Chinese pages with language switch links.

## Validation

```bash
conda run -n ocp python -m compileall agent primitives attacks solving tools operators web run_agent.py
conda run -n ocp python -m pytest
conda run -n ocp ocp-agent --help
git diff --check
```

Latest default pytest status: `170 passed, 106 skipped`.

## Next Work

1. Use profiling results to prioritize deeper model generation optimizations.
2. Continue narrowing broad exception handling in solver/model generation paths.
3. Continue improving web draft review ergonomics and artifact browsing.
