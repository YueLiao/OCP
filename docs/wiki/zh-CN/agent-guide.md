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

进入 CLI 后，可以使用 `draft <cipher text>` 运行文本优先抽取流程。CLI 会打印候选
`CipherSpec` 草稿，并在构建前要求确认。

## 网页界面

```bash
python3 web/app.py --port 5001
```

网页端包含 chat、provider 配置，以及面向文本优先密码描述的 `Draft` 动作。`Draft`
会抽取 facts、返回可审阅的 `CipherSpec` 草稿，并在构建 cipher 前要求确认。
每次文本优先 draft 流程都会在 `OCP_FILES_DIR/agent_jobs/` 下写出可复现 JSON job
记录，并作为 artifact link 返回。

## 文本优先密码输入

推荐的抽取路径是用户提供文本：纯文本、Markdown、LaTeX、伪代码或结构化笔记。PDF/图片抽取
只是实验性导入 helper，因为视觉识别可能漏读数学细节，不应自动构建 cipher。

当前文本优先 schema 提供：

- `CipherInput`：保存原始文本以及来源、格式和语言提示。
- `CipherFacts`：保存中间抽取事实、假设、歧义和来源证据。
- `CipherSpecDraft`：保存可审阅的候选 `CipherSpec`，包括阻塞性校验错误、
  警告、澄清问题，并默认要求用户确认。
- `build_cipher_facts_extraction_prompt()` 和 `parse_cipher_facts_response()`：
  为 LLM 抽取提供确定性的 prompt/parse 边界。

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

高层 `OCPAgent` API 暴露同一套流程：

```python
agent = OCPAgent(llm_provider=my_provider)

facts_result = agent.extract_cipher_facts(
    r"x_0 \leftarrow (x_0 \ggg 7) \boxplus x_1",
    format_hint="latex",
)
draft = agent.draft_cipher_spec()

# 先审阅 draft.validation_errors、draft.warnings 和 draft.assumptions。
build_result = agent.confirm_cipher_spec(draft)
```

流程成功时，`facts_result.data["artifact_links"]` 和
`build_result.data["artifact_links"]` 会包含 JSON job 记录路径。
