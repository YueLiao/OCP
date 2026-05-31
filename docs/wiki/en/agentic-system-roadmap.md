# OCP Agentic System Roadmap

Language: **English** | [中文](../zh-CN/agentic-system-roadmap.md)

Status: proposal for review. This page is the implementation contract to confirm
before changing the Agent feature set.

## Direction

The next Agentic system should be **text-first**. Users should provide cipher
descriptions as plain text, Markdown, LaTeX fragments, pseudocode, tables, or
structured notes. PDF and image ingestion can remain as convenience helpers, but
they must not be treated as the primary source of truth because visual models can
misread formulas, tables, state layouts, and bit-index conventions.

Primary input formats:

- Plain text copied from papers or notes.
- Markdown with lists, code blocks, and tables.
- LaTeX equations, algorithm environments, and tabular data.
- Pseudocode and assignment-style round descriptions.
- Mixed Chinese/English technical descriptions.
- User-authored structured notes.

## Product Goal

Convert human-readable cipher descriptions into validated OCP `CipherSpec`
objects, then build, analyze, visualize, and generate code only after explicit
user confirmation at risky points.

The system should feel like a careful cryptanalysis assistant, not an automatic
"paper to code" black box. Every inferred parameter, assumption, and ambiguity
should be reviewable.

## Non-Goals

- Do not promise accurate cipher extraction from images or scanned PDFs.
- Do not run code generation, solver jobs, or file-producing workflows without a
  confirmation checkpoint.
- Do not silently invent missing S-boxes, permutation tables, constants, key
  schedules, or bit ordering rules.
- Do not make the web UI depend on one vendor-specific LLM API.

## Core Workflow

1. User provides text, Markdown, LaTeX, or pseudocode.
2. Agent normalizes the text while preserving source spans.
3. Agent extracts candidate `CipherFacts` with confidence and citations.
4. Agent validates completeness, consistency, and OCP supportability.
5. Agent asks targeted clarification questions when information is missing.
6. Agent builds a `CipherSpecDraft`.
7. Agent runs deterministic schema validation and construction smoke checks.
8. Agent presents a human-readable review.
9. User confirms or edits the draft.
10. Agent builds the OCP primitive and offers analysis, code generation, and
    visualization actions.

## Architecture

| Layer | Responsibility | Initial implementation target |
|---|---|---|
| Input | Accept direct text, Markdown, LaTeX, uploaded `.txt`/`.md` files, and pasted notes. | Extend `CipherInput` and text normalization. |
| Extraction | Ask the LLM for structured facts with citations and confidence. | New text-only extraction prompts and parser tests. |
| Validation | Check sizes, word layout, round count, operation support, tables, constants, and key schedule completeness. | Deterministic validators independent of the LLM. |
| Drafting | Map facts into `CipherSpecDraft` and then `CipherSpec`. | Explicit draft schema and conversion helpers. |
| Confirmation | Show assumptions, warnings, missing fields, and proposed `CipherSpec`. | CLI/web review step before build or solve. |
| Execution | Build OCP primitives and run requested workflows after confirmation. | Reuse existing `OCPAgent` skills. |
| Web | Provide editor, provider settings, draft review, job history, and artifacts. | Text workspace before advanced uploads. |
| Storage | Record replayable jobs, prompts, normalized input, draft specs, and output paths. | JSON job records under configurable output dir. |

## Data Contracts

### `CipherInput`

Required fields:

- `raw_text`: original user text.
- `source_type`: `direct_text`, `uploaded_text`, `markdown`, `latex`, or
  `pseudocode`.
- `format_hint`: user-provided or inferred format.
- `language_hint`: `en`, `zh`, `mixed`, or `unknown`.

Important behavior:

- Preserve the original text.
- Normalize LaTeX tokens such as `\oplus`, `\boxplus`, `\lll`, and `\ggg`.
- Keep source span offsets when possible so extracted facts can point back to
  the user's text.

### `CipherFacts`

Facts should be intermediate evidence, not executable code:

- Name and primitive type.
- State size, word size, number of words, and layout.
- Round count and round function steps.
- Supported operations: XOR, AND, OR, NOT, rotations, shifts, modular addition,
  S-box, permutation, matrix/linear layer, round-key addition, constants.
- S-box tables, permutation tables, matrices, constants, and test vectors.
- Key schedule facts for block ciphers.
- Ambiguities, assumptions, unsupported operations, and citations.

