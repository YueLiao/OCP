# 性能基线

语言：[English](../en/performance-baseline.md) | **中文**

本页记录轻量级模型生成基线。该命令只构建约束，不调用外部求解器。

```bash
python -m tools.profile_model_generation --indent 0
python -m tools.profile_model_generation forro:1 --top-limit 5
```

快照日期：2026-05-28。
环境：本机 macOS 上的 `ocp` conda 环境。
模型：`DIFFERENTIALPATH_PROB`，SAT，每个 primitive 取一轮/一个 subround。

## 基线

| Case | 约束数量 | 主要热点 |
|---|---:|---|
| `present:1` | 1,280 | `PRESENT_Sbox` 896 条约束，`Equal` 384 |
| `chacha:1` | 20,848 | `Equal` 11,264，`ModAdd` 6,512 |
| `salsa:1` | 22,896 | `Equal` 13,312，`ModAdd` 6,512 |
| `forro:1` | 16,586 | `Equal` 13,568，`ModAdd` 2,442 |

耗时会随机器和 Python 运行时波动，因此不作为硬性断言。约束数量和 operator
调用次数更稳定，已经通过回归测试覆盖。

Profiler 还会输出 `operator_prefixes`，按 operator 类型和 ID 前缀聚合约束。例如
`Equal:IN_LINK_EQ` 表示 primitive 输入链接，`Equal:Add1_EQ` 表示 `Add1`
层周围未被更新 word 的 identity 传播。

为了快速查看，每份报告还会包含 `top_operators` 和 `top_operator_prefixes`，
按生成约束数量排序。可以用 `--top-limit` 控制摘要行数。
`identity_elision_candidates` 会保守估算未来基于 alias 的优化可能移除的内部
identity 约束子集。详见 [Identity Elision 设计](identity-elision-design.md)。
传入 `--identity-elision` 会启用实验性 alias pass，并报告模型生成阶段实际降低后的约束数量。

## 如何理解这些数字

- ARX primitive 中 `Equal` 占比较高，因为层间状态传递和输入/输出链接都被显式建模。
- 除状态链接外，`ModAdd` 是 ARX 模型中最主要的非线性建模成本。
- Salsa 的 round function 使用临时 word，因此一轮 SAT 模型比 ChaCha 更大。
- Forro 每个 subround 的 modular addition 更少，但结构链接仍占一轮模型的大头。
- Forro 一个 subround 的 `Equal` 约束分散在输入链接、输出链接以及每个 ARX 层未被更新的
  word 上。因此如果要显著减少约束数量，需要设计变量别名或 identity-elision 方案，
  不能只做局部删除。

## 优化方向

近期优化应在保持图语义不变的前提下减少重复结构工作：

1. 继续集中维护 ARX layer builder，让 ChaCha、Salsa、Forro 使用同一套经过测试的构建方式。
2. 当模型参数不变时，避免重复生成相同的 S-box、matrix 和 template artifact。
3. 优化 solver-facing 输出前先 profiling，因为模型生成和求解阶段的热点不同。
