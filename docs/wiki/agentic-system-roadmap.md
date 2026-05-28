# OCP Agentic System Roadmap / OCP Agentic 系统路线图

Status: proposal for review. Do not implement until the codebase refactor
baseline is stable and this roadmap is confirmed.

状态：待评审方案。代码重构基线稳定且本路线图确认前，不进入功能实现。

## Direction Change / 方向调整

The original Agent design mentions PDF and image extraction. In practice, VLM
recognition is not reliable enough for cryptographic specifications: formulas,
tables, state layouts, and bit-index conventions are easy to misread. The next
Agentic system should prioritize **user-provided text**.

原 Agent 设计曾支持 PDF 和图片抽取。但实践上，VLM 对密码算法规格的识别还不够可靠：
公式、表格、状态布局、bit 编号规则都容易误读。下一阶段 Agentic 系统应优先支持
**用户提供的纯文本描述**。

Accepted input should include:

输入形式应支持：

- Plain text copied from papers or notes.
- Markdown descriptions.
- LaTeX fragments, equations, algorithm environments, and tables.
- Pseudocode.
- Mixed Chinese/English descriptions.
- User-authored structured notes.

- 从论文或笔记复制出的纯文本。
- Markdown 描述。
- LaTeX 片段、公式、算法环境和表格。
- 伪代码。
- 中英文混合描述。
- 用户自己整理的结构化笔记。

PDF/image ingestion can remain as a lower-priority helper, but should no longer
be the primary path for accurate cipher specification.

PDF/图片输入可以保留为低优先级辅助能力，但不应再作为准确抽取密码规格的主路径。

## Product Goal / 产品目标

Build a robust Agentic workflow that converts human-readable cipher descriptions
into validated OCP `CipherSpec` objects, then builds, analyzes, visualizes, and
generates code for the cipher with explicit user confirmation at risky points.

构建一套扎实的 Agentic 工作流：将人类可读的密码算法描述转换成经过校验的 OCP
`CipherSpec`，再在关键风险点经过用户确认后完成构建、分析、可视化和代码生成。

## Core Workflow / 核心工作流

1. User provides text, Markdown, LaTeX, or pseudocode.
2. Agent normalizes the text into a canonical internal representation.
3. Agent extracts candidate cipher facts.
4. Agent checks completeness, consistency, and OCP supportability.
5. Agent asks targeted clarification questions when needed.
6. Agent builds a `CipherSpec`.
7. Agent runs static validation and small construction smoke tests.
8. Agent presents a human-readable review.
9. User confirms.
10. Agent builds the OCP primitive and offers analysis/codegen/visualization.

1. 用户提供文本、Markdown、LaTeX 或伪代码。
2. Agent 将输入规整为统一内部表示。
3. Agent 抽取候选密码事实。
4. Agent 检查完整性、一致性和 OCP 可支持性。
5. 信息不足时，Agent 提出有针对性的澄清问题。
6. Agent 构建 `CipherSpec`。
7. Agent 运行静态校验和小型构建冒烟测试。
8. Agent 向用户展示可读的规格审阅稿。
9. 用户确认。
10. Agent 构建 OCP primitive，并提供分析、代码生成和可视化选项。

## Proposed Architecture / 建议架构

### 1. Input Layer / 输入层

Responsibilities:

职责：

- Accept direct text from CLI, Python API, and web UI.
- Accept `.txt`, `.md`, `.tex`, `.rst` uploads.
- Preserve raw input in session metadata.
- Normalize line endings and remove irrelevant frontmatter if requested.
- Keep source spans for traceability when possible.

- 从 CLI、Python API、网页端接收直接文本。
- 接收 `.txt`、`.md`、`.tex`、`.rst` 上传。
- 在 session metadata 中保留原始输入。
- 标准化换行，并在用户允许时移除无关 frontmatter。
- 尽量保留来源片段位置，便于追踪。

### 2. Text Normalization Layer / 文本规整层

Responsibilities:

职责：

- Preserve mathematical meaning while reducing formatting noise.
- Convert common LaTeX symbols to canonical tokens:
  - `\oplus` -> XOR
  - `\boxplus` -> modular addition
  - `\lll`, `\ggg`, `\rotateleft`, `\rotateright` -> rotations
