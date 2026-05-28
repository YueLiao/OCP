# OCP Agent - 自动化密码分析助手

语言：[English](README.md) | **中文**

OCP Agent 是 OCP 之上的会话式和程序式工作流层，用于通过自然语言或 Python API 完成密码实例化、自定义密码定义、代码生成、可视化、差分分析和线性分析。

## 快速开始

### 1. 安装依赖

```bash
pip install -e ".[agent]"

# 可选求解器
pip install -r requirements-solvers.txt
```

### 2. 启动 CLI

```bash
cd /path/to/OCP

export OPENAI_API_KEY="sk-xxx"
python3 run_agent.py --provider openai

export DEEPSEEK_API_KEY="sk-xxx"
python3 run_agent.py --provider deepseek

export OPENAI_COMPATIBLE_API_KEY="your-key"
python3 run_agent.py --provider openai-compatible --base-url http://localhost:8000/v1

python3 run_agent.py --provider anthropic
python3 run_agent.py --provider gemini
python3 run_agent.py --provider ollama --model llama3
```

DeepSeek 使用 OpenAI-compatible 协议。默认模型是 `deepseek-chat`，也可以使用
`--model deepseek-reasoner`。

## 对话示例

```text
You> Analyze SPECK32/64 with differential cryptanalysis using MILP

Assistant> Created SPECK32_64. Running differential analysis...
```

文本优先的自定义密码输入：

```text
You> Parse this Markdown/LaTeX cipher description:
     x_0 \leftarrow (x_0 \ggg 7) \boxplus x_1
     x_1 \leftarrow (x_1 \lll 2) \oplus x_0

Assistant> Normalized the text and extracted candidate cipher facts...
```

准确抽取密码规格时，推荐用户提供纯文本、Markdown、LaTeX 或伪代码。PDF/图片抽取只是实验性导入
helper，不再作为主路径；构建前必须审阅草稿。

## Python API

直接 API 不需要配置 LLM：

```python
from agent import OCPAgent

agent = OCPAgent()
agent.instantiate_cipher("speck", "blockcipher", version=[32, 64])
agent.generate_code(language="python", unroll=True, test=True)
agent.differential_analysis(goal="DIFFERENTIALPATH_PROB", model_type="milp")
agent.linear_analysis(goal="LINEARPATH_CORR", model_type="sat")
```

自定义密码：

```python
from agent import OCPAgent, CipherSpec, LayerSpec

spec = CipherSpec(
    name="TinyARX",
    cipher_type="permutation",
    block_size=32,
    word_bitsize=16,
    nbr_words=2,
    nbr_rounds=10,
    round_structure=[
        LayerSpec("rotation", {"direction": "r", "amount": 7, "word_index": 0}),
        LayerSpec("modadd", {"input_indices": [[0, 1]], "output_indices": [0]}),
        LayerSpec("rotation", {"direction": "l", "amount": 2, "word_index": 1}),
        LayerSpec("xor", {"input_indices": [[0, 1]], "output_indices": [1]}),
    ],
)

agent = OCPAgent()
agent.define_custom_cipher(spec)
agent.differential_analysis(model_type="milp")
```

## Web UI

```bash
python3 web/app.py --port 5001
```

打开 `http://localhost:5001`。

## 相关文档

- [仓库中文 README](../README.zh-CN.md)
- [中文 Wiki](../docs/wiki/zh-CN/README.md)
- [Agentic 系统路线图](../docs/wiki/zh-CN/agentic-system-roadmap.md)
