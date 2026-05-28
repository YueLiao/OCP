# OCP Agentic System Roadmap

Language: **English** | [中文](../zh-CN/agentic-system-roadmap.md)

Status: proposal for review. Do not implement until the codebase refactor
baseline is stable and this roadmap is confirmed.

## Direction Change

The original Agent design mentioned PDF and image extraction. In practice, VLM
recognition is not reliable enough for cryptographic specifications: formulas,
tables, state layouts, and bit-index conventions are easy to misread. The next
Agentic system should prioritize **user-provided text**.

Accepted input should include:

- Plain text copied from papers or notes.
- Markdown descriptions.
- LaTeX fragments, equations, algorithm environments, and tables.
- Pseudocode.
- Mixed Chinese/English descriptions.
- User-authored structured notes.

PDF/image ingestion can remain as a lower-priority helper, but should no longer
be the primary path for accurate cipher specification.

## Product Goal

Build a robust Agentic workflow that converts human-readable cipher descriptions
into validated OCP `CipherSpec` objects, then builds, analyzes, visualizes, and
generates code for the cipher with explicit user confirmation at risky points.

## Core Workflow

1. User provides text, Markdown, LaTeX, or pseudocode.
2. Agent normalizes the text into a canonical internal representation.
3. Agent extracts candidate cipher facts.
4. Agent checks completeness, consistency, and OCP supportability.
5. Agent asks targeted clarification questions when needed.
6. Agent builds a `CipherSpec`.
7. Agent runs static validation and construction smoke tests.
8. Agent presents a human-readable review.
9. User confirms.
10. Agent builds the OCP primitive and offers analysis/codegen/visualization.

## Proposed Architecture

- **Input layer:** normalize text and preserve source spans.
- **Extraction layer:** produce `CipherFacts` with confidence and citations.
- **Validation layer:** check sizes, state layout, round count, operation support, and missing values.
- **Draft layer:** map facts to `CipherSpecDraft`.
- **Confirmation layer:** show a concise review and ask for targeted clarifications.
- **Execution layer:** build OCP objects and run analysis only after confirmation.
- **Web layer:** provide text editor, provider settings, run history, and artifact downloads.

## Provider Requirements

The system should support OpenAI, DeepSeek, generic OpenAI-compatible APIs,
Anthropic, Gemini, and local Ollama models through one provider factory.

## Todo

- Design `CipherFacts` and `CipherSpecDraft` schemas.
- Add text-only extraction prompts and deterministic parser tests.
- Add a web text workspace with provider configuration.
- Add confirmation checkpoints before code execution or solver runs.
- Add replayable job records for generated artifacts.
