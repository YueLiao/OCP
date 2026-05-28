# Standardization Report / 代码规范化报告

This page records the first repository standardization pass. The guiding rule
was to preserve cryptanalysis behavior while making the project easier to run,
test, document, and extend.

本页记录第一轮代码仓标准化工作。核心原则是保持密码分析行为不变，同时让项目更容易运行、
测试、阅读文档和继续扩展。

## Diagnosis Checklist / 诊断清单

| Area | Status | Notes |
|---|---:|---|
| Repository structure | Needs work | Core engine, tests, agent, docs, and generated files are now separated more clearly, but deeper module boundaries still need work. |
| Architecture boundaries | Needs work | Agent provider creation, output paths, and shared attack helpers were tightened; solver/modeling layers still mix logging, I/O, and domain logic in places. |
| Public interfaces | Needs work | `OCPAgent` and provider launchers are clearer; operator/model APIs still need typed contracts over time. |
| Readability | Needs work | Low-risk path/config cleanup completed; larger files such as `Sbox.py`, `matrix.py`, and attack modules remain complex. |
| Style tooling | Pass | `pyproject.toml` now defines package metadata and pytest settings. |
| Error handling | Needs work | Optional dependency failures are less noisy; solver/trail progress output now has a quiet mode, but broad exception handling remains in some paths. |
| Configuration | Pass | Output location is centralized through `tools.paths.get_files_dir()` and supports `OCP_FILES_DIR`. |
| Tests | Pass | Core smoke tests are deterministic; solver/legacy/generated tests are guarded by explicit pytest flags. |
| Documentation | Pass | Root README and wiki pages now document install, usage, testing, development, and the agentic roadmap. |
| Packaging | Pass | Editable install and `ocp-agent` console entry point are configured. |
| Performance | Needs work | Import-time optional dependency work was reduced; S-box truth-table generation, GF(2) matrix helpers, PMR generation, and cardinality helpers now have focused low-risk optimizations. Deeper speedups still need profiling of model generation and solver loops. |

## Behavioral Invariants / 行为不变量

- Existing primitive/operator modeling semantics should remain unchanged.
- Built-in cipher instantiation should keep the same names and constructor behavior.
- Existing generated output format should remain compatible.
- Solver-dependent tests are not removed; they are opt-in because they require external solvers.
- The direct Python API remains usable without any LLM provider.

- 现有 primitive/operator 建模语义保持不变。
- 内置密码实例化名称和构造方式保持兼容。
- 已有生成文件格式保持兼容。
- 依赖外部 solver 的测试未删除，只改为显式开关运行。
- 直接 Python API 仍然不需要配置大模型。

## Completed Changes / 已完成改动

- Added packaging metadata, optional dependency groups, and the `ocp-agent` console script.
- Added CI smoke tests for Python 3.10 and 3.11.
- Added deterministic unit tests for Agent direct API, response parsing, paths, operator core behavior, provider defaults, and text input normalization.
- Centralized output directory handling with `OCP_FILES_DIR`.
- Suppressed noisy import-time optional dependency warnings and made failures surface closer to actual use.
- Added DeepSeek and generic OpenAI-compatible provider support.
- Added text-first cipher input dataclasses and Markdown/LaTeX normalization.
- Optimized pure S-box DDT/LAT/truth-table helpers while preserving generated tables.
- Optimized GF(2) matrix multiplication/power and cached PMR generation.
- Simplified repeated cardinality-constraint plumbing and fixed trivial SAT at-most bounds.
- Added shared `attacks.common` helpers for attack config, fixed boundary constraints, nonzero input constraints, and trail structure extraction.
- Fixed linear SAT fixed-mask indexing and linear decimal-weight detection to use LAT data.
- Added `tools.search_reporting` so solver/trail progress remains verbose by default but can be silenced with `verbose=False`.
- Fixed the mutable default argument in `write_sat_model`.
- Hardened objective-function term parsing for integer and decimal SAT objective variables.
- Deduplicated the implementation-test helpers in the top-level `OCP.py` example script.
- Expanded bilingual README/wiki documentation.

- 添加 package metadata、可选依赖组和 `ocp-agent` 命令行入口。
- 添加 Python 3.10/3.11 的 CI smoke test。
- 添加 Agent 直接 API、响应解析、路径、operator 核心行为、provider 默认值和文本规整的确定性单测。
- 用 `OCP_FILES_DIR` 统一输出目录。
- 减少 import 阶段可选依赖噪声，让缺失依赖在实际使用时再明确暴露。
- 添加 DeepSeek 与通用 OpenAI-compatible provider 支持。
- 添加文本优先的密码输入 dataclass 与 Markdown/LaTeX 规整。
- 优化纯 S-box DDT/LAT/truth-table 辅助函数，并保持生成表不变。
- 优化 GF(2) 矩阵乘法/幂运算，并缓存 PMR 生成。
- 简化重复的 cardinality constraint 逻辑，并修复 SAT at-most 平凡上界。
- 添加 `attacks.common`，复用 attack 配置、固定边界约束、输入非零约束和 trail 结构抽取逻辑。
- 修复 linear SAT 固定 mask 的 bit 索引，并让 linear 小数权重检测使用 LAT 数据。
- 添加 `tools.search_reporting`，默认保留 solver/trail 进度输出，同时支持 `verbose=False` 静默运行。
- 修复 `write_sat_model` 的可变默认参数。
- 加固 objective-function term 解析，覆盖 SAT 整数和小数目标变量。
- 去重顶层 `OCP.py` 示例脚本里的实现测试辅助函数。
- 扩展中英文 README/wiki 文档。

## Validation / 验证

```bash
conda run -n ocp python -m compileall agent primitives attacks solving tools operators web run_agent.py
conda run -n ocp python -m pytest
conda run -n ocp ocp-agent --help
```

Latest result:

最新结果：

- `compileall`: passed
- `pytest`: 45 passed, 106 skipped
- `ocp-agent --help`: passed

Skipped tests are intentional by default:

默认跳过的测试是有意设置：

- `--run-legacy-operators`
- `--run-solver`
- `--run-implementations`

## Next Work / 后续工作

1. Add the real text-first extraction skill around `CipherInput`, `CipherFacts`, and `CipherSpecDraft`.
2. Add provider capability flags for JSON output, tool calls, vision, and reasoning content.
3. Continue refactoring large operator/model files only with focused regression tests.
4. Profile model generation and solver setup to identify the next measurable speedups.
5. Upgrade the web UI from chat plus upload into a proper text extraction workspace with fact review and editable `CipherSpec`.

1. 围绕 `CipherInput`、`CipherFacts`、`CipherSpecDraft` 实现真正的文本优先抽取 skill。
2. 增加 provider 能力标记，包括 JSON output、tool calls、vision、reasoning content。
3. 继续在有聚焦回归测试保护的前提下拆分大型 operator/model 文件。
4. 对模型生成和 solver 初始化做 profiling，寻找下一批可量化加速点。
5. 将 Web UI 从聊天加上传升级为文本抽取工作台，支持事实复核和可编辑 `CipherSpec`。
