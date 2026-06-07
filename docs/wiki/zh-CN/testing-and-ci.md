# 测试与 CI

语言：[English](../en/testing-and-ci.md) | **中文**

## 快速默认测试

```bash
python -m pytest
```

默认测试会运行标准化轻量测试，并跳过：

- 旧式脚本风格算子实验。
- 生成实现测试。
- 依赖求解器的密码分析测试。

## 可选测试套件

```bash
python -m pytest --run-implementations
python -m pytest --run-solver
```

修改对应子系统并安装匹配的可选后端后，再运行这些测试。

当 PySAT 可用时，solver 套件会包含一条 identity-elision SAT smoke test。
该测试会构建 Forro 的 elided 模型、求解它，并验证 trail extraction 能通过 alias pass
找回被移除变量的取值：

```bash
python -m pytest test/unit/test_performance_regressions.py::test_identity_elision_sat_solver_smoke_preserves_trail_lookup --run-solver
```

`test/operators/` 下的旧式算子文件是人工实验脚本，会在 pytest 下有意跳过：

```bash
python test/operators/test_xor.py
```

## CI

GitHub Actions 会运行：

```bash
python -m pip install -e ".[test]"
python -m compileall agent primitives attacks solving tools operators web run_agent.py
ocp-agent --help
python -m pytest
```

`test` extra 包含默认测试需要导入的轻量 Agent/Web 依赖。CI 有意不安装可选求解器依赖。
求解器测试应在后端安装方式稳定后，作为独立 workflow 添加。

## 源码分发包

源码分发包应包含：

- 根目录 README 和 license 文件。
- `requirements*.txt` 依赖集合。
- `docs/` 下适合迁移到 wiki 的 Markdown 文档。
- `files/*_modeling/` 下已跟踪的 S-box 和 matrix 建模模板。

`MANIFEST.in` 会显式记录这些文件，确保 release archive 包含 source-tree
工作流需要的运行时模板。

## 求解器能力检查

可选求解器后端可以在不 import 原生求解器模块的情况下检查：

```python
from solving.solving import is_solver_available, solver_capabilities

solver_capabilities()
is_solver_available("milp", "DEFAULT")
is_solver_available("sat", "Glucose3")
```

`DEFAULT` MILP 会映射到 Gurobi。`DEFAULT` SAT 和具名 PySAT 引擎会映射到
PySAT 后端。OR-Tools SAT 路径目前是预留接口，尚未实现，因此即使 Python
包已安装，也不会被报告为可执行可用。

Attack 配置会在共享 frontend 边界统一规整：

- `config_model["model_type"]` 接受 `milp` 或 `sat`，并统一成小写。
- 显式传入的 `config_model["filename"]` 会被保留；未传入时，OCP 会写到运行时
  `OCP_FILES_DIR` 位置。
- `config_solver["solver"]` 默认是 `DEFAULT`。
- 如果传入 `config_solver["solution_number"]`，它必须是正整数。

Solver wrapper 暴露 `normalize_milp_solver_name()` 和 `normalize_sat_solver_name()`
用于显式校验；`is_solver_available()` 仍是安静的能力检查，未知 solver 名会返回 `False`。
直接调用 solver 时也会校验 `config_solver` 必须是字典，保留调用者传入的空配置字典，
并把规整后的 solver 名称写回该字典。

共享 attack frontend 对外仍返回 legacy `config_model` 和 `config_solver` 字典，
但内部会先通过类型化的 `AttackSearchConfig` wrapper 统一规整。Differential 和
linear search 也复用同一条 helper 路径来展开 `INPUT_NOT_ZERO` 这类符号约束，
以及 goal 要求的固定输入/输出 difference 或 mask 约束。

## 本地输出隔离

```bash
OCP_FILES_DIR=/tmp/ocp-files python -m pytest --run-implementations
```

这样可以避免生成的模型、trail 和实现文件混入仓库已跟踪内容。

## 模型生成 Profiling

做聚焦性能优化时，可以通过 `config_model` 打开可选模型生成 profiling：

```python
config_model = {"profile_model_generation": True}
```

模型构建结束后，`config_model["model_generation_profile"]` 会包含每类 operator 的调用次数、
生成约束数量和耗时。
已解析的约束模板会按文件名和修改时间缓存，因此模板重新生成后会自动失效。

如果只想做一次可复现的本地快照、且不启动求解器：

```bash
python -m tools.profile_model_generation present:1 forro:1
python -m tools.profile_model_generation chacha:1 salsa:1 forro:1 --identity-elision
```

Profile case 使用 `name` 或 `name:rounds` 格式；rounds 和 `--top-limit`
都必须是正整数。

该命令会输出 JSON，包含 primitive 构建耗时、模型生成耗时、约束数量和按 operator
聚合的热点统计。它适合在运行更重的求解器流程之前，用来比较小规模性能优化改动。
