# Contributing to OCP / OCP 贡献指南

Thank you for helping improve OCP. The goal of this repository is to become a
clean, usable, stable, and robust open-source cryptanalysis platform.

感谢你帮助改进 OCP。本仓库的目标是成为一套干净、易用、稳定、鲁棒的开源密码分析平台。

## Development Setup / 开发环境

Recommended conda setup:

推荐 conda 环境：

```bash
conda create -n ocp python=3.11
conda activate ocp
python -m pip install -e ".[agent,test]"
```

Classic requirements files are also available:

也可以使用传统 requirements 文件：

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-agent.txt
```

Install solver backends only when needed:

仅在需要时安装求解器后端：

```bash
python -m pip install -r requirements-solvers.txt
```

## Default Validation / 默认验证

Run the fast default checks before sending changes:

提交改动前，请先运行快速默认检查：

```bash
python -m compileall agent primitives attacks solving tools operators
python -m pytest
```

The default test run is intentionally fast. It skips legacy operator
experiments, generated implementation tests, and solver-dependent tests.

默认测试有意保持快速。它会跳过旧式算子实验、生成实现测试和依赖求解器的测试。

Optional suites:

可选测试套件：

```bash
python -m pytest --run-legacy-operators
python -m pytest --run-implementations
python -m pytest --run-solver
```

## Runtime Outputs / 运行产物

Runtime artifacts default to `files/`. To isolate generated files:

运行产物默认写入 `files/`。如需隔离生成文件：

```bash
export OCP_FILES_DIR=/tmp/ocp-files
```

Do not commit generated outputs unless they are intentionally curated modeling
templates or documentation assets.

不要提交运行生成物，除非它们是明确维护的建模模板或文档资产。

## Change Guidelines / 改动原则

- Preserve existing public import paths and primitive factory names.
- Preserve cryptanalysis semantics unless a behavior change is explicitly approved.
- Keep refactors small and reviewable.
- Add tests for new public APIs and bug fixes.
- Avoid new dependencies unless the benefit is clear.
- Keep PDF/image extraction experimental; prefer text-first Agent workflows.

- 保持现有公开 import 路径和 primitive 工厂函数名称。
- 除非明确批准行为变更，否则保持密码分析语义不变。
- 重构应小而可审阅。
- 新公开 API 和 bug fix 应补测试。
- 避免无必要新增依赖。
- PDF/图片抽取保持 experimental，Agent 工作流优先文本输入。

## Pull Request Checklist / PR 检查清单

- [ ] The change is behavior-preserving, or behavior changes are documented.
- [ ] Default validation passes.
- [ ] Optional heavy tests were run if the change touches solvers/codegen/operators.
- [ ] README/Wiki updates are included for user-facing changes.
- [ ] Generated artifacts are not accidentally committed.

- [ ] 改动保持行为兼容，或已记录行为变化。
- [ ] 默认验证通过。
- [ ] 如果改动涉及 solver/codegen/operator，已运行相关重型测试。
- [ ] 面向用户的变化已更新 README/Wiki。
- [ ] 没有误提交生成产物。
