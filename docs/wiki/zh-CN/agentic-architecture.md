# Agentic 架构

语言：[English](../en/agentic-architecture.md) | **中文**

本文描述当前标准化后的 Agent 目标架构。目标是一套可用、稳定、文本优先的密码分析助手，
并且在高风险步骤前有明确确认点，所有产物都能追踪和复现。

## 分层

| 层级 | 职责 |
|---|---|
| Provider | 将 OpenAI、DeepSeek、OpenAI-compatible、Anthropic、Gemini 和 Ollama 统一到 `LLMProvider` 后面。 |
| Planner | 将用户文本转换为 skill 调用，或进入草稿/审阅流程。 |
| Skill executor | 通过 `AgentCore` 一次执行一个 `SkillRequest`，返回 `SkillResult`。 |
| Validator | 确定性校验 `CipherInput`、`CipherFacts`、`CipherSpecDraft` 和 `CipherSpec`。 |
| Verifier | 在构建、求解、代码生成或可视化前运行轻量冒烟检查。 |
| Artifact manager | 通过 `artifact_links` 返回生成文件，并记录可复现 JSON job。 |
| Session | 保存当前 cipher、待确认 facts、待确认 draft、job 记录、近期结果和执行 trace。 |
| Web/API | 用稳定 JSON 响应暴露 draft、confirm、analyze、code 和 visualize 动作。 |

## 错误边界

面向用户的边界应先分类错误再返回：

- JSON 请求体缺失或非法：HTTP 400，`error_code=invalid_json`。
- Provider/API key/配置缺失：HTTP 400，返回 provider 相关提示。
- 文本为空或文件类型不支持：HTTP 400 或 `SkillResult(success=False)`。
- LLM 解析失败：`SkillResult(success=False)`，说明未获得可解析 facts。
- Skill 内部失败：在 skill 边界包装成 `SkillResult(success=False)`。
- 非预期 route/provider 初始化失败：HTTP 500，并带 `error_code` 便于诊断。

`/api/analyze`、`/api/code` 和 `/api/visualize` 要求传入 `confirmed=true`。
网页端会先弹出确认，因为这些动作可能运行外部 solver 或写出产物。

## 标准响应形状

执行 skill 的 Web endpoint 应返回：

```json
{
  "success": true,
  "skill": "code_generation",
  "summary": "Generated ...",
  "error": null,
  "data": {},
  "artifact_links": [],
  "context": {}
}
```

`artifact_links` 是生成代码、trail JSON/TXT、可视化 PDF 和 job 记录的稳定出口。

Agent 也会把 links 扩展为结构化 `artifacts`：

```json
{
  "id": "stable sha256-derived id",
  "label": "generated_code",
  "path": "/tmp/ocp-files/SPECK32_64.py",
  "type": "source",
  "source_skill": "code_generation",
  "exists": true,
  "created_at": "2026-05-28T..."
}
```

`/api/status` 会返回最近 trace 和 session artifact registry，供网页侧边栏展示。

## 文本优先流程

1. 用户提交纯文本、Markdown、LaTeX 或伪代码。
2. `extract_cipher_facts()` 调用配置好的 provider 抽取结构化 facts。
3. 确定性 validator 分类阻塞错误和警告。
4. `draft_cipher_spec()` 创建可审阅草稿。
5. 用户确认草稿。
6. `confirm_cipher_spec()` 构建 OCP primitive。
7. 用户分别运行分析、代码生成或可视化动作。

PDF/图片上传仍是实验性辅助，应进入同一套审阅流程。

## Web 动作

网页端暴露：

- `POST /api/text/draft`
- `POST /api/text/confirm`
- `POST /api/analyze`
- `POST /api/code`
- `POST /api/visualize`
- `POST /api/upload`

页面在 cipher 可用后提供差分分析、线性分析、代码生成和可视化按钮。

可以使用 `GET /api/solvers` 或 `OCPAgent().solver_capabilities()` 在运行求解器分析前检查
可用后端。
