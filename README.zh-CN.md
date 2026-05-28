# OCP（开放密码分析平台）

语言：[English](README.md) | **中文**

OCP 是一个 Python 研究平台，用于建模对称密码算法、生成实现代码、可视化结构，并通过
MILP/SAT 后端搜索差分或线性特征。

此分支还包含 **OCP Agent**：一个会话式和程序式工作流层，可以实例化内置密码、根据结构化
规格定义自定义密码、解析文本优先的密码算法描述，并执行分析流程。

官方上游仓库：https://github.com/Open-CP/OCP

## 仓库结构

| 路径 | 用途 |
|---|---|
| `variables/` | 密码图中的变量节点。 |
| `operators/` | 布尔、模加、S 盒、矩阵、AES 轮等算子。 |
| `primitives/` | 内置密码和置换模型。 |
| `attacks/` | 差分/线性分析调度和 trail 结果格式。 |
| `solving/` | MILP/SAT 求解器封装。 |
| `implementations/` | Python/C/SystemVerilog 代码生成与测试。 |
| `visualisations/` | 结构和 trail 可视化工具。 |
| `tools/` | 约束生成、目标函数、资源监控和工具函数。 |
| `agent/` | OCP 工作流的会话式/API 封装。 |
| `web/` | OCP Agent 的 Flask 网页聊天界面。 |
| `test/` | 单元、算子、实现和密码分析测试。 |
| `docs/wiki/` | 带语言切换入口的 Wiki 风格文档。 |

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

如需使用 Agent 和网页界面：

```bash
pip install -e ".[agent]"
```

可选求解器和建模后端：

```bash
pip install -r requirements-solvers.txt
```

也可以继续使用传统 requirements 文件：

```bash
pip install -r requirements.txt
pip install -r requirements-agent.txt
```

注意：

- `gurobipy` 需要有效的 Gurobi 安装和许可证。
- `python-sat` 用于 SAT 求解。
- PDF 抽取需要 `PyMuPDF` 或 `pdfplumber`。
- 部分约束生成模式会使用 `pyeda`、`pycddlib` 和 Espresso 相关工具。

## 快速开始：Python API

```python
from agent import OCPAgent

agent = OCPAgent()
agent.instantiate_cipher("speck", "blockcipher", version=[32, 64])

agent.generate_code(language="python", unroll=True, test=True)
agent.differential_analysis(model_type="milp")
agent.linear_analysis(model_type="sat")
```

直接 API 不需要配置大模型。

## 快速开始：命令行 Agent

```bash
export OPENAI_API_KEY="sk-..."
python3 run_agent.py --provider openai

export DEEPSEEK_API_KEY="sk-..."
python3 run_agent.py --provider deepseek

export OPENAI_COMPATIBLE_API_KEY="key"
python3 run_agent.py --provider openai-compatible --base-url http://localhost:8000/v1

python3 run_agent.py --provider anthropic
python3 run_agent.py --provider gemini
python3 run_agent.py --provider ollama --model llama3
```

文本优先输入示例：

```text
Describe the following ARX cipher from this Markdown/LaTeX text:
x_0 \leftarrow (x_0 \ggg 7) \boxplus x_1
x_1 \leftarrow (x_1 \lll 2) \oplus x_0
Then run differential cryptanalysis using MILP.
```

准确抽取密码规格时，纯文本、Markdown 和 LaTeX 输入是首选路径。PDF/图片抽取仍保留为实验能力，
因为视觉识别可能漏读公式、表格、状态布局和 bit 编号规则。

## 快速开始：网页界面

```bash
pip install -r requirements-agent.txt
python3 web/app.py --port 5001
```

打开 `http://localhost:5001`。

使用 `Draft` 处理文本优先的密码描述。确认构建后，网页端提供差分分析、线性分析、代码生成和
可视化动作，生成文件通过 `artifact_links` 返回。

## 内置密码

Agent 目录当前包含：

`speck`, `simon`, `aes`, `gift`, `present`, `skinny`, `ascon`, `chacha`,
`salsa`, `forro`, `led`, `siphash`, `shacal2`, `rocca`, `speedy`, `trivium`.

不同密码支持的类型不同：`permutation`、`blockcipher` 和 `keypermutation`。

## 自定义密码定义

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

## 生成文件

运行时输出默认写入 `files/`，包括生成的实现代码、MILP/SAT 模型文件、trail JSON/TXT
文件和可视化 PDF。

`files/*_modeling/` 中部分建模模板来自上游历史并已被跟踪。不要在普通清理中顺手删除；
如果后续决定改成按需生成，应单独做一次迁移。

重定向运行产物：

```bash
export OCP_FILES_DIR=/tmp/ocp-files
```

## 验证

```bash
python -m compileall agent primitives attacks solving tools operators
python -m pytest

# 可选重型测试：
python -m pytest --run-implementations
python -m pytest --run-solver

# 人工运行旧式 operator 实验脚本：
python test/operators/test_xor.py
```

默认 pytest 只运行轻量、标准化测试。脚本式算子实验在 pytest 下始终跳过，因为它们是人工
实验脚本。生成实现测试和依赖求解器的密码分析测试需要显式开启。

## 文档

- [Wiki 首页](docs/wiki/README.md)
- [English wiki](docs/wiki/en/README.md)
- [中文 Wiki](docs/wiki/zh-CN/README.md)
- [Agentic 架构](docs/wiki/zh-CN/agentic-architecture.md)
- [Agent 使用指南](agent/README.zh-CN.md)
