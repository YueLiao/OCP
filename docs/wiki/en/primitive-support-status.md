# Primitive Support Status

Language: **English** | [中文](../zh-CN/primitive-support-status.md)

This page records implementation status for primitives whose source files exist
but whose supported variants or validation coverage are intentionally limited.

## Agent Catalog

The Agent catalog exposes built-in primitives only when the factory and variant
are safe enough for user-facing workflows.

- `shacal2`: exposed for the implemented 256-bit variant.
- `trivium`: not exposed through the Agent catalog yet.

## Core Prototypes

Some core primitive modules remain useful as research scaffolding but should not
be treated as complete, verified implementations.

| Primitive | Status | Notes |
|---|---|---|
| `primitives.shacal2` | Partial variant coverage | The 256-bit path is implemented and has a checked-in test vector. The 512-bit constant table and test vector coverage remain incomplete. |
| `primitives.trivium` | Prototype | The module builds a graph skeleton, but the full Trivium update equations and official test vectors are not complete. |

## Contributor Rules

- Do not add incomplete variants to the Agent catalog.
- Add explicit version validation before exposing a variant through user-facing
  APIs.
- Add at least one nontrivial test vector before documenting a primitive variant
  as supported.
- Keep prototypes documented as such until implementation generation and model
  generation have focused regression tests.
