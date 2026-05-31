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
| 配置 | 通过 | 输出位置通过运行时 `tools.paths.get_files_dir()` 调用集中管理，并支持 `OCP_FILES_DIR`。 |
| 测试 | 通过 | 核心冒烟测试确定；solver/generated 测试通过显式 pytest 开关保护。 |
| 文档 | 通过 | README/wiki 已改为语言切换链接，不再中英混排。 |
| 打包 | 通过 | 已配置 editable install 和 `ocp-agent` 命令行入口。 |
| 性能 | 需继续改进 | 可选后端 import 更 lazy；S-box、矩阵和 primitive layer 查找 helper 已做聚焦优化。 |

## 已完成改动

- 添加 package metadata、可选依赖组和 `ocp-agent` 命令行入口。
- 添加 Python 3.10/3.11 的 CI smoke test。
- 为 Agent API、路径、provider、搜索 I/O、operator 核心行为和文本输入规整添加确定性单测。
- 用 `OCP_FILES_DIR` 统一运行时输出路径。
- 移除 attack 输出路径的 import-time 快照，让模型和 trail 文件名能响应运行时 `OCP_FILES_DIR` 变化。
- 移除 logic minimization 和 agent 代码生成默认输出目录里的 import-time 路径快照。
- 让默认 `OCPAgent` 代码生成和可视化输出通过运行时 `OCP_FILES_DIR` 解析。
- 为 agent 代码生成测试结果添加结构化通过/失败统计，同时保留旧的结果条目。
- 为 agent 代码生成和可视化输出添加 artifact links。
- 将 agent 代码生成输出目录失败包装到 `SkillResult` 中。
- 将 agent 可视化输出目录失败包装到 `SkillResult` 中。
- 让 artifact registry ID 在不同 Python 进程之间保持确定性。
- 添加基于当前 session registry 的网页 artifact 下载 endpoint 和侧边栏下载链接。
- 按稳定 artifact ID 对 session artifact 记录去重。
- 减少 solver/modeling 可选后端在 import 阶段的噪声。
- 为 analysis skill 添加不支持 model type 的边界校验。
- 为 analysis skill 添加非正 solution count 的边界校验。
- 在 agent 内置 cipher 实例化边界添加版本校验。
- 将 Agent 中 SHACAL2 实例化限制为已实现的 256-bit 版本，并澄清 Trivium catalog 状态。
- 添加 primitive 支持状态页面，记录 SHACAL2 部分覆盖和 Trivium 原型状态。
- 将 trail solution-bit 的异常处理收窄到数值转换失败。
- 添加 DeepSeek 与通用 OpenAI-compatible provider 支持。
- 为 DeepSeek OpenAI-compatible 覆盖参数和通用 base URL 缺失场景添加 provider smoke 覆盖。
- 添加文本优先密码输入 dataclass、Markdown/LaTeX 规整、确定性 facts 校验、prompt/parse 边界和 draft-to-spec 转换 helper。
- 为规整后的 text-first cipher 输入行添加行/列 source span，并持久化到 job records。
- 在 `AgentCore` 抽取流程中复用共享 LLM JSON response parser。
- 添加文本优先 facts 抽取、draft 创建和显式确认构建的 `OCPAgent` 直接 API。
- 添加 CLI `draft <cipher text>` 文本优先草稿审阅和确认流程。
- 添加网页 text draft/confirm endpoint 和 `Draft` UI 动作，用于先审阅再构建。
- 添加网页/API 路径，允许用户提交手动编辑后的 `CipherSpec` draft，并在确认前做确定性校验。
- 添加持久网页 CipherSpec draft 编辑器和构建前校验控件。
- 将网页 provider API key 解析与 CLI 的环境变量默认行为对齐。
- 为网页 JSON endpoints 缺失 JSON body 的情况添加显式 400 响应。
- 对网页 provider 配置错误返回 HTTP 400。
- 网页 API 响应不再暴露 provider 初始化、chat 和 upload 处理时的底层异常细节。
- 为已确认的网页 analysis 响应添加 solver 能力元数据。
- 从网页上传 endpoint 返回文件抽取 data 和 artifact links。
- 避免上传临时文件已缺失时的清理错误掩盖网页上传响应。
- 为 text-first 抽取、draft 和 confirmation 添加可复现 JSON job 记录与 artifact links。
- 为 text-first job records 添加 prompt/input/response/draft/confirmation hash 和确认时间戳。
- 为 text-first job records 添加手动修订时间戳和 hash。
- 将文本优先 Agentic 路线图扩展为可评审实现契约，覆盖 schema、网页流程、provider、安全确认和测试。
- 为文本优先 Agentic 的 source span、手动编辑、golden examples、provider 边界、solver 元数据和 job records 添加剩余实施清单。
- 添加 ARX、SPN 和 S-box/permutation 的 text-first golden fixtures，用于 draft 校验。
- 将更多 XOR 和 bitwise OR 作为 S-box 的行为迁移到稳定 operator 单测。
- 将 N-XOR 的实现生成、linear 和 truncated-linear 行为迁移到稳定 operator 单测。
- 将 ConstantXOR 和 NOT 的实现生成、header、truncated 行为迁移到稳定 operator 单测。
- 将 rotation 和 shift 的实现生成与模型行为迁移到稳定 operator 单测。
- 将 CopyOperator 和 NoneOperator 行为迁移到稳定 operator 单测。
- 将 ConstantAdd header 与 ModAdd differential/linear 模型行为迁移到稳定 operator 单测。
- 将轻量 S-box 代码生成、branch number 和 weight helper 行为迁移到稳定 operator 单测。
- 将 Matrix 代码生成、GF(2^m) 算术和 zero-star pattern 行为迁移到稳定 operator 单测。
- 将 ANDXOR 和 GF2Linear_Trans 行为迁移到稳定 operator 单测。
- 为 AES round 的结构、header 和实现生成添加稳定 composite operator 单测。
- 为 SHACAL2 Sigma、Sum、Maj 和 Ch 的代码生成添加稳定 composite operator 单测。
- 收拢 SHACAL2 composite operator 中重复的 header、implementation 和 model 生成 helper。
- 修复 SHACAL2 composite model generation，避免向子 operator 传入不支持的参数。
- 收拢 AES round layer 遍历逻辑，并显式化 Matrix branch-number 路由条件。
- 扩展 Forro subround 回归覆盖，检查操作位置、rotation 参数和 key-stream temp-word 连线。
- 优化 S-box 和 GF(2) 矩阵 helper，并修复 PMR 分块拼接。
- 收拢 Boolean、modular、S-box 和 matrix operator 中重复的模型生成 helper。
- 清理 S-box 带权 truth-table、matrix bit-model、显式 modular arithmetic 和未完成 operator 抽象。
- 将 matrix truncated-model fallback 诊断接入 Python warnings，并使用运行时输出路径。
- 收拢 primitive layer 的 Equal 约束、图遍历、输入/输出链接 helper，并优化 layer 输出查找。
- 集中 Forro 的状态尺寸、默认 subround 数、keystream 元数据和 factory 变量创建逻辑。
- 将 attack/solver 进度消息接入 verbose-aware logging，并把工具诊断改为 Python warnings。
- 添加显式 solver 能力报告，用于检查可选 MILP/SAT 后端，并文档化当前 solver fallback。
- 添加显式源码分发 manifest，覆盖文档、依赖文件和已跟踪的建模模板。
- 确保 PySAT 求解过程中即使抛出异常也会释放 solver 实例。
- 将运行时资源监控的异常处理收窄到 psutil/OS 失败。
- 收窄 SCIP solver 失败处理，让意外程序错误继续暴露。
- 收窄 PySAT cardinality fallback 处理，让意外程序错误继续暴露。
- 将 attack 入口基于 `assert` 的参数校验替换为共享的显式 `ValueError` 校验。
- 将 attack/model generation 路径里的重复约束和 objective 列表拼接改为显式原地扩展。
- 添加可选模型生成 profiling，用于记录每类 operator 的约束数量和耗时。
- 为模型生成 profiler 输入添加更清晰的校验和 CLI usage 错误。
- 集中管理模型生成 profiling 的 config key。
- 将模型生成 profiling 和 identity-elision 状态 helper 从 `tools.model_constraints` 拆出，同时保留兼容 import。
- 将 PySAT cardinality 后端 helper 从 `tools.model_constraints` 拆出，同时保留兼容 wrapper。
- 将约束模板生成、缓存和实例化 helper 从 `tools.model_constraints` 拆出，同时保留公开 import。
- 将 Boolean XOR/NXOR 与 matrix 约束 helper 从 `tools.model_constraints` 拆出，同时保留公开 import。
- 将 sequential SAT encoding 和 Matsui 搜索约束 helper 从 `tools.model_constraints` 拆出，同时保留公开 import。
- 将 predefined SAT/MILP 约束构造 helper 从 `tools.model_constraints` 拆出，同时保留公开 import。
- 将 model scope、version assignment 和 round model generation helper 从 `tools.model_constraints` 拆出，同时保留公开 import。
- 将 operator 内部 import 改为直接依赖新的 bit-constraint 和 model-template 模块，而不是兼容 facade。
- 将 attack/search/profiler 内部 import 改为直接依赖新的 model-configuration、predefined-constraint、search-constraint 和 state 模块。
- 将 objective-target 解析和 SAT/MILP objective 约束构造拆到 `tools.objective_targets`。
- 将 MILP search 的模型约束构造、objective 选择和解 objective 后处理拆成更聚焦的 helper。
- 将 optimal SAT search-strategy 解析拆到 `tools.objective_targets`。
- 将 SAT decimal-objective combination 查找集中到 `tools.objective_targets`。
- 将重复的 SAT objective-constraint 求解调用收拢到私有 helper。
- 集中 SAT optimal-search strategy 到 `SUM_*` 约束类型的映射。
- 让 decimal SAT objective 过滤跳过缺少 `obj_fun_value` 的异常解记录。
- 将 SAT CNF 和 MILP LP 模型序列化 helper 拆到 `tools.model_io`。
- 将 symbolic CNF 变量抽取改为逐 literal 收集，避免先拼接完整模型字符串。
- 按文件修改时间缓存已解析约束模板，减少重复 S-box 模板加载。
- 将模板实例化里的逐变量多次正则替换改为单次 token 替换，减少约束模板展开开销。
- 为模型生成添加 opt-in identity elision，用于保守跳过内部 Equal 链。
- 验证 identity-elision 下的 trail extraction、MILP/SAT 生成和 primitive graph 边界。
- 复用 model config 并关闭 identity elision 时，会清理其私有状态。
- 集中管理 identity-elision 在模型生成和 trail extraction 中使用的私有 config key。
- 将 PDF/image 抽取重新标注为 experimental import helper，并关闭网页上传自动构建。
- 为 experimental file extraction 添加显式页码范围校验。
- 明确旧式 operator 文件是人工实验脚本。
- 将 Equal implementation 和 MILP equivalence 覆盖从旧式 operator 脚本迁入聚焦的 pytest 用例。
- 将文档拆为英文和中文页面，并在顶部提供语言切换链接。
- 为 SHACAL2 1024-bit Sigma/Sum 常量添加回归覆盖。
- 集中 SHACAL2 Sigma/Sum 常量，并为不支持的 keysize 添加显式校验。
- 集中 Forro 参考测试向量，并覆盖 factory 挂载行为。
- 将 SHACAL2 layered header 的重复检查从列表扫描改为 set 查询。
- 修正 bitwise S-box 实现生成逻辑，使非方形输出按 output width 解包。

## 验证

```bash
conda run -n ocp python -m compileall agent primitives attacks solving tools operators web run_agent.py
conda run -n ocp python -m pytest
conda run -n ocp ocp-agent --help
git diff --check
```

最新默认 pytest 状态：`170 passed, 106 skipped`。

## 后续工作

1. 基于 profiling 结果决定更深层模型生成优化优先级。
2. 继续收窄 solver/model generation 路径里的宽泛异常处理。
3. 继续优化网页 draft review 体验和 artifact 浏览。
