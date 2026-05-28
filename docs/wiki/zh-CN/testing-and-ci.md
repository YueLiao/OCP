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

`test/operators/` 下的旧式算子文件是人工实验脚本，会在 pytest 下有意跳过：

```bash
python test/operators/test_xor.py
```

## CI

GitHub Actions 会运行：

```bash
python -m pip install -e ".[test]"
python -m compileall agent primitives attacks solving tools operators
python -m pytest
```

CI 有意不安装可选求解器依赖。求解器测试应在后端安装方式稳定后，作为独立 workflow 添加。

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

## 本地输出隔离

```bash
OCP_FILES_DIR=/tmp/ocp-files python -m pytest --run-implementations
```

这样可以避免生成的模型、trail 和实现文件混入仓库已跟踪内容。
