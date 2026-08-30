# Code Quality TODO

Backlog of known code-quality issues to address as follow-up work. Each entry notes
the symptom, the root cause, and what "done" looks like.

## Simeck: incomplete version coverage in the primitive definition

**Status:** open (follow-up)

**Symptom.** `primitives/simeck.py` defines the Simeck family but does not cover all
official versions:

- `Simeck_block_cipher` / `SIMECK_BLOCKCIPHER` only support `[32, 64]` and `[48, 96]`.
  The `Simeck64/128` version is missing:
  - default round count (`__init__`) only handles `(32,64)→32` and `(48,96)→36`, so
    `[64,128]` falls through to `nbr_rounds=None` and fails;
  - `gen_test_vectors` only ships vectors for `[32,64]` and `[48,96]`.
- The permutation (`SIMECK_PERMUTATION`) supports v32/v48/v64, but this is not symmetric
  with the block cipher, and there is no single source of truth for the supported set.

**Root cause.** Version-specific parameters (round counts, supported `(block, key)`
pairs, test vectors) are hard-coded per branch rather than driven by a table covering the
full family, so adding a version means editing several scattered conditionals and it is
easy to leave one out.

**Why it matters.** This is the same failure class as the corrected `SIMECK64` keyless
test vector and the KNOT-512 constant bug: a version that is declared but never fully
wired up / verified. An unsupported-but-plausible version silently errors (or worse,
was previously mis-verified) instead of being either fully supported or explicitly
rejected.

**Done looks like.**
- Add `Simeck64/128` end-to-end (round count 44, key schedule, KAT-verified against the
  designers' paper vectors), or explicitly reject unsupported versions with a clear error
  instead of falling through to `None`.
- Drive supported versions and their parameters from one table shared by round-count
  defaults and `gen_test_vectors`, so permutation and block-cipher coverage stay in sync.
- Ensure every declared version ships a test vector and is exercised by the KAT sweep
  (`test/unit/test_kat_simeck.py`), so no version is "defined but never verified".
