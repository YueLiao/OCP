# OCP (Open Cryptanalysis Platform) / 开放密码分析平台

OCP is a Python research platform for modeling symmetric cryptographic
primitives, generating implementations, visualizing structures, and searching
for differential or linear trails with MILP/SAT backends.

OCP 是一个 Python 研究平台，用于建模对称密码算法、生成实现代码、可视化结构，并通过
MILP/SAT 后端搜索差分或线性特征。

This fork also includes **OCP Agent**, a conversational and programmatic layer
that can instantiate built-in ciphers, define custom ciphers from structured
specifications, extract cipher descriptions from papers, and run analysis
workflows.

此分支还包含 **OCP Agent**：一个会话式和程序式接口层，可以实例化内置密码、根据结构化
描述定义自定义密码、从论文中抽取算法描述，并执行分析流程。

Official upstream: https://github.com/Open-CP/OCP

官方上游仓库：https://github.com/Open-CP/OCP

## Repository Layout / 仓库结构

| Path | English | 中文 |
|---|---|---|
| `variables/` | Variable nodes used in cipher graphs. | 密码图中的变量节点。 |
| `operators/` | Boolean, modular, S-box, matrix, AES-round, and helper operators. | 布尔、模加、S 盒、矩阵、AES 轮等算子。 |
| `primitives/` | Built-in cipher and permutation models. | 内置密码和置换模型。 |
| `attacks/` | Differential and linear attack orchestration and trail formats. | 差分/线性分析调度和 trail 结果格式。 |
| `solving/` | MILP/SAT solver wrappers. | MILP/SAT 求解器封装。 |
| `implementations/` | Python/C/SystemVerilog code generation and implementation tests. | Python/C/SystemVerilog 代码生成与测试。 |
| `visualisations/` | Structure and trail visualization helpers. | 结构与 trail 可视化工具。 |
| `tools/` | Constraint generation, model objectives, resource monitoring, and utilities. | 约束生成、目标函数、资源监控和工具函数。 |
| `agent/` | Conversational/API wrapper around OCP workflows. | OCP 工作流的会话式/API 封装。 |
| `web/` | Flask web chat interface for OCP Agent. | OCP Agent 的 Flask 网页聊天界面。 |
| `test/` | Operator, implementation, and cryptanalysis tests. | 算子、实现和密码分析测试。 |
| `docs/wiki/` | Wiki-style bilingual documentation. | Wiki 风格中英文文档。 |

## Install / 安装

Create a virtual environment first.

建议先创建虚拟环境。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For the Agent and web UI:

如需使用 Agent 和网页界面：

```bash
pip install -e ".[agent]"
```

Solver and modeling backends are optional. Install only the ones you need:

求解器和建模后端是可选依赖，请按需安装：

```bash
pip install -r requirements-solvers.txt
```

Classic requirements files remain available for users who prefer explicit
requirements-based installs:

如果你更偏好传统 requirements 安装，也可以继续使用：

```bash
pip install -r requirements.txt
pip install -r requirements-agent.txt
```

Notes:

注意：

- `gurobipy` requires a valid Gurobi installation/license for MILP solving.
- `python-sat` is needed for SAT solving.
- `PyMuPDF` or `pdfplumber` is needed for PDF extraction.
- `pyeda`, `pycddlib`, and Espresso-related tooling are used by some constraint generation modes.

- `gurobipy` 需要有效的 Gurobi 安装和许可证。
- `python-sat` 用于 SAT 求解。
- PDF 抽取需要 `PyMuPDF` 或 `pdfplumber`。
- 部分约束生成模式会使用 `pyeda`、`pycddlib` 和 Espresso 相关工具。

## Quick Start: Python API / 快速开始：Python API

```python
from agent import OCPAgent

agent = OCPAgent()
agent.instantiate_cipher("speck", "blockcipher", version=[32, 64])

# Generate implementation code.
agent.generate_code(language="python", unroll=True, test=True)

# Run cryptanalysis. Requires the selected solver backend.
agent.differential_analysis(model_type="milp")
agent.linear_analysis(model_type="sat")
```

The direct API does not require an LLM provider.

直接 API 不需要配置大模型。

## Quick Start: CLI Agent / 快速开始：命令行 Agent

```bash
export OPENAI_API_KEY="sk-..."
python3 run_agent.py --provider openai

# Other providers:
export DEEPSEEK_API_KEY="sk-..."
python3 run_agent.py --provider deepseek

export OPENAI_COMPATIBLE_API_KEY="key"
python3 run_agent.py --provider openai-compatible --base-url http://localhost:8000/v1

python3 run_agent.py --provider anthropic
python3 run_agent.py --provider gemini
python3 run_agent.py --provider ollama --model llama3
```

Example prompt:

示例输入：

