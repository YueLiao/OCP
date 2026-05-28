# Development and Standardization / 开发与标准化指南

## Current Project Shape / 当前项目形态

OCP is a mixed research/library/tooling repository. It is not yet a fully
packaged Python distribution. Public usage is currently through direct module
imports, scripts, and the Agent API.

OCP 是研究代码、库和工具混合型仓库。目前还不是完整打包的 Python 发行包。公开使用方式
主要是直接模块导入、脚本和 Agent API。

## Behavioral Invariants / 行为不变量

When refactoring, preserve:

重构时需要保持：

- Existing primitive factory names such as `SPECK_BLOCKCIPHER`.
- Existing package/module import paths.
- Operator model-version semantics.
- MILP/SAT objective names and constraint formats.
- Default output directory behavior under `files/`.
- Test vector behavior for generated implementations.

- 现有 primitive 工厂名，例如 `SPECK_BLOCKCIPHER`。
- 现有包/模块导入路径。
- 算子的 model-version 语义。
- MILP/SAT 目标名称和约束格式。
- 默认输出到 `files/` 的行为。
- 生成实现的测试向量行为。

## Recommended Cleanup Phases / 推荐清理阶段

### Phase 1: Safe Hygiene / 第一阶段：低风险清理

- Add dependency files and generated-output ignore rules.
- Improve missing-dependency errors at API boundaries.
- Reduce import-time warnings from optional dependencies.
- Add bilingual README/wiki documentation.
- Run compile/smoke checks.

- 添加依赖文件和生成物忽略规则。
- 改善 API 边界处的缺依赖错误。
- 减少可选依赖在 import 时产生的 warning。
- 添加中英文 README/Wiki 文档。
- 运行编译和冒烟检查。

### Phase 2: Interface and Tests / 第二阶段：接口与测试

- Add a small configuration module for output directories and solver defaults.
- Add focused tests for Agent direct API behavior.
- Split LLM parsing from skill execution tests using fake providers.
- Make web UI session management explicit.
- Add optional-dependency markers or skip logic in tests.

- 添加小型配置模块管理输出目录和求解器默认值。
- 为 Agent 直接 API 行为添加聚焦测试。
- 使用 fake provider 分离 LLM 解析和 skill 执行测试。
- 明确网页界面的 session 管理。
- 为可选依赖添加测试标记或 skip 逻辑。

### Phase 3: Deeper Architecture / 第三阶段：更深架构调整

- Introduce package metadata only after deciding the supported install model.
- Move generated modeling templates out of tracked runtime output if upstream agrees.
- Centralize solver capability detection.
- Profile constraint generation and cache repeated S-box/matrix model generation.

- 在确定支持的安装模型之后再引入完整包元数据。
- 如果上游认可，将生成的建模模板移出被跟踪的运行输出目录。
- 集中管理求解器能力检测。
- profile 约束生成，并缓存重复的 S 盒/矩阵模型生成。

## Performance Opportunities / 性能优化机会

Potential acceleration points:

潜在加速点：

1. Cache S-box DDT/LAT-derived constraints across identical S-box classes and model versions.
2. Cache matrix constraint templates under a stable key: matrix, field polynomial, goal, model type.
3. Avoid rebuilding full `functions/rounds/layers/positions` maps when the same cipher and goal are analyzed repeatedly.
4. Avoid import-time optional backend probing; detect only when a backend is requested.
5. For large documents, keep the current multi-step extraction pipeline and page filtering instead of sending full papers to the LLM.

1. 对相同 S 盒类和 model version 缓存 DDT/LAT 派生约束。
2. 以矩阵、域多项式、目标、模型类型作为稳定 key 缓存矩阵约束模板。
3. 同一 cipher 和 goal 重复分析时，避免重复构建完整的 `functions/rounds/layers/positions` 映射。
4. 避免 import 时探测所有可选后端，只在请求某后端时检测。
5. 对长文档保持当前多步抽取和页过滤，而不是整篇论文直接送入 LLM。

## Validation Commands / 验证命令

```bash
python -m pip install -e ".[agent,test]"
python -m compileall agent primitives attacks solving tools
python -m pytest

# Optional suites:
python -m pytest --run-legacy-operators
python -m pytest --run-implementations
python -m pytest --run-solver
```

Run solver-dependent tests only after installing the matching backend.

只有安装对应后端后，才运行依赖求解器的测试。

Default pytest behavior intentionally keeps the standard check fast. Legacy
operator experiments, generated implementation checks, and solver-heavy
cryptanalysis tests are opt-in.

默认 pytest 行为有意保持快速。旧式算子实验、生成实现检查，以及依赖求解器的重型密码分析
测试都需要显式开启。

## Runtime Paths / 运行路径

Use `tools.paths.get_files_dir()` for new code that writes runtime artifacts.
It preserves the historical default of `<repo>/files` and supports
`OCP_FILES_DIR` for local experiments or CI isolation.

新代码如果需要写运行产物，应使用 `tools.paths.get_files_dir()`。它保持历史默认行为
`<repo>/files`，同时支持通过 `OCP_FILES_DIR` 在本地实验或 CI 中隔离输出。
