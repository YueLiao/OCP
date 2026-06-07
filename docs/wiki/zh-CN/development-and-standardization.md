# 开发与标准化指南

语言：[English](../en/development-and-standardization.md) | **中文**

## 项目形态

OCP 是研究代码、库和工具混合型仓库。当前公开使用方式主要包括直接模块导入、脚本、Agent API
和网页界面。

## 行为不变量

重构时需要保持：

- 现有 primitive 工厂名，例如 `SPECK_BLOCKCIPHER`。
- 现有包/模块导入路径。
- 算子的 model-version 语义。
- MILP/SAT 目标名称和约束格式。
- 默认输出到 `files/` 的行为，除非设置 `OCP_FILES_DIR`。
- 生成实现的测试向量行为。

## 推荐清理阶段

### 第一阶段：低风险清理

- 持续维护依赖元数据和生成物忽略规则。
- 改善 API 边界处的可选依赖错误。
- 减少可选 solver/modeling 后端在 import 阶段的副作用。
- README/wiki 按语言拆分，并在页面顶部提供语言切换链接。
- 每个 coherent change 后运行编译和冒烟检查。

### 第二阶段：接口与测试

- 集中管理输出目录和求解器默认值。
- 为 Agent 直接 API 行为添加聚焦测试。
- 使用 fake provider 分离 LLM 解析测试和 skill 执行测试。
- 明确网页界面的 session 管理。
- 可选 solver/generated 测试继续通过显式 pytest 开关运行。

### 第三阶段：更深架构调整

- 只有通过专门迁移，才把生成建模模板移出已跟踪运行输出。
- 继续集中管理求解器能力检测。
- 深层性能重写前先 profile 约束生成。
- 拆分大型 operator/model 文件时必须有聚焦回归测试保护。

## 性能优化机会

潜在加速点：

1. 针对相同 S-box 类和 model version 缓存 DDT/LAT 派生约束。
2. 对等价 operator 复用生成的 S-box 和 matrix 模板约束。
3. 相同 attack scope 避免重复完整展开 `functions/rounds/layers/positions`。
4. 保持可选后端 lazy import。
5. 文档抽取优先使用文本输入，避免整篇文档直接进入 LLM prompt。

## 上游同步流程

当 Open-CP/OCP 上游更新时，使用以下流程：

```bash
git status --short
git fetch origin
git fetch myfork
git rev-list --left-right --count origin/main...HEAD
git log --oneline --left-right --cherry-pick origin/main...HEAD
git diff --name-status $(git merge-base origin/main HEAD)..origin/main
```

推荐合并策略：

- 保留本地 optimization、Agent、Web、测试和文档改进。
- 当 fork 已经领先很多提交时，用显式 merge commit 把上游合入 `main`；
  不要随意改写本地历史。
- 如果 `operators/`、`primitives/`、`tools/` 或 `attacks/` 出现冲突，先识别
  上游语义变化，再把它迁移到本地已经重构过的结构中，避免直接整文件覆盖。
- 合并后运行 operator 聚焦测试、默认 pytest、CLI help，以及
  [性能基线](performance-baseline.md) 中的 profiling smoke 命令。
- 只有当 fork 相对上游为 `0 behind` 且工作区干净时再 push。

## 验证命令

```bash
python -m pip install -e ".[agent,test]"
python -m compileall agent primitives attacks solving tools operators
python -m pytest

# 可选测试：
python -m pytest --run-implementations
python -m pytest --run-solver

# 人工运行旧式 operator 实验：
python test/operators/test_xor.py
```
