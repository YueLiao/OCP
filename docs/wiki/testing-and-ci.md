# Testing and CI / 测试与 CI

## Fast Default / 快速默认测试

The default test command is designed to be fast and stable:

默认测试命令目标是快速、稳定：

```bash
python -m pytest
```

It runs standardized lightweight tests and skips:

它会运行标准化轻量测试，并跳过：

- Legacy script-style operator experiments.
- Generated implementation tests.
- Solver-dependent cryptanalysis tests.

- 旧式脚本风格算子实验。
- 生成实现测试。
- 依赖求解器的密码分析测试。

## Optional Suites / 可选测试套件

```bash
python -m pytest --run-implementations
python -m pytest --run-solver
```

Use these suites when touching the corresponding subsystem.

修改对应子系统时再运行这些测试。

Legacy operator files under `test/operators/` are manual experiment scripts and
are intentionally skipped under pytest. Run one directly when needed:

`test/operators/` 下的旧式算子文件是人工实验脚本，会在 pytest 下有意跳过。需要时直接运行
单个脚本：

```bash
python test/operators/test_xor.py
```

## CI / 持续集成

GitHub Actions runs:

GitHub Actions 会运行：

```bash
python -m pip install -e ".[test]"
python -m compileall agent primitives attacks solving tools operators
python -m pytest
```

The CI intentionally avoids optional solver dependencies. Solver-backed tests
should be added as a separate workflow after the backend setup is stable.

CI 有意不安装可选求解器依赖。求解器测试应在后端安装方式稳定后，作为独立 workflow 添加。

## Local Output Isolation / 本地输出隔离

Use `OCP_FILES_DIR` during experiments:

实验时建议使用 `OCP_FILES_DIR`：

```bash
OCP_FILES_DIR=/tmp/ocp-files python -m pytest --run-implementations
```

This prevents generated models, trails, and implementation files from mixing
with tracked repository content.

这样可以避免生成的模型、trail 和实现文件混入仓库已跟踪内容。
