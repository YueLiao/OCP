# OCP Wiki

语言：[English](../en/README.md) | **中文**

OCP 将密码算法建模为变量和算子组成的图。内置 primitive 按轮构建这些图。Attack 模块把算子
翻译成 MILP/SAT 约束，solver 模块搜索解，trail 类负责格式化差分或线性特征结果。

OCP Agent 是核心平台之上的工作流层。它可以通过 LLM provider 解析用户请求，执行结构化
skill，维护会话状态，并通过直接 Python API 暴露同样能力。

## 页面

- [Agent 使用指南](agent-guide.md)
- [开发与标准化指南](development-and-standardization.md)
- [代码规范化报告](standardization-report.md)
- [Agentic 系统路线图](agentic-system-roadmap.md)
- [测试与 CI](testing-and-ci.md)

## 常见工作流

1. 实例化内置密码并运行差分分析。
2. 生成 Python/C/SystemVerilog 实现并运行测试向量。
3. 使用 `CipherSpec` 定义自定义密码。
4. 将文本优先的密码描述解析为候选规格。
5. 可视化 primitive 或 trail。

## 安装摘要

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[agent,test]"
pip install -r requirements-solvers.txt    # 可选求解器/建模后端
```

求解器依赖是可选的，因为不同用户可能使用 Gurobi、SCIP、PySAT，或只做代码生成而不求解。
