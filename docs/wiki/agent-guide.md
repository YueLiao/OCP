# Agent Guide / Agent 使用指南

## Overview / 概览

OCP Agent turns OCP workflows into structured skills. The central orchestrator is
`AgentCore`; the user-facing API is `OCPAgent`.

OCP Agent 将 OCP 工作流封装为结构化 skill。核心调度器是 `AgentCore`，面向用户的 API
是 `OCPAgent`。

Main skills:

主要 skill：

| Skill | English | 中文 |
|---|---|---|
| `cipher_instantiation` | Load a built-in cipher. | 加载内置密码。 |
| `cipher_definition` | Build a custom cipher from `CipherSpec`. | 从 `CipherSpec` 构建自定义密码。 |
| `cipher_extraction` | Extract a cipher spec from PDF/image/text. | 从 PDF/图片/文本抽取密码规格。 |
| `differential_analysis` | Run differential cryptanalysis. | 运行差分分析。 |
| `linear_analysis` | Run linear cryptanalysis. | 运行线性分析。 |
| `code_generation` | Generate Python/C/SystemVerilog implementations. | 生成 Python/C/SystemVerilog 实现。 |
| `visualization` | Generate structure visualizations. | 生成结构可视化。 |

## Direct API / 直接 API

Use the direct API when you do not need natural language parsing.

如果不需要自然语言解析，建议使用直接 API。

```python
from agent import OCPAgent

agent = OCPAgent()
result = agent.instantiate_cipher("speck", "blockcipher", version=[32, 64])
print(result.summary)

agent.generate_code(language="python", unroll=True)
agent.differential_analysis(model_type="milp")
```

## Chat API / 聊天 API

Use an LLM provider when you want natural language requests.

如果希望用自然语言请求，配置一个 LLM provider。

```python
from agent import OCPAgent
from agent.llm.openai_provider import OpenAIProvider

provider = OpenAIProvider(api_key="sk-...", model="gpt-4o")
agent = OCPAgent(llm_provider=provider)

print(agent.chat("Analyze SPECK32/64 with differential cryptanalysis using MILP"))
```

## CLI / 命令行

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

DeepSeek 使用 OpenAI-compatible 协议。设置 `DEEPSEEK_API_KEY` 即可；默认模型为
`deepseek-chat`，也可以用 `--model deepseek-reasoner` 指定推理模型。

## Web UI / 网页界面

```bash
python3 web/app.py --port 5001
```

The web UI keeps a single global session and is intended for local, single-user
experiments.

网页界面当前使用单个全局 session，适合本地单用户实验。

## Defining Custom Ciphers / 定义自定义密码

`CipherSpec` is the stable schema between natural language extraction and OCP's
low-level primitive graph.

`CipherSpec` 是自然语言抽取和 OCP 底层 primitive 图之间的稳定 schema。

Supported layer types:

支持的层类型：

- `rotation`
- `xor`
- `modadd`
- `sbox`
- `permutation`
- `matrix`
- `add_round_key`
- `add_constant`

Example:

示例：

```python
from agent import CipherSpec, LayerSpec

spec = CipherSpec(
    name="ToySPN",
    cipher_type="permutation",
    block_size=16,
    word_bitsize=1,
    nbr_words=16,
    nbr_rounds=4,
    sbox_tables={"s": [0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD,
                       0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2]},
    round_structure=[
        LayerSpec("sbox", {"sbox_name": "s", "index": [[0,1,2,3], [4,5,6,7],
                                                       [8,9,10,11], [12,13,14,15]]}),
        LayerSpec("permutation", {"table": [0,4,8,12,1,5,9,13,2,6,10,14,3,7,11,15]}),
    ],
)
```

## Error Handling / 错误处理

If a direct API call reports a missing module, install the corresponding
requirements file first. For example, missing `numpy` means:

如果直接 API 报缺少模块，请先安装对应 requirements。例如缺少 `numpy` 表示：

```bash
pip install -r requirements.txt
```

Solver errors usually mean the selected backend is not installed, not licensed,
or not available on the current system.

求解器错误通常表示所选后端未安装、无许可证，或当前系统不可用。
