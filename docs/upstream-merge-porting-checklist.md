# Upstream Merge — Porting Work Order

**Goal:** reconcile the OCP-agent core with upstream OCP by porting upstream's new
work onto the agent's (refactored) core, ahead of the eventual project merge.

| Field | Value |
|---|---|
| Upstream (OCP) | `https://github.com/Open-CP/OCP` — official core, adds features + docstrings |
| Fork (this repo, OCP-agent) | `https://github.com/YueLiao/OCP` — standardization refactor + agent/web |
| Fork point | `513963ae51bbaad2dcd5c5155d537e60ebc17afb` (2026-06-01) |
| Chosen base | **the agent's refactored core** (more evolved, has bug fixes, partially synced) |
| Analysis date | 2026-08-13 |
| Status | Not started |

> Line/anchor references below were captured at analysis time. **Re-verify anchors
> against current `HEAD` before editing** — the surrounding code may have shifted.

---

## TL;DR — the divergence is smaller than it looks

Raw diff across the 21 both-modified core files is ~5,900 lines, but most of that is
(a) the agent's own refactor and (b) upstream fixes the agent **already merged**
(`assert`→`raise`, SAT bit-indexing fix, mask validation, `fix_diff` length check — all
present). The genuine new work to port is **two features + a handful of fixes**:

1. **Two-subset integral distinguisher** (operators/Sbox, tools/model_constraints, tools helper).
2. **OR-Tools CPSAT SAT solver** (solving/solving.py — slot already scaffolded).
3. **AESround S-box version coverage** for differential & linear goals (one rules table).
4. A few isolated correctness fixes + two policy decisions.

**Only two genuinely HARD items remain:** `B1` (version-config decoupling) and `A2` (linear ELP).

**Estimated effort:** ~1–1.5 weeks incl. regression.

---

## Prerequisites & conventions (read before porting)

- **Do NOT port upstream's structural/style choices** that the agent deliberately changed:
  underscore-privatization of helpers, docstring rewrites, `gen_round_model_constraint_obj_fun`
  signature change (agent keeps `goal` and calls `configure_model_version` internally),
  removed `visualisations` import. These are intentional divergences — leave the agent's version.
