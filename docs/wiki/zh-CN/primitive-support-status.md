# Primitive 支持状态

语言：[English](../en/primitive-support-status.md) | **中文**

本页记录那些源码文件已经存在、但支持变体或验证覆盖仍有意受限的 primitive 状态。

## Agent Catalog

Agent catalog 只暴露已经足够适合用户工作流的内置 primitive factory 和 variant。

- `shacal2`：只暴露已实现的 256-bit 变体。
- `trivium`：暂不通过 Agent catalog 暴露。

## Core 原型

部分 core primitive 模块仍可作为研究脚手架使用，但不应被当作完整且已验证的实现。

| Primitive | 状态 | 说明 |
|---|---|---|
| `primitives.shacal2` | 变体覆盖不完整 | 256-bit 路径已实现，并有已登记测试向量。512-bit 常量表和测试向量覆盖仍未完成。 |
| `primitives.trivium` | 原型 | 该模块能构建图结构骨架，但完整 Trivium update equations 和官方测试向量尚未完成。 |

## 贡献规则

- 不要把未完成变体加入 Agent catalog。
- 在通过用户 API 暴露某个变体前，先添加显式版本校验。
- 至少添加一个非平凡测试向量后，再把 primitive 变体写作文档中的 supported。
- 原型在实现生成和模型生成都有聚焦回归测试前，应继续明确标为 prototype。
