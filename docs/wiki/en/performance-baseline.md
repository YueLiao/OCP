# Performance Baseline

Language: **English** | [中文](../zh-CN/performance-baseline.md)

This page records a lightweight model-generation baseline. The command builds
constraints only; it does not call external solvers.

```bash
python -m tools.profile_model_generation --indent 0
python -m tools.profile_model_generation forro:1 --top-limit 5
```

Snapshot date: 2026-06-01.
Environment: local `ocp` conda environment on macOS.
Model: `DIFFERENTIALPATH_PROB`, SAT, one round/subround per primitive.

Follow-up snapshot date: 2026-06-02.
The follow-up run used:

```bash
python -m tools.profile_model_generation forro:1 chacha:1 salsa:1 --identity-elision --top-limit 3
python -m tools.profile_model_generation present:1 forro:1 --top-limit 3
```

Upstream-merge recheck date: 2026-06-07.
After merging Open-CP/OCP `513963a` (`update operators`), the same profiling
commands were re-run to confirm that the operator-model updates did not regress
the existing generation baselines.

## Baseline

| Case | Constraints | Top Hotspots |
|---|---:|---|
| `present:1` | 1,264 | `PRESENT_Sbox` 880 constraints, `Equal` 384 |
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

For quick inspection, each report also includes `top_operators` and
`top_operator_prefixes`, sorted by generated constraint count. Use
`--top-limit` to control how many rows are included in those summaries.
`identity_elision_candidates` estimates the conservative subset of internal
identity constraints that could be removed by a future alias-based pass. See
[Identity Elision Design](identity-elision-design.md).
Passing `--identity-elision` enables the experimental alias pass and reports the
actual reduced constraint count for model generation.

## Identity-Elision Opt-In Baseline

| Case | SAT Baseline | SAT Elided | MILP Baseline | MILP Elided |
|---|---:|---:|---:|---:|
| `chacha:1` | 20,848 | 11,632 | 15,440 | 10,688 |
| `salsa:1` | 22,896 | 11,632 | 16,496 | 10,688 |
| `forro:1` | 16,586 | 5,066 | 10,029 | 4,089 |

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
- PRESENT's S-box template cache is keyed by S-box table fingerprint, so the
  current minimized template is isolated from other S-boxes that share a model
  version.

The 2026-06-02 follow-up confirms the same direction:

- `forro:1` SAT drops from 16,586 constraints to 5,066 with
  `--identity-elision`, skipping 180 internal identity constraints through
  aliases.
- `chacha:1` and `salsa:1` SAT both report 11,632 elided constraints, with
  `ModAdd` as the largest remaining operator group.
- `present:1` remains dominated by `PRESENT_Sbox`: 880 of 1,264 constraints in
  the non-elided SAT snapshot.

The 2026-06-07 upstream-merge recheck kept the same constraint counts:

- `forro:1` SAT remains 16,586 constraints without elision and 5,066 with
  `--identity-elision`.
- `chacha:1` and `salsa:1` SAT remain 11,632 constraints with
  `--identity-elision`; `ModAdd` remains the largest operator group.
- `present:1` remains 1,264 SAT constraints, with `PRESENT_Sbox` contributing
  880 constraints.

## Optimization Direction

Near-term optimization should focus on preserving graph semantics while
reducing repeated structural work:

1. Keep ARX layer builders centralized so ChaCha, Salsa, and Forro use the same
   tested construction idioms.
2. Avoid regenerating identical S-box, matrix, and template artifacts when the
   model parameters are unchanged.
3. Profile before optimizing solver-facing output, because generation and
   solving have different hotspots.