- Extract algorithm blocks and tables.
- Keep original table text alongside parsed candidate values.

- 保留数学含义，同时减少格式噪声。
- 将常见 LaTeX 符号转为统一 token：
  - `\oplus` -> XOR
  - `\boxplus` -> modular addition
  - `\lll`、`\ggg`、`\rotateleft`、`\rotateright` -> rotation
- 抽取算法块和表格。
- 解析候选表值时保留原始表文本。

### 3. Fact Extraction Layer / 事实抽取层

The extractor should produce an intermediate `CipherFacts` object rather than
jumping directly to `CipherSpec`.

抽取器应先产生中间对象 `CipherFacts`，不要直接跳到 `CipherSpec`。

Candidate facts:

候选事实：

- Cipher name and family.
- Primitive type: permutation, block cipher, stream cipher, keyed permutation.
- Block/state size.
- Word/nibble/bit layout.
- 2D state layout: rows, columns, row-major/column-major mapping.
- Number of rounds.
- Round operations in exact order.
- S-box tables.
- Permutation tables.
- Linear/matrix layers.
- Round constants.
- Key schedule.
- Test vectors.
- Ambiguities and confidence notes.

- 密码名称和族类。
- primitive 类型：permutation、block cipher、stream cipher、keyed permutation。
- block/state 大小。
- word/nibble/bit 布局。
- 二维状态布局：行数、列数、row-major/column-major 映射。
- 轮数。
- 精确顺序的轮函数操作。
- S 盒表。
- 置换表。
- 线性/矩阵层。
- 轮常数。
- 密钥编排。
- 测试向量。
- 歧义和置信度说明。

### 4. Validation and Dialogue Layer / 校验与对话层

Responsibilities:

职责：

- Detect missing required fields.
- Detect inconsistent sizes, e.g. `block_size != word_bitsize * nbr_words`.
- Detect unsupported constructs before build time.
- Ask compact clarification questions.
- Present a reviewable summary before building.

- 检测缺失字段。
- 检测尺寸不一致，例如 `block_size != word_bitsize * nbr_words`。
- 在构建前发现 OCP 暂不支持的结构。
- 提出简洁澄清问题。
- 构建前展示可审阅摘要。

Clarification should be targeted, not generic. Example:

澄清问题应有针对性，而不是泛泛提问。例如：

```text
The text says the S-box is applied to columns of a 4x16 state.
Should bit index 0 mean row 0 column 0, and bit index 16 mean row 1 column 0?
```

### 5. Planning and Execution Layer / 规划与执行层

Agent execution should be explicit and resumable:

Agent 执行应明确且可恢复：

- `parse_text`
- `extract_facts`
- `validate_facts`
- `ask_clarification`
- `formalize_cipher_spec`
- `review_spec`
- `build_cipher`
- `run_analysis`
- `generate_code`
- `visualize`

Each step should write a `SkillResult` and update session metadata.

每一步都应写入 `SkillResult` 并更新 session metadata。

### 6. Web UI / 网页端

The web UI should become a real workspace, not only a chat box.

网页端应升级为真正的工作台，而不仅是聊天框。

Required views:

必要视图：

- Text input editor with Markdown/LaTeX-friendly formatting.
- Uploaded text file panel.
- Extraction progress timeline.
- Candidate facts table.
- `CipherSpec` JSON viewer/editor.
- Human-readable cipher summary.
- Clarification question panel.
- Build/analyze/codegen action panel.
- Results panel with trails, generated files, and errors.

- 支持 Markdown/LaTeX 的文本输入编辑器。
- 上传文本文件面板。
- 抽取进度时间线。
- 候选事实表。
- `CipherSpec` JSON 查看/编辑器。
- 人类可读的密码规格摘要。
- 澄清问题面板。
- 构建/分析/代码生成操作面板。
- 结果面板，展示 trail、生成文件和错误。

The web UI should support local single-user mode first. Multi-user persistence
can be a later phase.

网页端应先支持本地单用户模式。多用户持久化可以放到后续阶段。

## LLM Provider Support / LLM Provider 支持

Current providers:

当前已有 provider：

- OpenAI
- DeepSeek
- Generic OpenAI-compatible endpoint
- Anthropic
- Gemini
- Ollama

