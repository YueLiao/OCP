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

The current implementation has two modes. The default profiler reports
diagnostic candidates only:

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

The opt-in prototype can also generate a model with those candidates skipped and
their variable names rewritten through an alias map:

```bash
python -m tools.profile_model_generation forro:1 --identity-elision
```

For `forro:1`, the SAT model drops from 16,586 constraints to 5,066 constraints
in the current baseline. The MILP model drops from 10,029 constraints to 4,089.
This mode is still experimental and is not enabled by default.

## Implementation Plan

1. Verify visualization with aliases.
2. Add solver-backed smoke tests when optional solver CI is available.
3. Compare profiler baselines before enabling it by default.

## Safety Rules

- Do not elide primitive input/output links in the first implementation.
- Do not elide round-link constraints until trail extraction and visualization
  are verified with aliases.
- Do not mutate existing variable IDs; maintain an external alias map.
- Keep generated implementations unchanged.
- Require broader regression tests for at least PRESENT, ChaCha, Salsa, and
  Forro before changing defaults.
- Trail extraction must resolve missing original-layer variables through the
  alias map while keeping the original layered graph in the rendered trail.
