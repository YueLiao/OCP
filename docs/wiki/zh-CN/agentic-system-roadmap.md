# OCP Agentic 系统路线图

语言：[English](../en/agentic-system-roadmap.md) | **中文**

状态：待评审方案。本页是后续修改 Agent 功能前需要确认的实现契约。

## 方向

下一阶段 Agentic 系统应采用**文本优先**路线。用户应提供纯文本、Markdown、
LaTeX 片段、伪代码、表格或结构化笔记来描述密码算法。PDF 和图片输入可以保留为便捷辅助，
但不能作为主可信来源，因为视觉模型容易误读公式、表格、状态布局和 bit 编号规则。

主要输入格式：

- 从论文或笔记复制出的纯文本。
- 带列表、代码块和表格的 Markdown。
- LaTeX 公式、算法环境和表格。
- 伪代码和赋值式轮函数描述。
- 中英文混合技术描述。
- 用户自己整理的结构化笔记。

## 产品目标

将人类可读的密码算法描述转换为经过校验的 OCP `CipherSpec` 对象，并且只在用户明确确认后
进行构建、分析、可视化和代码生成。

系统应像谨慎的密码分析助手，而不是自动“论文转代码”的黑盒。每个推断参数、假设和歧义都应
可以被用户审阅。

## 非目标

- 不承诺从图片或扫描 PDF 中准确抽取密码算法。
- 不在缺少确认的情况下运行代码生成、求解器任务或会写文件的流程。
- 不静默编造缺失的 S-box、置换表、常数、密钥编排或 bit ordering 规则。
- 不让网页端绑定到某一个 LLM 厂商 API。

## 核心工作流

1. 用户提供文本、Markdown、LaTeX 或伪代码。
2. Agent 规整文本，并保留来源片段。
3. Agent 抽取候选 `CipherFacts`，包含置信度和引用。
4. Agent 校验完整性、一致性和 OCP 可支持性。
5. 信息缺失时，Agent 提出有针对性的澄清问题。
6. Agent 构建 `CipherSpecDraft`。
7. Agent 运行确定性的 schema 校验和构建冒烟检查。
8. Agent 展示人类可读的审阅稿。
9. 用户确认或编辑草稿。
10. Agent 构建 OCP primitive，并提供分析、代码生成和可视化动作。

## 架构

| 层级 | 职责 | 初始实现目标 |
|---|---|---|
| 输入层 | 接收直接文本、Markdown、LaTeX、上传的 `.txt`/`.md` 文件和粘贴笔记。 | 扩展 `CipherInput` 和文本规整。 |
| 抽取层 | 要求 LLM 输出带引用和置信度的结构化 facts。 | 新增纯文本抽取 prompts 和 parser 测试。 |
| 校验层 | 检查尺寸、word 布局、轮数、操作支持、表、常数和密钥编排完整性。 | 独立于 LLM 的确定性 validator。 |
| 草稿层 | 将 facts 映射为 `CipherSpecDraft`，再映射到 `CipherSpec`。 | 显式草稿 schema 和转换 helper。 |
| 确认层 | 展示假设、警告、缺失字段和拟定 `CipherSpec`。 | CLI/web 构建或求解前的审阅步骤。 |
| 执行层 | 用户确认后构建 OCP primitive 并运行请求的工作流。 | 复用现有 `OCPAgent` skills。 |
| 网页层 | 提供编辑器、provider 设置、草稿审阅、任务历史和产物。 | 先做文本工作区，再做高级上传。 |
| 存储层 | 记录可复现 job、prompt、规整输入、草稿 spec 和输出路径。 | 在可配置输出目录下保存 JSON job 记录。 |

## 数据契约

### `CipherInput`

必需字段：

- `raw_text`：用户原始文本。
- `source_type`：`direct_text`、`uploaded_text`、`markdown`、`latex` 或
  `pseudocode`。
- `format_hint`：用户提供或系统推断的格式。
- `language_hint`：`en`、`zh`、`mixed` 或 `unknown`。

关键行为：

- 保留原始文本。
- 规整 `\oplus`、`\boxplus`、`\lll`、`\ggg` 等 LaTeX token。
- 尽量保留来源位置，让抽取出的 facts 可以指回用户文本。

