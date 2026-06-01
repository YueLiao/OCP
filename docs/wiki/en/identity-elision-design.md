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

Current one-round/subround opt-in baselines:

| Case | SAT Baseline | SAT Elided | MILP Baseline | MILP Elided | Aliases |
|---|---:|---:|---:|---:|---:|
| `chacha:1` | 20,848 | 11,632 | 15,440 | 10,688 | 144 |
| `salsa:1` | 22,896 | 11,632 | 16,496 | 10,688 | 176 |
| `forro:1` | 16,586 | 5,066 | 10,029 | 4,089 | 180 |

This mode is still experimental and is not enabled by default.

Candidate selection is intentionally narrow: only single-input, single-output
`Equal` edges with matching word sizes are eligible. Alias construction rejects
conflicting outputs and alias cycles instead of silently producing ambiguous
models. Constraint rewriting resolves chained aliases and caches token
substitutions within each generated batch to avoid repeated alias parsing on
large SAT/MILP outputs.

## Verified Boundaries

- Trail extraction resolves missing original-layer variables through the alias
  map, including chained aliases, while keeping the original layered graph in
  rendered trails.
- Visualization continues to read the primitive graph. Identity elision does not
  mutate constraint IDs, variable IDs, or Equal edges in the primitive object.
- Reused model configuration dictionaries clear alias/profile state when
  identity elision is disabled again.
- Candidate guards reject mismatched widths, multi-variable Equal-like edges,
  alias conflicts, and alias cycles.

## Implementation Plan

1. Add solver-backed smoke tests when optional solver CI is available.
2. Compare profiler baselines before enabling it by default.
3. Validate trail extraction against solver-produced solutions for ChaCha,
   Salsa, and Forro.

## Safety Rules

- Do not elide primitive input/output links in the first implementation.
- Do not elide round-link constraints; current verification only covers
  conservative internal identities.
- Do not mutate existing variable IDs; maintain an external alias map.
- Keep generated implementations unchanged.
- Require broader regression tests for at least PRESENT, ChaCha, Salsa, and
  Forro before changing defaults.
- Trail extraction must resolve missing original-layer variables through the
  alias map while keeping the original layered graph in the rendered trail.
