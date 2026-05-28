# Agent Guide

Language: **English** | [中文](../zh-CN/agent-guide.md)

## Overview

OCP Agent turns OCP workflows into structured skills. The central orchestrator is
`AgentCore`; the user-facing API is `OCPAgent`.

Main skills:

| Skill | Purpose |
|---|---|
| `cipher_instantiation` | Load a built-in cipher. |
| `cipher_definition` | Build a custom cipher from `CipherSpec`. |
| `cipher_text_input` | Normalize plain text, Markdown, and LaTeX cipher descriptions. |
| `differential_analysis` | Run differential cryptanalysis. |
| `linear_analysis` | Run linear cryptanalysis. |
| `code_generation` | Generate Python/C/SystemVerilog implementations. |
| `visualization` | Generate structure visualizations. |

## Direct API

Use the direct API when you do not need natural language parsing.

```python
from agent import OCPAgent

agent = OCPAgent()
agent.instantiate_cipher("speck", "blockcipher", version=[32, 64])
agent.generate_code(language="python", unroll=True)
agent.differential_analysis(model_type="milp")
```

## CLI

```bash
python3 run_agent.py --provider openai
python3 run_agent.py --provider deepseek
python3 run_agent.py --provider openai-compatible --base-url http://localhost:8000/v1
python3 run_agent.py --provider anthropic
python3 run_agent.py --provider gemini
python3 run_agent.py --provider ollama --model llama3
```

DeepSeek uses the OpenAI-compatible protocol. Set `DEEPSEEK_API_KEY`; the
default model is `deepseek-chat`, and `deepseek-reasoner` can be selected with
`--model`.

Inside the CLI, use `draft <cipher text>` to run the text-first extraction
flow. The CLI prints the proposed `CipherSpec` draft and asks before building.

## Web UI

```bash
python3 web/app.py --port 5001
```

## Text-First Cipher Input

The preferred extraction path is user-provided text: plain text, Markdown,
LaTeX, pseudocode, or structured notes. PDF/image extraction remains
experimental because visual recognition can miss mathematical details.

The text-first schema currently provides:

- `CipherInput` for raw text plus source, format, and language hints.
- `CipherFacts` for intermediate extracted facts, assumptions, ambiguities, and
  source evidence.
- `CipherSpecDraft` for a reviewable proposed `CipherSpec` with blocking
  validation errors, warnings, clarification questions, and mandatory user
  confirmation.
- `build_cipher_facts_extraction_prompt()` and `parse_cipher_facts_response()`
  for a deterministic prompt/parse boundary around LLM extraction.

```python
from agent.skills.cipher_text_input import (
    CipherFacts,
    CipherInput,
    build_cipher_spec_draft,
    parse_cipher_facts_response,
)
from agent.llm.prompt_templates import build_cipher_facts_extraction_prompt

cipher_input = CipherInput(
    raw_text=r"x_0 \leftarrow (x_0 \ggg 7) \boxplus x_1",
    source_type="direct_text",
    format_hint="latex",
)
assert cipher_input.validate() == []
prompt = build_cipher_facts_extraction_prompt(cipher_input)

facts = CipherFacts(
    name="TinyARX",
    primitive_type="permutation",
    state={"block_size": 32, "word_bitsize": 16, "nbr_words": 2},
    rounds={"nbr_rounds": 4},
    operations=[
        {"type": "rotation", "params": {"direction": "r", "amount": 7, "word_index": 0}},
        {"type": "modadd", "params": {"input_indices": [[0, 1]], "output_indices": [0]}},
    ],
)

draft = build_cipher_spec_draft(facts)
assert draft.is_valid
assert draft.requires_user_confirmation
```

The high-level `OCPAgent` API exposes the same flow:

```python
agent = OCPAgent(llm_provider=my_provider)

facts_result = agent.extract_cipher_facts(
    r"x_0 \leftarrow (x_0 \ggg 7) \boxplus x_1",
    format_hint="latex",
)
draft = agent.draft_cipher_spec()

# Review draft.validation_errors, draft.warnings, and draft.assumptions first.
build_result = agent.confirm_cipher_spec(draft)
```
