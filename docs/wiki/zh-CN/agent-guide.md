# Agent 使用指南

语言：[English](../en/agent-guide.md) | **中文**

## 概览

OCP Agent 将 OCP 工作流封装为结构化 skill。核心调度器是 `AgentCore`，面向用户的 API 是
`OCPAgent`。

主要 skill：

| Skill | 用途 |
|---|---|
| `cipher_instantiation` | 加载内置密码。 |
| `cipher_definition` | 从 `CipherSpec` 构建自定义密码。 |
| `cipher_text_input` | 规整纯文本、Markdown 和 LaTeX 密码描述。 |
| `differential_analysis` | 运行差分分析。 |
| `linear_analysis` | 运行线性分析。 |
| `code_generation` | 生成 Python/C/SystemVerilog 实现。 |
| `visualization` | 生成结构可视化。 |

## 直接 API

如果不需要自然语言解析，建议使用直接 API。

```python
from agent import OCPAgent

agent = OCPAgent()
agent.instantiate_cipher("speck", "blockcipher", version=[32, 64])
agent.generate_code(language="python", unroll=True)
agent.differential_analysis(model_type="milp")
```

## 命令行

```bash
python3 run_agent.py --provider openai
python3 run_agent.py --provider deepseek
python3 run_agent.py --provider openai-compatible --base-url http://localhost:8000/v1
python3 run_agent.py --provider anthropic
python3 run_agent.py --provider gemini
python3 run_agent.py --provider ollama --model llama3
```

DeepSeek 使用 OpenAI-compatible 协议。设置 `DEEPSEEK_API_KEY` 即可；默认模型为
`deepseek-chat`，也可以用 `--model deepseek-reasoner` 指定推理模型。

## 网页界面

```bash
python3 web/app.py --port 5001
```

## 文本优先密码输入

推荐的抽取路径是用户提供文本：纯文本、Markdown、LaTeX、伪代码或结构化笔记。PDF/图片抽取
保留为实验能力，因为视觉识别可能漏读数学细节。

当前文本优先 schema 提供：

- `CipherInput`：保存原始文本以及来源、格式和语言提示。
- `CipherFacts`：保存中间抽取事实、假设、歧义和来源证据。
- `CipherSpecDraft`：保存可审阅的候选 `CipherSpec`，包括阻塞性校验错误、
  警告、澄清问题，并默认要求用户确认。

```python
from agent.skills.cipher_text_input import (
    CipherFacts,
    CipherInput,
    build_cipher_spec_draft,
)

cipher_input = CipherInput(
    raw_text=r"x_0 \leftarrow (x_0 \ggg 7) \boxplus x_1",
    source_type="direct_text",
    format_hint="latex",
)
assert cipher_input.validate() == []

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
