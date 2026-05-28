# Identity Elision 设计

语言：[English](../en/identity-elision-design.md) | **中文**

OCP 目前会在每个 layer 边界创建显式变量，并为未被当前 operator 更新的 word 生成
`Equal` 约束。这种设计清晰、稳健，但 ARX primitive 的 SAT/MILP 模型中有相当一部分
约束都花在结构性 identity 传播上。

## 目标

通过变量别名替换部分内部 identity 链，减少生成模型大小，同时保持 public primitive API、
图语义、trail 格式化、实现生成和求解行为不变。

## 当前原型

当前实现有两种模式。默认 profiler 只报告诊断候选：

```bash
python -m tools.profile_model_generation forro:1 --top-limit 5
```

JSON 报告中会包含 `identity_elision_candidates`：

- `estimated_constraints`：可能可移除的内部 identity 约束数量。
- `estimated_ratio`：候选约束占总生成约束的比例。
- `top_candidates`：最大的候选前缀。

候选检测是保守的。它会包含 `Equal:Add1_EQ` 这样的内部 layer identity，
但会排除 primitive 输入链接、输出链接和轮间链接，例如 `Equal:IN_LINK_EQ`、
`Equal:OUT_LINK_EQ`、`Equal:LINK_EQ`。

opt-in 原型也可以跳过这些候选约束，并通过 alias map 重写模型变量名：

```bash
python -m tools.profile_model_generation forro:1 --identity-elision
```

在当前基线里，`forro:1` 的 SAT 模型会从 16,586 条约束降到 5,066 条约束。
MILP 模型会从 10,029 条约束降到 4,089 条约束。该模式仍是实验性的，默认不会启用。

## 已验证边界

- Trail extraction 会通过 alias map 解析缺失的原始层变量，同时在渲染 trail
  时保留原始分层图。
- Visualization 继续读取 primitive graph。Identity elision 不会修改 primitive
  对象中的 constraint ID、variable ID 或 Equal 边。

## 实现计划

1. 当可选 solver CI 可用后，增加 solver-backed smoke test。
2. 对比 profiler baseline 后，再考虑是否默认启用。

## 安全规则

- 第一版不要 elide primitive 输入/输出链接。
- 不 elide 轮间链接；当前验证只覆盖保守的内部 identity。
- 不直接修改现有变量 ID，而是维护外部 alias map。
- 保持生成实现代码不变。
- 改默认行为前，至少为 PRESENT、ChaCha、Salsa、Forro 补更广的回归测试。
- Trail extraction 必须能通过 alias map 解析缺失的原始层变量，同时渲染时仍保留原始分层图。
