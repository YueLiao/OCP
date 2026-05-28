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

## Web UI

```bash
python3 web/app.py --port 5001
```

## Text-First Cipher Input

The preferred extraction path is user-provided text: plain text, Markdown,
LaTeX, pseudocode, or structured notes. PDF/image extraction remains
experimental because visual recognition can miss mathematical details.
