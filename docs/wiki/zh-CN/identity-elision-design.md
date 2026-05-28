# Identity Elision 设计

语言：[English](../en/identity-elision-design.md) | **中文**

OCP 目前会在每个 layer 边界创建显式变量，并为未被当前 operator 更新的 word 生成
`Equal` 约束。这种设计清晰、稳健，但 ARX primitive 的 SAT/MILP 模型中有相当一部分
约束都花在结构性 identity 传播上。

## 目标

通过变量别名替换部分内部 identity 链，减少生成模型大小，同时保持 public primitive API、
图语义、trail 格式化、实现生成和求解行为不变。

## 当前原型

当前实现只做诊断，不会删除约束：

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

## 实现计划

1. 在 primitive 图构建完成后，为候选 identity operator 构建 alias map。
2. 模型生成阶段通过 alias map 重写变量名。
3. display dictionary 和 trace metadata 需要感知 alias，这样用户仍然能检查原始分层图。
4. 增加 opt-in 配置，例如 `config_model["identity_elision"]`。
5. 对比 profiler baseline 后，再考虑是否默认启用。

## 安全规则

- 第一版不要 elide primitive 输入/输出链接。
- 在 trail extraction 和 visualization 完成 alias 验证前，不要 elide 轮间链接。
- 不直接修改现有变量 ID，而是维护外部 alias map。
- 保持生成实现代码不变。
- 改默认行为前，至少为 PRESENT、ChaCha、Salsa、Forro 补 SAT 和 MILP 回归测试。
