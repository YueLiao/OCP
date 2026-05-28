# 代码规范化报告

语言：[English](../en/standardization-report.md) | **中文**

本页记录仓库标准化工作。核心原则是保持密码分析行为不变，同时让项目更容易运行、测试、阅读文档和继续扩展。

## 诊断清单

| 领域 | 状态 | 说明 |
|---|---:|---|
| 仓库结构 | 需继续改进 | 核心引擎、测试、agent、文档和生成文件边界更清楚了；更深模块边界仍需整理。 |
| 架构边界 | 需继续改进 | Agent provider、输出路径、attack 公共 helper、operator helper、primitive layer/link helper、verbose-aware 诊断和 solver 能力报告已收紧。 |
| 公共接口 | 需继续改进 | `OCPAgent` 和 provider 启动入口更清楚；operator/model API 后续仍需要类型化契约。 |
| 可读性 | 需继续改进 | operator 和 primitive 框架已完成多轮低风险清理；attack 模块和 solver/modeling 边界仍较复杂。 |
| 风格工具 | 通过 | `pyproject.toml` 已定义 package metadata 和 pytest 设置。 |
| 错误处理 | 需继续改进 | 可选依赖失败和工具诊断更安静；部分路径仍有较宽泛异常处理。 |
| 配置 | 通过 | 输出位置通过 `tools.paths.get_files_dir()` 集中管理，并支持 `OCP_FILES_DIR`。 |
| 测试 | 通过 | 核心冒烟测试确定；solver/generated 测试通过显式 pytest 开关保护。 |
| 文档 | 通过 | README/wiki 已改为语言切换链接，不再中英混排。 |
| 打包 | 通过 | 已配置 editable install 和 `ocp-agent` 命令行入口。 |
| 性能 | 需继续改进 | 可选后端 import 更 lazy；S-box、矩阵和 primitive layer 查找 helper 已做聚焦优化。 |

## 已完成改动

- 添加 package metadata、可选依赖组和 `ocp-agent` 命令行入口。
- 添加 Python 3.10/3.11 的 CI smoke test。
- 为 Agent API、路径、provider、搜索 I/O、operator 核心行为和文本输入规整添加确定性单测。
- 用 `OCP_FILES_DIR` 统一运行时输出路径。
- 减少 solver/modeling 可选后端在 import 阶段的噪声。
- 添加 DeepSeek 与通用 OpenAI-compatible provider 支持。
- 添加文本优先密码输入 dataclass、Markdown/LaTeX 规整、确定性 facts 校验、prompt/parse 边界和 draft-to-spec 转换 helper。
- 添加文本优先 facts 抽取、draft 创建和显式确认构建的 `OCPAgent` 直接 API。
- 添加 CLI `draft <cipher text>` 文本优先草稿审阅和确认流程。
- 添加网页 text draft/confirm endpoint 和 `Draft` UI 动作，用于先审阅再构建。
- 为 text-first 抽取、draft 和 confirmation 添加可复现 JSON job 记录与 artifact links。
- 将文本优先 Agentic 路线图扩展为可评审实现契约，覆盖 schema、网页流程、provider、安全确认和测试。
- 优化 S-box 和 GF(2) 矩阵 helper，并修复 PMR 分块拼接。
- 收拢 Boolean、modular、S-box 和 matrix operator 中重复的模型生成 helper。
- 清理 S-box 带权 truth-table、matrix bit-model、显式 modular arithmetic 和未完成 operator 抽象。
- 收拢 primitive layer 的 Equal 约束、图遍历、输入/输出链接 helper，并优化 layer 输出查找。
- 将 attack/solver 进度消息接入 verbose-aware logging，并把工具诊断改为 Python warnings。
- 添加显式 solver 能力报告，用于检查可选 MILP/SAT 后端，并文档化当前 solver fallback。
- 将 attack/model generation 路径里的重复约束和 objective 列表拼接改为显式原地扩展。
- 明确旧式 operator 文件是人工实验脚本。
- 将文档拆为英文和中文页面，并在顶部提供语言切换链接。

## 验证

```bash
conda run -n ocp python -m compileall agent primitives attacks solving tools operators web run_agent.py
conda run -n ocp python -m pytest
conda run -n ocp ocp-agent --help
git diff --check
```

最新默认 pytest 状态：`88 passed, 106 skipped`。

## 后续工作

1. 深层性能重写前先 profile 模型生成过程。
2. 继续收窄 solver/model generation 路径里的宽泛异常处理。
3. 将 PDF/image 抽取明确降级为 experimental import helper。