- **Match agent conventions when porting logic:** lazy module loading (`import_module` in
  try/except, not top-level imports), `log()` from `tools.search_reporting` instead of `print`,
  centralized instrumentation in parent functions (don't duplicate monitors/timing), and the
  data-driven `GOAL_MODEL_VERSION_RULES` table instead of if/elif chains.
- **Regression is mandatory** after each package (see bottom).

---

## Package 0 — Quick correctness fixes (EASY, do first)

| ☐ | Item | File · anchor | Notes | Owner | Status |
|---|---|---|---|---|---|
| ☐ | Empty-vars guard (B3) | `tools/predefined_constraints.py:~59` | Add `if not cons_vars_name: return []` after `expand_constraint_vars(...)`, before the `builders[...]` return. Prevents malformed `" = 0"`. | | |
| ☐ | Matsui defensive copy (B5) | `tools/search_constraints.py:~51` (milp) & `~97` (sat) | Insert `obj_fun = list(obj_fun)` / `obj_var = list(obj_var)` before the trailing-`[]` popping `while`. Fixes latent caller-list mutation. | | |
| ☐ | Matrix unsupported model_type (B6) | `tools/bit_constraints.py:~144` & `~162` | Add `else: raise ValueError("Unsupported model_type ...")` inside each `len(vin) == 1` block (was silent `None` fall-through). | | |
| ☐ | OR-Tools capability probe fix | `solving/solving.py:~77-81` & `~78`/`~45` | In `solver_capabilities()["sat"]["ORTools"]`: `implemented=False`→`True`; change availability probe `_modules_available("ortools","ortoolslpparser")`→`_modules_available("ortools")`. `ortoolslpparser` keeps it permanently "unavailable". (Flag flip lands with Package 2.) | | |
| ☐ | Trail cipher-label round count (A3) | `attacks/common.py:~381` | `f"{cipher.functions['PERMUTATION'].nbr_rounds}_..."` → `f"{cipher.nbr_rounds}_..."`. **Shared by diff+linear — verify the two round counts are equal for all ciphers first.** Low value; optional. | | |

---

## Package 1 — AESround S-box coverage (the "sbox constraints" feature) — MED

The feature lives in **one rules table**, not in the attack files:
`tools/model_configuration.py` → `GOAL_MODEL_VERSION_RULES` (lines ~12-24). `set_model_versions`
matches `operator_name == cons.__class__.__name__`, so `AESround` needs explicit tuples
(the `"Sbox"` matcher only catches classes ending in `Sbox`).

| ☐ | Item | File · anchor | Notes | Owner | Status |
|---|---|---|---|---|---|
| ☐ | Differential AESround rules | `tools/model_configuration.py:~13-19` | Append to each row: `DIFFERENTIAL_SBOXCOUNT`→`("XORDIFF_A","AESround")`; `DIFFERENTIALPATH_PROB`/`DIFFERENTIAL_PROB`→`("XORDIFF_PR","AESround")`; `TRUNCATEDDIFF_SBOXCOUNT`→`("TRUNCATEDDIFF_A","AESround")`. | | |
| ☐ | Linear AESround rules | `tools/model_configuration.py:~16-23` | Append: `LINEAR_SBOXCOUNT`→`("LINEAR_A","AESround")`; `LINEARPATH_CORR`/`LINEARHULL_CORR`→`("LINEAR_PR","AESround")`; `TRUNCATEDLINEAR_SBOXCOUNT`→`("TRUNCATEDLINEAR_A","AESround")`. | | |
| ☐ | DIFFERENTIAL_PROB → EXISTENCE override | `attacks/differential_cryptanalysis.py` `search_diff_trail`, after `validate_attack_search_request(...)` / before `parse_and_set_configs` | If `goal=="DIFFERENTIAL_PROB"` and `objective_target!="EXISTENCE"`, warn + override to `"EXISTENCE"`. Keep inline (differential-specific). | | |

---

## Package 2 — OR-Tools CPSAT SAT solver — MED (self-contained)

The agent already scaffolds the slot: `SAT_SOLVERS` includes `"ORTools"`, `normalize_sat_solver_name`
maps it, and `solve_sat()` dispatches to a `solve_sat_ortools(...)` **stub** (`return None`).

| ☐ | Item | File · anchor | Notes | Owner | Status |
|---|---|---|---|---|---|
| ☐ | Implement CPSAT routine | `solving/solving.py:~365-366` (stub) | Port upstream `solve_sat_cpsat` body (`cp_model.CpModel`, `new_bool_var` per var, `add_bool_or` per clause, single vs `SearchForAllSolutions` on `solution_number`). **It's a SAT backend (`ortools.sat.python.cp_model`), not MILP; does not need `ortoolslpparser`.** | | |
| ☐ | Lazy loader | `solving/solving.py` (alongside `_load_gurobi`/`_load_pysat`) | Add `_load_cpsat()` via `import_module(...)` in try/except; **do not** top-level `import cp_model`. | | |
| ☐ | Adapt to agent conventions | same routine | Replace `print`→`log(msg, config_solver=...)`; **remove** upstream's internal monitor/timing (parent `solve_sat()` owns it); wrap solve in narrowed `try/except`→`[]`/`None` like `solve_sat_pysat`/`solve_milp_scip`. | | |
| ☐ | **Input bridge (the real work)** | same routine | Upstream `solve_sat_cpsat` expects a list of clause strings; the agent dispatches by CNF `filename`. Convert the DIMACS/CNF file → clause list (+ `variable_map`) before feeding CPSAT. | | |

---

## Package 3 — Two-subset integral distinguisher (biggest feature, multi-file) — HARD

| ☐ | Item | File · anchor | Notes | Owner | Status |
|---|---|---|---|---|---|
| ☐ | **Prereq: copy helper module** | new `tools/sbox_division_trails.py` | Copy verbatim from upstream (64 lines, self-contained, no internal imports). Exposes `two_subset_sbox_truthtable(sbox_table, bit_size)`. Ports 1-3 fail to import without it. | | |
| ☐ | Sbox import + dispatcher | `operators/Sbox.py` import block & `generate_model` (~340-351) | Add `from tools.sbox_division_trails import two_subset_sbox_truthtable`; add `elif self.model_version in [self.__class__.__name__ + "_INTEGRAL_TWOSUBSET"]: return self._generate_model_integral_twosubset(...)` before the final `else` raise. **Do not** add upstream's `tools.model_constraints` import — agent imports those from `tools.model_templates`. | | |
| ☐ | Sbox new method | `operators/Sbox.py` (after dispatcher, before `_generate_model_diff_linear_pr`) | Add `_generate_model_integral_twosubset`. MILP-only + `input_bitsize==output_bitsize` guard. **Rewrite with agent helpers**: `_bitwise_model_vars()`, `_template_io_vars()`, `generate_and_save_constraints(...)` + `instantiate_constraints_template(...)` — do NOT copy upstream's "save-then-reread" idiom. | | |
| ☐ | 11 cipher S-box subclasses | `operators/Sbox.py` "Cipher Sbox" section, between `PRESENT_Sbox` and `KNOT_Sbox` | `RECTANGLE_Sbox` + `LBlock_Sbox0..9` (4×4 tables). Trivial, independent of the integral method. | | |
| ☐ | Input/output model gating (B2) | `tools/model_configuration.py` `gen_round_model_constraint_obj_fun` (~145-148) | Wrap the input/output constraint loops with `if config_model.get("gen_input_model", True):` / `gen_output_model`. **Keep the agent's `constraint.extend(generate_with_profile(...))` body** — only add the `if`. Lets integral search suppress I/O modeling. | | |
| ☐ | **B1: decouple version-config (HARD)** | `tools/model_configuration.py` + `attacks/differential_cryptanalysis.py:~80`, `attacks/linear_cryptanalysis.py:~82`, facade `tools/model_constraints.py:~82-114`, tests | Enabling refactor for integral search. **Decision: keep the agent's superior data-driven `configure_model_version` (`GOAL_MODEL_VERSION_RULES`) — only relocate WHO calls it.** Multi-file; update callers + facade + tests. | | |

---

## Package 4 — Decisions required before porting

| ☐ | Decision | File · anchor | Options |
|---|---|---|---|
| ☐ | **CardEnc failure policy (B4)** | `tools/sat_cardinality.py:~85-90` (`pysat_cardinality_constraints`, `except` block) | Upstream `raise ValueError(...)` (hard-fail) vs agent's current `warnings.warn(...); return []` (warn-and-continue). The agent centralized all 3 upstream sites here — **one edit covers all three**. Pick a policy. |
| ☐ | **Linear ELP metric (A2, HARD)** | `attacks/common.py:~406-414` (`extract_and_format_trails`) | Upstream changed linear aggregate from correlation-sum `2^(-w)` to **Expected Linear Potential** `sum(2^(-2w))` with new label. **This helper is SHARED with differential** — add a parameter (e.g. `square_weight`/`aggregate_exponent`) and pass the ELP variant ONLY from the linear frontend; keep differential's probability-sum untouched. Confirm the team wants ELP. |

---

## Already merged — verify only, do NOT re-port

These upstream changes are **already present** in the agent (confirmed during analysis):

- `assert` → `raise ValueError` across attack validation/boundary helpers.
- SAT fixed input/output bit-indexing fix (`mask[i]` → per-bit offset) — `common.gen_fixed_input_output_constraints`.
- Mask/diff length-overflow validation — `common.normalize_fixed_value_bits`.
- `fix_diff` length check.
- SAT decimal-objective: `computeLAT()` for linear vs `computeDDT()` for differential.
- `visualisations` import removal.
- Sbox integral feature is NOT present anywhere (no double-port risk) — Package 3 is a real port.

---

## Auto-merge files (no manual work — adopt during the git merge)

- **Only-upstream, adopt as-is (19):** new ciphers `lblock/rectangle/simeck/twine/siphash`,
  new attacks `impossible_differential/integral_cryptanalysis/zero_corr_linear`, all `__init__.py`,
  `implementations.py`, `visualisations.py`, `tools/sbox_division_trails.py` (see Package 3).
- **Only-agent (29):** agent's refactored primitives/tools — carry forward unchanged; consider
  upstreaming the general ones back to OCP later.

---

## Verification / regression (run after each package; full pass before sign-off)

- [ ] `python -m compileall agent primitives attacks solving tools operators`
- [ ] `python -m pytest` (light suite) — all green
- [ ] `python -m pytest --run-solver` — solver-backed cryptanalysis (needs python-sat / gurobi / scip)
- [ ] Agent end-to-end: instantiate a cipher, run differential + linear (SAT and MILP), confirm trails + artifacts.
- [ ] **Trail-value parity:** compare a known cipher's optimal differential probability / linear
      correlation before vs after the merge — the ELP change (A2) and AESround rules (Package 1)
      must not silently shift results.
- [ ] OR-Tools CPSAT: run a SAT analysis with `solver="ORTools"` and confirm it solves.
- [ ] Integral distinguisher: run an `*_INTEGRAL_TWOSUBSET` MILP model on a cipher with an S-box.

---

## Local core additions (agent-side, upstream candidates)

Changes made to core files in this fork that upstream does not have yet. Upstream them as
PRs to OCP rather than letting them re-diverge:

- **`primitives/primitives.py` → `ShiftLayer`** (2026-08-16): mirrors `RotationLayer` but uses
  `op.Shift` (non-bijective). Added so custom ciphers defined via the agent can use bit-shifts
  (e.g. SHA-2 sigma functions). Core already had the `Shift` operator but no layer helper.
- **`implementations/implementations.py` → `evaluate(cipher, inputs, cipher_name=None, output_len=None)`**
  (2026-08-16): runs a cipher's generated Python impl on concrete inputs and returns the output
  words - the shared "run a built cipher" primitive. `test_implementation_python` now builds on it,
  and the agent's `verify_cipher_test_vectors` calls it (no duplicated run logic). Enables
  test-vector derivation (e.g. a permutation's known-answer = block cipher run with zero subkeys).
- **`tools/minimize_logic.py` → `minimize_logic` path now uses PyEDA's built-in Espresso**
  (2026-08-17): the `tool_type="minimize_logic"` branch was labelled "via pyeda" but actually shelled
  out to an external `espresso` binary (`subprocess.run(['espresso', ...])`), so generating a NEW
  S-box's diff/linear model (any custom cipher whose S-box isn't in the `files/sbox_modeling/` cache)
  failed with `FileNotFoundError: 'espresso'`. Added `_pyeda_raw_patterns(ttable, variables)` which
  minimizes the ON-set with `pyeda.boolalg.minimization.espresso_tts` and emits cube patterns in the
  exact `0/1/-` column convention the external binary produces, so the downstream
  `espresso_pattern_to_ineq` parser is reused unchanged. Exactness verified exhaustively (a point is
  forbidden by some inequality iff it is in the ON-set) for n=3,4,5. The `minimize_logic_espresso`
  (external binary) branch is untouched. Net effect: new-S-box modeling needs no external tool, only
  the already-required PyEDA. Upstream this as a fix (the branch never did what its name/comment said).

---

## Longer-term (stop re-divergence)

After this port, do not keep dual-maintaining the core:
- Agent should **import** the core / sync via `git merge upstream` on a cadence; never edit core
  files in this fork — upstream general improvements as PRs to OCP.
- Derive shared metadata (cipher catalog, skill schemas, LLM prompts, online docs) from **one
  source** (core code + docstrings) rather than hand-duplicating.