```text
Describe the following ARX cipher from this Markdown/LaTeX text:
x_0 \leftarrow (x_0 \ggg 7) \boxplus x_1
x_1 \leftarrow (x_1 \lll 2) \oplus x_0
Then run differential cryptanalysis using MILP.
```

## Quick Start: Web UI / 快速开始：网页界面

```bash
pip install -r requirements-agent.txt
python3 web/app.py --port 5001
```

Open `http://localhost:5001`.

打开 `http://localhost:5001`。

## Built-in Ciphers / 内置密码

The Agent catalog currently includes:

Agent 目录当前包含：

`speck`, `simon`, `aes`, `gift`, `present`, `skinny`, `ascon`, `chacha`,
`salsa`, `forro`, `led`, `siphash`, `shacal2`, `rocca`, `speedy`, `trivium`.

Supported primitive types vary by cipher: `permutation`, `blockcipher`, and
`keypermutation`.

不同密码支持的类型不同：`permutation`、`blockcipher`、`keypermutation`。

## Custom Cipher Definition / 自定义密码定义

Use `CipherSpec` to define ciphers programmatically:

可以用 `CipherSpec` 程序式定义密码：

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

## Generated Files / 生成文件

Runtime outputs are written under `files/` by default. This includes generated
implementations, MILP/SAT model files, trail JSON/TXT files, and visualization
PDFs.

运行时输出默认写入 `files/`，包括生成的实现代码、MILP/SAT 模型文件、trail JSON/TXT
和可视化 PDF。

Some modeling templates under `files/*_modeling/` are currently tracked because
they exist in upstream history. Do not remove them in drive-by cleanup; use a
dedicated cleanup/change-management pass if the project decides to regenerate
them on demand.

`files/*_modeling/` 中部分建模模板当前已被上游历史跟踪。不要在普通清理中顺手删除；
如果项目决定改为按需生成，应单独做一次清理和迁移。

## Validation / 验证

Run the tests that match your installed optional dependencies:

根据已安装的可选依赖运行对应测试：

```bash
python -m compileall agent primitives attacks solving tools
python -m pytest

# Optional heavier suites:
python -m pytest --run-implementations
python -m pytest --run-solver
python -m pytest --run-legacy-operators
```

For development, install the editable package with test dependencies:

开发时建议安装 editable 包和测试依赖：

```bash
pip install -e ".[agent,test]"
```

MILP tests require a MILP backend such as Gurobi or SCIP. SAT tests require
`python-sat`.

MILP 测试需要 Gurobi 或 SCIP 等 MILP 后端。SAT 测试需要 `python-sat`。

By default, pytest runs only lightweight standardized tests. Script-style
operator experiments, generated implementation tests, and solver-dependent
cryptanalysis tests are skipped unless their explicit flags are passed.

默认情况下，pytest 只运行轻量、标准化测试。脚本式算子实验、生成实现测试和依赖求解器
的密码分析测试会被跳过，除非显式传入对应开关。

## Runtime Output Directory / 运行输出目录

The default output directory is `files/`. To redirect runtime artifacts:

默认输出目录是 `files/`。如需重定向运行产物：

```bash
export OCP_FILES_DIR=/tmp/ocp-files
```

This affects newly standardized output paths such as analysis models, trail
files, S-box/matrix modeling artifacts, and Agent code-generation defaults.

该变量会影响已标准化的输出路径，例如分析模型、trail 文件、S 盒/矩阵建模产物，以及
Agent 代码生成默认目录。

## Documentation / 文档

Start with the wiki-style bilingual docs:

建议从 Wiki 风格双语文档开始：

- [docs/wiki/README.md](docs/wiki/README.md)
- [docs/wiki/agent-guide.md](docs/wiki/agent-guide.md)
- [docs/wiki/development-and-standardization.md](docs/wiki/development-and-standardization.md)
- [docs/wiki/agentic-system-roadmap.md](docs/wiki/agentic-system-roadmap.md)
- [docs/wiki/testing-and-ci.md](docs/wiki/testing-and-ci.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

## Architecture / 架构

The high-level structure is:

整体结构如下：

1. User/API/Agent selects or defines a cipher.
2. Primitive classes build layered variable/operator graphs.
3. Attack modules select model versions and generate MILP/SAT constraints.
4. Solver wrappers run the configured backend.
5. Trail objects format results and optional visualization/codegen modules produce artifacts.

1. 用户/API/Agent 选择或定义密码。
2. Primitive 类构建按轮/层组织的变量-算子图。
3. Attack 模块选择模型版本并生成 MILP/SAT 约束。
4. Solver 封装运行配置的后端。
5. Trail 对象格式化结果，可视化/代码生成模块输出工件。

<p align="center">
  <img src="docs/images/architecture.png" alt="architecture" width="600">
</p>
