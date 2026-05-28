# Identity Elision Design

Language: **English** | [中文](../zh-CN/identity-elision-design.md)

OCP currently models every layer boundary with explicit variables and `Equal`
constraints for words that are not updated by the active operator. This is
clear and robust, but ARX primitives spend a large share of their SAT/MILP
model on structural identity propagation.

## Goal

Reduce generated model size by replacing selected internal identity chains with
variable aliases, while preserving public primitive APIs, graph semantics, trail
formatting, implementation generation, and solver behavior.

## Current Prototype

The current implementation is diagnostic only:

```bash
python -m tools.profile_model_generation forro:1 --top-limit 5
```

The JSON report includes `identity_elision_candidates`:

- `estimated_constraints`: internal identity constraints that may be removable.
- `estimated_ratio`: candidate constraints divided by total generated constraints.
- `top_candidates`: largest candidate prefixes.

The candidate detector is conservative. It includes internal layer identities
such as `Equal:Add1_EQ` and excludes primitive input links, output links, and
round-link constraints such as `Equal:IN_LINK_EQ`, `Equal:OUT_LINK_EQ`, and
`Equal:LINK_EQ`.

## Implementation Plan

1. Build an alias map for candidate identity operators after primitive graph
   construction.
2. Rewrite model-generation variable names through that alias map.
3. Keep display dictionaries and trace metadata aware of aliases so users can
   still inspect the original layered graph.
4. Add opt-in configuration, for example `config_model["identity_elision"]`.
5. Compare profiler baselines before enabling it by default.

## Safety Rules

- Do not elide primitive input/output links in the first implementation.
- Do not elide round-link constraints until trail extraction and visualization
  are verified with aliases.
- Do not mutate existing variable IDs; maintain an external alias map.
- Keep generated implementations unchanged.
- Require SAT and MILP regression tests for at least PRESENT, ChaCha, Salsa,
  and Forro before changing defaults.