### `CipherFacts`

Facts 是中间证据，不是可执行代码：

- 名称和 primitive 类型。
- 状态大小、word 大小、word 数量和布局。
- 轮数和轮函数步骤。
- 支持的操作：XOR、AND、OR、NOT、旋转、移位、模加、S-box、置换、
  matrix/linear layer、轮密钥加、常数加。
- S-box 表、置换表、矩阵、常数和测试向量。
- block cipher 的密钥编排 facts。
- 歧义、假设、不支持操作和来源引用。

### `CipherSpecDraft`

草稿应可审阅：

- 拟定的 `CipherSpec` 字典。
- 阻塞性校验错误。
- 非阻塞警告。
- Agent 做出的假设。
- 澄清问题。
- 默认 `requires_user_confirmation = True`。

## Provider 要求

Provider factory 应支持：

- OpenAI。
- 通过 OpenAI-compatible API 接入的 DeepSeek。
- 可配置 `base_url`、model 和 API key 环境变量的通用 OpenAI-compatible API。
- Anthropic。
- Gemini。
- 本地 Ollama。

抽取流水线只应依赖内部 `LLMProvider` 接口。Provider 特有逻辑应留在各 provider 类内部。

## 网页端要求

网页端应提供真正的文本工作区：

- 大文本编辑器，用于输入密码算法描述。
- 格式选择：auto、plain text、Markdown、LaTeX、pseudocode。
- Provider 选择器，包含 model、base URL 和 API key 字段。
- 将 “Extract facts”、“Validate draft”、“Build cipher”、“Run analysis” 和
  “Generate code” 拆成独立步骤。
- 草稿审阅面板，展示假设、警告、缺失字段和引用。
- 可编辑的 `CipherSpec` JSON 预览。
- Job 历史和产物下载。
- 当 solver 或 provider 不可用时，给出清晰 disabled 状态。

## 安全与确认

以下动作必须先确认：

- 从 LLM 生成的草稿构建自定义 cipher。
- 写出生成实现。
- 运行依赖求解器的 cryptanalysis。
- 保存或覆盖产物。

确认视图应展示：

- 即将构建或执行什么。
- 哪个 provider/model 生成了草稿。
- 还剩哪些假设。
- 将使用哪个可选 solver 后端。
- 产物会写到哪里。

## 测试计划

- 文本规整和 LaTeX token 处理单测。
- 使用固定 LLM-like JSON 响应的 parser 测试。
- 针对缺失状态大小、不支持操作、表格式错误、word 数量不一致和密钥编排不完整的校验测试。
- DeepSeek 和 OpenAI-compatible 默认配置的 provider factory 测试。
- Provider 配置、文本抽取请求校验和确认门槛的 Web API 测试。
- 为简单 ARX、SPN、S-box/置换和 block-cipher key schedule 输入建立 golden examples。

## 实现里程碑

1. 最终确定 `CipherInput`、`CipherFacts` 和 `CipherSpecDraft` schema。
   初始 dataclass 和确定性校验 helper 已就位。
2. 将 PDF/image-first 抽取 prompt 替换为 text-first 抽取 prompt。
   初始 text-first facts prompt 和 parser 边界已就位。
3. 添加确定性 validator 和 draft-to-spec 转换 helper。
   初始 facts 校验和 draft 转换已就位。
4. 添加 `extract_cipher_facts`、`draft_cipher_spec` 和 `confirm_cipher_spec` 直接 API。
5. 添加 CLI 确认流程。
6. 添加网页文本工作区和草稿审阅 UI。
7. 添加可复现 job 记录和产物链接。
8. 将 PDF/image 抽取降级为 experimental import helper。

## 待确认问题

- `CipherFacts` 的来源位置应使用 byte offset、行列范围，还是两者都存？
- 网页端应允许编辑 facts、最终 `CipherSpec`，还是两者都允许？
- 第一批 golden examples 应优先覆盖哪些 cipher family：ARX、SPN、Feistel、GFN 还是 stream cipher？
- Solver 能力检查应在抽取前展示、分析前展示，还是两个阶段都展示？
