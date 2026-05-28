# Agentic Architecture

Language: **English** | [中文](../zh-CN/agentic-architecture.md)

This page describes the intended Agent architecture after the current
standardization pass. The goal is a usable, stable, text-first cryptanalysis
assistant with clear confirmation points and replayable artifacts.

## Layers

| Layer | Responsibility |
|---|---|
| Provider | OpenAI, DeepSeek, OpenAI-compatible, Anthropic, Gemini, and Ollama adapters behind `LLMProvider`. |
| Planner | Convert user text into skill calls or a draft/review workflow. |
| Skill executor | Execute one `SkillRequest` at a time through `AgentCore` and return `SkillResult`. |
| Validator | Deterministically validate `CipherInput`, `CipherFacts`, `CipherSpecDraft`, and `CipherSpec`. |
| Verifier | Run lightweight smoke checks before risky build, solve, codegen, or visualization steps. |
| Artifact manager | Return generated files through `artifact_links` and record replayable JSON jobs. |
| Session | Store current cipher, pending facts, pending draft, job records, recent results, and execution trace entries. |
| Web/API | Present stable JSON responses and explicit actions for draft, confirm, analyze, code, and visualize. |

## Error Boundaries

User-facing boundaries should classify errors before returning them:

- Invalid or missing JSON request body: HTTP 400 with `error_code=invalid_json`.
- Missing provider/API key/config: HTTP 400 with provider-specific messages.
- Empty text or unsupported file type: HTTP 400 or `SkillResult(success=False)`.
- LLM parse failure: `SkillResult(success=False)` with a parseable-facts message.
- Internal skill failures: wrapped as `SkillResult(success=False)` at the skill boundary.
- Unexpected route/provider setup failures: HTTP 500 with `error_code` for diagnostics.

`/api/analyze`, `/api/code`, and `/api/visualize` require `confirmed=true`.
The web UI prompts before sending this flag because those actions can run
external solvers or write artifacts.

## Standard Response Shape

Web endpoints that execute skills should return:

```json
{
  "success": true,
  "skill": "code_generation",
  "summary": "Generated ...",
  "error": null,
  "data": {},
  "artifact_links": [],
  "context": {}
}
```

`artifact_links` is the stable place for generated code, trail JSON/TXT files,
visualization PDFs, and job records.

The Agent also expands links into structured `artifacts`:

```json
{
  "id": "stable-ish id",
  "label": "generated_code",
  "path": "/tmp/ocp-files/SPECK32_64.py",
  "type": "source",
  "source_skill": "code_generation",
  "exists": true,
  "created_at": "2026-05-28T..."
}
```

`/api/status` returns recent trace entries and the session artifact registry for
the web sidebar.

## Text-First Flow

1. User submits plain text, Markdown, LaTeX, or pseudocode.
2. `extract_cipher_facts()` asks the configured provider for structured facts.
3. Deterministic validators classify blocking errors and warnings.
4. `draft_cipher_spec()` creates a reviewable draft.
5. User confirms the draft.
6. `confirm_cipher_spec()` builds the OCP primitive.
7. User runs analysis, code generation, or visualization as separate actions.

PDF/image upload remains experimental and should feed the same review process.

## Web Actions

The web UI exposes:

- `POST /api/text/draft`
- `POST /api/text/confirm`
- `POST /api/analyze`
- `POST /api/code`
- `POST /api/visualize`
- `POST /api/upload`

The page includes direct action buttons for differential analysis, linear
analysis, code generation, and visualization after a cipher is available.

Use `GET /api/solvers` or `OCPAgent().solver_capabilities()` to inspect
available solver backends before launching solver-backed analysis.