Potential future providers:

未来可选：

- OpenRouter or other model routers, only if needed.

### DeepSeek Notes / DeepSeek 说明

DeepSeek's official API is OpenAI-compatible. Official docs list:

DeepSeek 官方 API 兼容 OpenAI 格式。官方文档列出：

- `base_url`: `https://api.deepseek.com`
- OpenAI-compatible alternative: `https://api.deepseek.com/v1`
- `deepseek-chat`: chat model line.
- `deepseek-reasoner`: reasoning model line.
- JSON Output support via `response_format={"type": "json_object"}`.
- Function Calling / Tool Calls support.

Sources:

来源：

- DeepSeek quick start: https://deepseek.apidog.io/
- DeepSeek API features: https://api-docs.deepseek.com/news/news0725/

Implemented design choice:

已采用的设计：

DeepSeek is implemented as a thin preset over a generic OpenAI-compatible
provider first. This keeps behavior simple while leaving room for
DeepSeek-specific JSON mode, reasoning content, and tool-call handling later.

DeepSeek 已先作为通用 OpenAI-compatible provider 上的轻量 preset 实现。这样当前行为
简单明确，同时为后续 DeepSeek 专属 JSON mode、reasoning content、tool-call 兼容保留空间。

## Data Models / 数据模型

### `CipherInput`

```python
{
  "source_type": "direct_text | file_upload",
  "format_hint": "plain | markdown | latex | pseudocode | mixed",
  "raw_text": "...",
  "source_name": "...",
  "language_hint": "en | zh | mixed | unknown"
}
```

### `CipherFacts`

```python
{
  "name": "...",
  "primitive_type": "...",
  "state": {...},
  "rounds": {...},
  "operations": [...],
  "tables": {...},
  "key_schedule": {...},
  "test_vectors": [...],
  "ambiguities": [...],
  "source_spans": [...]
}
```

### `CipherSpecDraft`

`CipherSpecDraft` is a validated-but-not-yet-confirmed `CipherSpec` plus notes.

`CipherSpecDraft` 是已经校验但尚未确认的 `CipherSpec` 加注释说明。

```python
{
  "spec": {...},
  "validation_errors": [...],
  "warnings": [...],
  "assumptions": [...],
  "requires_user_confirmation": true
}
```

## TODO List / TODO 清单

### Phase A: Documentation and Design / A 阶段：文档与设计

- [ ] Confirm this roadmap.
- [x] Define `CipherInput`, `CipherFacts`, and `CipherSpecDraft` dataclasses.
- [ ] Define accepted text formats and examples.
- [x] Decide DeepSeek provider shape: generic OpenAI-compatible plus DeepSeek preset.
- [ ] Define web UI wire protocol for text extraction sessions.

- [ ] 确认本路线图。
- [x] 定义 `CipherInput`、`CipherFacts`、`CipherSpecDraft` dataclass。
- [ ] 定义可接受文本格式和示例。
- [x] 决定 DeepSeek provider 形态：通用 OpenAI-compatible 加 DeepSeek preset。
- [ ] 定义网页端文本抽取 session 的接口协议。

### Phase B: Backend Agent Core / B 阶段：后端 Agent 核心

- [ ] Add text-first extraction skill: `cipher_text_extraction`.
- [ ] Keep old file extraction but mark PDF/image as experimental.
- [x] Add Markdown/LaTeX normalization helpers.
- [ ] Add intermediate fact extraction prompt.
- [ ] Add fact validation before `CipherSpec` formalization.
- [ ] Add clarification loop driven by validation errors.
- [ ] Add JSON-mode calls where supported.
- [ ] Add fake LLM provider tests for deterministic parsing behavior.

- [ ] 添加文本优先抽取 skill：`cipher_text_extraction`。
- [ ] 保留旧文件抽取，但将 PDF/图片标记为 experimental。
- [x] 添加 Markdown/LaTeX 规整工具。
- [ ] 添加中间事实抽取 prompt。
- [ ] 在 `CipherSpec` 形式化前增加事实校验。
- [ ] 基于校验错误添加澄清循环。
- [ ] 对支持的 provider 使用 JSON mode。
- [ ] 添加 fake LLM provider 测试，保证解析行为可测。

