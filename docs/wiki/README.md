# OCP Wiki / OCP Wiki 首页

This directory contains wiki-style documentation for OCP and OCP Agent.

本目录提供 OCP 和 OCP Agent 的 Wiki 风格文档。

## Pages / 页面

- [Agent Guide / Agent 使用指南](agent-guide.md)
- [Development and Standardization / 开发与标准化指南](development-and-standardization.md)
- [Standardization Report / 代码规范化报告](standardization-report.md)
- [Agentic System Roadmap / Agentic 系统路线图](agentic-system-roadmap.md)
- [Testing and CI / 测试与 CI](testing-and-ci.md)

## What OCP Is / OCP 是什么

OCP models ciphers as graphs of variables and operators. Built-in primitives
construct these graphs round by round. Attack modules translate operators into
MILP/SAT constraints, solver modules search for solutions, and trail classes
format the resulting differential or linear characteristics.

OCP 将密码算法建模为变量和算子组成的图。内置 primitive 按轮构建这些图。Attack
模块把算子翻译成 MILP/SAT 约束，solver 模块搜索解，trail 类负责格式化差分或线性
特征结果。

OCP Agent adds a workflow layer around the core platform. It can parse user
requests through an LLM provider, execute structured skills, keep session state,
and expose the same capabilities through a direct Python API.

OCP Agent 是核心平台之上的工作流层。它可以通过 LLM provider 解析用户请求，执行结构化
skill，维护会话状态，并通过直接 Python API 暴露同样能力。

## Typical Workflows / 常见工作流

1. Instantiate a built-in cipher and run differential analysis.
2. Generate Python/C/SystemVerilog implementations and run test vectors.
3. Define a custom cipher with `CipherSpec`.
4. Extract a cipher from a paper and formalize it into `CipherSpec`.
5. Visualize a primitive or a trail.

1. 实例化内置密码并运行差分分析。
2. 生成 Python/C/SystemVerilog 实现并运行测试向量。
3. 使用 `CipherSpec` 定义自定义密码。
4. 从论文中抽取密码描述并形式化为 `CipherSpec`。
5. 可视化 primitive 或 trail。

## Installation Summary / 安装摘要

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-agent.txt      # optional Agent/web dependencies
pip install -r requirements-solvers.txt    # optional solver/modeling backends
```

Solver packages are optional because different users may prefer Gurobi, SCIP,
PySAT, or only code generation without solving.

求解器依赖是可选的，因为不同用户可能只使用 Gurobi、SCIP、PySAT，或只做代码生成而不求解。
