# OCP Agentic 系统路线图

语言：[English](../en/agentic-system-roadmap.md) | **中文**

状态：待评审方案。代码重构基线稳定且本路线图确认前，不进入功能实现。

## 方向调整

原 Agent 设计曾提到 PDF 和图片抽取。但实践上，VLM 对密码算法规格的识别还不够可靠：公式、表格、
状态布局和 bit 编号规则都容易误读。下一阶段 Agentic 系统应优先支持**用户提供的纯文本描述**。

输入形式应支持：

- 从论文或笔记复制出的纯文本。
- Markdown 描述。
- LaTeX 片段、公式、算法环境和表格。
- 伪代码。
- 中英文混合描述。
- 用户自己整理的结构化笔记。

PDF/图片输入可以保留为低优先级辅助能力，但不应再作为准确抽取密码规格的主路径。

## 产品目标

构建一套扎实的 Agentic 工作流：将人类可读的密码算法描述转换成经过校验的 OCP `CipherSpec`
对象，再在关键风险点经过用户确认后完成构建、分析、可视化和代码生成。

## 核心工作流

1. 用户提供文本、Markdown、LaTeX 或伪代码。
2. Agent 将输入规整为统一内部表示。
3. Agent 抽取候选密码事实。
4. Agent 检查完整性、一致性和 OCP 可支持性。
5. 信息不足时，Agent 提出有针对性的澄清问题。
6. Agent 构建 `CipherSpec`。
7. Agent 运行静态校验和构建冒烟测试。
8. Agent 向用户展示可读的规格审阅稿。
9. 用户确认。
10. Agent 构建 OCP primitive，并提供分析、代码生成和可视化选项。

## 建议架构

- **输入层：** 规整文本，并保留来源片段。
- **抽取层：** 生成带置信度和引用位置的 `CipherFacts`。
- **校验层：** 检查尺寸、状态布局、轮数、操作支持情况和缺失值。
- **草稿层：** 将 facts 映射为 `CipherSpecDraft`。
- **确认层：** 展示简洁审阅稿，并提出有针对性的澄清问题。
- **执行层：** 用户确认后再构建 OCP 对象并运行分析。
- **网页层：** 提供文本编辑区、provider 设置、运行历史和产物下载。

## Provider 要求

系统应通过统一 provider factory 支持 OpenAI、DeepSeek、通用 OpenAI-compatible API、
Anthropic、Gemini 和本地 Ollama 模型。

## Todo

- 设计 `CipherFacts` 和 `CipherSpecDraft` schema。
- 添加纯文本抽取 prompts 和确定性 parser 测试。
- 添加带 provider 配置的网页文本工作区。
- 在代码执行或求解器运行前添加确认检查点。
- 为生成产物添加可复现 job 记录。