### Phase C: Provider Layer / C 阶段：Provider 层

- [x] Add `OpenAICompatibleProvider`.
- [x] Add DeepSeek preset:
  - env var: `DEEPSEEK_API_KEY`
  - default base URL: `https://api.deepseek.com`
  - default models: `deepseek-chat`, `deepseek-reasoner`
- [ ] Add provider capability flags:
  - JSON output
  - tool calls
  - vision
  - reasoning content
  - max context hint
- [x] Add provider configuration tests.

- [x] 添加 `OpenAICompatibleProvider`。
- [x] 添加 DeepSeek preset：
  - 环境变量：`DEEPSEEK_API_KEY`
  - 默认 base URL：`https://api.deepseek.com`
  - 默认模型：`deepseek-chat`、`deepseek-reasoner`
- [ ] 添加 provider 能力标记：
  - JSON output
  - tool calls
  - vision
  - reasoning content
  - max context hint
- [x] 添加 provider 配置测试。

### Phase D: Web UI / D 阶段：网页端

- [ ] Replace chat-only extraction flow with text workspace.
- [ ] Add direct text input with format selector.
- [ ] Add `.txt`, `.md`, `.tex`, `.rst` upload.
- [ ] Add progress timeline.
- [ ] Add candidate facts table.
- [ ] Add editable `CipherSpec` JSON panel.
- [ ] Add confirmation workflow before build.
- [x] Add provider selection for DeepSeek/OpenAI-compatible endpoints.

- [ ] 将纯聊天抽取流程升级为文本工作台。
- [ ] 添加带格式选择器的直接文本输入。
- [ ] 添加 `.txt`、`.md`、`.tex`、`.rst` 上传。
- [ ] 添加进度时间线。
- [ ] 添加候选事实表。
- [ ] 添加可编辑 `CipherSpec` JSON 面板。
- [ ] 构建前添加确认流程。
- [x] 添加 DeepSeek/OpenAI-compatible endpoint 的 provider 选择。

### Phase E: Safety and Verification / E 阶段：安全与验证

- [ ] Require user confirmation before building uncertain specs.
- [ ] Track assumptions explicitly.
- [ ] Add deterministic schema validation tests.
- [ ] Add golden text fixtures for ARX, SPN, Feistel, and 2D-state ciphers.
- [ ] Add regression tests for LaTeX operation parsing.
- [ ] Add small construction smoke tests for generated `CipherSpec`.

- [ ] 对不确定规格，构建前必须用户确认。
- [ ] 显式记录假设。
- [ ] 添加确定性的 schema 校验测试。
- [ ] 添加 ARX、SPN、Feistel、二维状态密码的 golden text fixture。
- [ ] 添加 LaTeX 操作解析回归测试。
- [ ] 对生成的 `CipherSpec` 添加小型构建冒烟测试。

## Out of Scope for First Implementation / 首轮不做

- Full PDF layout reconstruction.
- Image/VLM-based primary extraction.
- Multi-user web persistence.
- Automated cryptographic correctness proof.
- Blindly running expensive solver searches immediately after extraction.

- 完整 PDF 版面重建。
- 以图片/VLM 作为主抽取路径。
- 多用户网页持久化。
- 自动密码正确性证明。
- 抽取后立即盲跑昂贵求解任务。

## Review Questions / 待确认问题

1. Should PDF/image extraction remain visible in the UI, or be hidden under
   "experimental imports"?
2. Should DeepSeek be implemented as a preset of OpenAI-compatible provider or
   a dedicated provider class from the start?
3. Should `CipherFacts` be persisted as JSON files for debugging?
4. Should web UI allow direct manual edits to `CipherSpec`, or only guided edits?
5. Which cipher families should be used as golden fixtures first?

1. PDF/图片抽取是否继续显示在 UI 中，还是放到 “experimental imports” 下？
2. DeepSeek 一开始作为 OpenAI-compatible provider 的 preset，还是直接做专用 provider？
3. 是否将 `CipherFacts` 持久化为 JSON 文件以便调试？
4. 网页端是否允许直接手改 `CipherSpec`，还是只允许引导式修改？
5. 首批 golden fixture 应覆盖哪些密码族？