### `CipherSpecDraft`

Drafts should be user-reviewable:

- Proposed `CipherSpec` dictionary.
- Blocking validation errors.
- Non-blocking warnings.
- Assumptions made by the Agent.
- Clarification questions.
- `requires_user_confirmation = True` by default.

## Provider Requirements

The provider factory should support:

- OpenAI.
- DeepSeek through its OpenAI-compatible API.
- Generic OpenAI-compatible APIs with configurable `base_url`, model, and API
  key environment variable.
- Anthropic.
- Gemini.
- Local Ollama.

The extraction pipeline should depend only on the internal `LLMProvider`
interface. Provider-specific features should stay behind provider classes.

## Web Requirements

The web UI should expose a real text workspace:

- Large text editor for cipher descriptions.
- Format selector: auto, plain text, Markdown, LaTeX, pseudocode.
- Provider selector with model, base URL, and API key fields.
- "Extract facts", "Validate draft", "Build cipher", "Run analysis", and
  "Generate code" actions as separate steps.
- Draft review panel with assumptions, warnings, missing fields, and citations.
- Editable `CipherSpec` JSON preview.
- Job history and artifact downloads.
- Clear disabled states when a solver or provider is unavailable.

## Safety And Confirmation

Confirmation is required before:

- Building a custom cipher from an LLM-generated draft.
- Writing generated implementations.
- Running solver-backed cryptanalysis.
- Saving or overwriting artifacts.

The confirmation view should show:

- What will be built or executed.
- Which provider/model produced the draft.
- Which assumptions remain.
- Which optional solver backend will be used.
- Where artifacts will be written.

## Testing Plan

- Unit tests for text normalization and LaTeX token handling.
- Parser tests using fixed LLM-like JSON responses.
- Validation tests for missing state size, unsupported operation, malformed
  table, inconsistent word count, and incomplete key schedule.
- Provider factory tests for DeepSeek and OpenAI-compatible defaults.
- Web API tests for provider config, text extraction request validation, and
  confirmation gates.
- Golden examples for simple ARX, SPN, S-box/permutation, and block-cipher key
  schedule inputs.

## Implementation Milestones

1. Finalize schemas for `CipherInput`, `CipherFacts`, and `CipherSpecDraft`.
   Initial dataclasses and deterministic validation helpers are in place.
2. Replace PDF/image-first extraction prompts with text-first extraction prompts.
   Initial text-first facts prompt and parser boundary are in place.
3. Add deterministic validators and draft-to-spec conversion helpers.
   Initial fact validation and draft conversion are in place.
4. Add direct API methods for `extract_cipher_facts`, `draft_cipher_spec`, and
   `confirm_cipher_spec`.
   Initial direct API methods are in place.
5. Add CLI confirmation flow.
   Initial `draft <cipher text>` confirmation flow is in place.
6. Add web text workspace and draft review UI.
   Initial web draft/confirm endpoints and a `Draft` UI action are in place.
7. Add replayable job records and artifact links.
   Initial JSON job records for text-first extraction/draft/confirmation are in place.
8. Relegate PDF/image extraction to an experimental import helper.

## Remaining Build Checklist

The next implementation pass should focus on these concrete gaps:

- Add line/column source spans to `CipherInput` normalization and carry them
  through `CipherFacts` citations.
- Add a manual facts editor path in the web API so users can correct extracted
  facts before `CipherSpecDraft` generation.
- Add a manual `CipherSpec` JSON patch path in the web API with deterministic
  schema validation before confirmation.
- Add golden text examples for one ARX primitive, one SPN primitive, and one
  S-box/permutation primitive.
- Add provider smoke tests that assert DeepSeek and generic OpenAI-compatible
  providers never require provider-specific logic outside the provider layer.
- Add solver capability metadata to web analysis responses before users confirm
  solver-backed jobs.
- Record provider name, model, prompt version, normalized text hash, draft hash,
  and confirmation timestamp in every text-first job record.
- Split web UI actions into persistent panes for input, facts, draft/spec,
  execution, and artifacts once the API supports manual edits.

## Open Questions

- Should `CipherFacts` store source spans as byte offsets, line/column ranges,
  or both?
- Should the web UI allow manual editing of facts, final `CipherSpec`, or both?
- Which minimal set of cipher families should become golden examples first:
  ARX, SPN, Feistel, GFN, or stream ciphers?
- Should solver capability checks be shown before extraction, before analysis,
  or both?
