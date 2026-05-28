# Standardization Report

Language: **English** | [中文](../zh-CN/standardization-report.md)

This page records the repository standardization pass. The guiding rule was to
preserve cryptanalysis behavior while making the project easier to run, test,
document, and extend.

## Diagnosis Checklist

| Area | Status | Notes |
|---|---:|---|
| Repository structure | Needs work | Core engine, tests, agent, docs, and generated files are clearer; deeper module boundaries still need work. |
| Architecture boundaries | Needs work | Agent provider creation, output paths, and shared attack helpers were tightened; solver/modeling layers still mix logging, I/O, and domain logic in places. |
| Public interfaces | Needs work | `OCPAgent` and provider launchers are clearer; operator/model APIs still need typed contracts over time. |
| Readability | Needs work | Low-risk cleanup completed; large files such as `Sbox.py`, `matrix.py`, and attack modules remain complex. |
| Style tooling | Pass | `pyproject.toml` defines package metadata and pytest settings. |
| Error handling | Needs work | Optional dependency failures are less noisy; broad exception handling remains in some paths. |
| Configuration | Pass | Output location is centralized through `tools.paths.get_files_dir()` and supports `OCP_FILES_DIR`. |
| Tests | Pass | Core smoke tests are deterministic; solver/generated tests are guarded by explicit pytest flags. |
| Documentation | Pass | README/wiki pages now use language switch links instead of mixed bilingual pages. |
| Packaging | Pass | Editable install and `ocp-agent` console entry point are configured. |
| Performance | Needs work | Optional backend imports are lazier; S-box and matrix helpers have focused optimizations. |

## Completed Changes

- Added packaging metadata, optional dependency groups, and the `ocp-agent` console script.
- Added CI smoke tests for Python 3.10 and 3.11.
- Added deterministic unit tests around Agent APIs, paths, providers, search I/O, operator core behavior, and text input normalization.
- Centralized runtime output paths with `OCP_FILES_DIR`.
- Reduced import-time optional dependency noise for solver/modeling backends.
- Added DeepSeek and generic OpenAI-compatible provider support.
- Added text-first cipher input dataclasses and Markdown/LaTeX normalization.
- Optimized S-box and GF(2) matrix helpers, and fixed PMR block assembly.
- Clarified legacy operator scripts as manual experiments.
- Split documentation into English and Chinese pages with language switch links.

## Validation

```bash
conda run -n ocp python -m compileall agent primitives attacks solving tools operators web run_agent.py
conda run -n ocp python -m pytest
conda run -n ocp ocp-agent --help
git diff --check
```

Latest default pytest status: `48 passed, 106 skipped`.

## Next Work

1. Continue low-risk operator cleanup with focused regression tests.
2. Add the full text-first agentic extraction design around `CipherInput`, `CipherFacts`, and `CipherSpecDraft`.
3. Profile model generation before deeper performance rewrites.
