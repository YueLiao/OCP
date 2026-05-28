# Performance Baseline

Language: **English** | [中文](../zh-CN/performance-baseline.md)

This page records a lightweight model-generation baseline. The command builds
constraints only; it does not call external solvers.

```bash
python -m tools.profile_model_generation --indent 0
```

Snapshot date: 2026-05-28.
Environment: local `ocp` conda environment on macOS.
Model: `DIFFERENTIALPATH_PROB`, SAT, one round/subround per primitive.

## Baseline

| Case | Constraints | Top Hotspots |
|---|---:|---|
| `present:1` | 1,280 | `PRESENT_Sbox` 896 constraints, `Equal` 384 |
| `chacha:1` | 20,848 | `Equal` 11,264, `ModAdd` 6,512 |
| `salsa:1` | 22,896 | `Equal` 13,312, `ModAdd` 6,512 |
| `forro:1` | 16,586 | `Equal` 13,568, `ModAdd` 2,442 |

Timings are intentionally not treated as hard assertions because they vary by
machine and Python runtime. Constraint counts and operator call counts are more
stable and are covered by regression tests.

The profiler also reports `operator_prefixes`, which groups constraints by
operator class and ID prefix. For example, `Equal:IN_LINK_EQ` identifies
primitive input links, while `Equal:Add1_EQ` identifies identity propagation
around an `Add1` layer.

## Reading the Numbers

- `Equal` dominates ARX primitives because layer transitions and state links are
  represented explicitly.
- `ModAdd` is the main nonlinear ARX modeling cost after state-link constraints.
- Salsa carries temporary words in the round function, so its one-round SAT
  model is larger than ChaCha's.
- Forro has fewer modular additions per subround, but a large share of its
  one-subround model is still structural linking.
- Forro's one-subround `Equal` constraints are distributed across input links,
  output links, and each ARX layer's untouched words. That means meaningful
  constraint-count reduction would require a planned variable-aliasing or
  identity-elision design, not a local deletion.

## Optimization Direction

Near-term optimization should focus on preserving graph semantics while
reducing repeated structural work:

1. Keep ARX layer builders centralized so ChaCha, Salsa, and Forro use the same
   tested construction idioms.
2. Avoid regenerating identical S-box, matrix, and template artifacts when the
   model parameters are unchanged.
3. Profile before optimizing solver-facing output, because generation and
   solving have different hotspots.
