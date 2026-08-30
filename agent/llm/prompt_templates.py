"""Prompt templates and data catalogs for LLM integration.

This module provides structured data and prompt templates that LLMProvider
implementations can use to construct effective prompts for their chosen model.
"""

import json
from typing import List

from agent.skills.cipher_instantiation import CIPHER_CATALOG
from agent.skills.cipher_examples import few_shot_facts_text


# Valid attack goals
DIFFERENTIAL_GOALS = [
    "DIFFERENTIAL_SBOXCOUNT",
    "DIFFERENTIALPATH_PROB",
    "DIFFERENTIAL_PROB",
    "TRUNCATEDDIFF_SBOXCOUNT",
]

LINEAR_GOALS = [
    "LINEAR_SBOXCOUNT",
    "LINEARPATH_CORR",
    "LINEARHULL_CORR",
    "TRUNCATEDLINEAR_SBOXCOUNT",
]

# JSON schema for LLM response format
INTENT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "needs_clarification": {
            "type": "boolean",
            "description": "True if the request is ambiguous and needs user clarification",
        },
        "clarification_prompt": {
            "type": "string",
            "description": "Question to ask user if needs_clarification is true",
        },
        "requests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "skill": {
                        "type": "string",
                        "enum": [
                            "cipher_instantiation",
                            "code_generation",
                            "visualization",
                            "differential_analysis",
                            "linear_analysis",
                            "integral_analysis",
                            "impossible_differential_analysis",
                            "zero_correlation_analysis",
                            "two_stage_trail_search",
                            "cipher_definition",
                            "cipher_dialogue",
                            "cipher_extraction",
                        ],
                    },
                    "params": {"type": "object"},
                },
                "required": ["skill", "params"],
            },
        },
    },
    "required": ["needs_clarification", "requests"],
}

TEXT_CIPHER_FACTS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "cipher_facts": {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"]},
                "primitive_type": {"type": ["string", "null"], "enum": ["permutation", "blockcipher", None]},
                "state": {"type": "object"},
                "rounds": {"type": "object"},
                "operations": {"type": "array"},
                "tables": {"type": "object"},
                "key_schedule": {"type": "object"},
                "test_vectors": {"type": "array"},
                "ambiguities": {"type": "array"},
                "versions": {"type": ["object", "null"]},
                "default_version": {"type": ["string", "null"]},
                # Data-path representations (MUTUALLY EXCLUSIVE - set at most one). These MUST be
                # top-level keys, NOT nested inside "layout" (a nested cell_layout is the #1
                # extraction mistake). "layout" = bit-sliced (rows/cols); "cell_layout" = cell
                # SPN (cell_bits/nbr_cells); "arx" = add-rotate-xor.
                "layout": {"type": ["object", "null"]},
                "cell_layout": {"type": ["object", "null"]},
                "arx": {"type": ["object", "null"]},
                # Key-schedule declarations (top-level, not inside key_schedule).
                "key_archetype": {"type": ["object", "null"]},
                "pre_whitening": {"type": ["boolean", "null"]},
                "post_whitening": {"type": ["boolean", "null"]},
                # Optional source-evidence map: fact name -> {section/line_start/line_end}.
                "source_spans": {"type": ["object", "null"]},
            },
            "required": ["name", "primitive_type", "state", "rounds", "operations"],
        }
    },
    "required": ["cipher_facts"],
}


def _format_cipher_catalog_for_prompt():
    """Format the cipher catalog into a readable string for prompts."""
    lines = []
    for name, entry in sorted(CIPHER_CATALOG.items()):
        types = list(entry["factories"].keys())
        defaults = entry.get("default_version", {})
        versions = entry.get("valid_versions", {})
        lines.append(f"  - {name}: types={types}, defaults={defaults}")
        if versions:
            for t, v in versions.items():
                lines.append(f"      {t} versions: {v}")
    return "\n".join(lines)


SYSTEM_PROMPT_TEMPLATE = """\
You are an assistant for the OCP (Open Cryptanalysis Platform) automated cryptanalysis tool.
Your task is to parse user requests about cryptographic analysis into structured skill invocations.

## Available Ciphers
{cipher_catalog}

## Available Skills
{skills}

## Attack Goals
Differential: {diff_goals}
Linear: {linear_goals}

## Solver Types
- milp (default): MILP-based solver (Gurobi)
- sat: SAT-based solver (PySAT)

## Instructions
Parse the user's request and return a JSON object matching this schema:
{schema}

Key rules:
1. If the user mentions a known cipher but no cipher is loaded, include a cipher_instantiation request FIRST.
2. For analysis tasks, default to MILP solver and DIFFERENTIALPATH_PROB/LINEARPATH_CORR goals unless specified.
3. If the user wants both differential and linear analysis, include both as separate requests.
4. For code generation, default to Python unless specified.
5. If the request is unclear, set needs_clarification=true with a helpful question.
6. If the user describes a NEW/CUSTOM cipher not in the catalog, use cipher_dialogue with action="start" to begin collecting its specification, then cipher_definition to build it.
7. If the user provides cipher parameters during a dialogue, use cipher_dialogue with action="update" and the structured data.
8. For differential or linear analysis of a built-in cipher: if no cipher is loaded yet AND the user did not state the number of rounds, DO NOT instantiate. Instead set needs_clarification=true and ask how many rounds to analyze (full-round optimal search can be very slow). If a cipher is already loaded, use its rounds.
9. If "Current Session State" contains "panel_settings", the user has pre-set defaults in a control panel. Apply each panel setting to the matching parameter (cipher -> cipher_name, type -> cipher_type, version, rounds, and the analysis params goal, model_type, constraints, objective_target, solver, solution_number, input_diff, output_diff) WHENEVER the user's message does not specify that parameter. This satisfies rule 8: panel rounds count as stated rounds. If the user's message DOES specify a value for a parameter, the message value takes precedence over the panel setting (the latest input wins): use the message value and do NOT ask for confirmation.

## Custom Cipher Definition
When a user describes a new cipher, extract a CipherSpec:
- cipher_type: "permutation" or "blockcipher"
- block_size, word_bitsize, nbr_words, nbr_rounds
- round_structure: list of layers, each with layer_type and params:
  - rotation: {{"direction": "l"/"r", "amount": N, "word_index": N}}
  - shift: {{"direction": "l"/"r", "amount": N, "word_index": N}}
  - xor / and / or: {{"input_indices": [[a,b]], "output_indices": [c]}}  (e.g. w[c] = a OP b)
  - not: {{"input_indices": [[a]], "output_indices": [c]}}  (w[c] = NOT a)
  - n_xor: {{"input_indices": [[a,b,c,...]], "output_indices": [d]}}  (w[d] = a ^ b ^ c ^ ...)
  - andxor: {{"input_indices": [[a,b,c]], "output_indices": [d]}}  (w[d] = (a & b) ^ c, e.g. SIMON)
  - modadd: {{"input_indices": [[a,b]], "output_indices": [c]}}
  - sbox: {{"sbox_name": "name", "index": [[w,...],...]}} - each index GROUP lists the state words
    that form ONE S-box input, so a group holds exactly (S-box input bits / word_bitsize) words.
    A per-cell S-box at cell granularity (word_bitsize == cell bits == S-box width, e.g. Midori/
    PRESENT/GIFT with 4-bit words + 4-bit S-box) is ONE word per group: [[0],[1],[2],...]. A
    bit-sliced n-bit S-box (word_bitsize=1) groups all n bits: [[b0,..,b_{{n-1}}],...]. An m-bit
    S-box over w-bit words groups m/w words. Do NOT reuse MixColumn's per-column grouping (whole
    columns of cells) for the S-box - that is a different, wider grouping.
  - permutation: {{"table": [...]}}
  - matrix: {{"matrix": [[int,...],...], "indices": [[word,...],...], "polynomial": "0xNN"}} - a
    GF(2^n) diffusion matrix (AES MixColumns style). Coefficients are INTEGERS (the GF element's
    integer form: AES 2=x, 3=x+1, 1=1), NEVER symbols like "alpha^3" (alpha^3 -> 8, alpha^3+1 -> 9).
    "indices" groups the words each matrix application acts on (AES: [[0,1,2,3],[4,5,6,7],...]).
    "polynomial" is the reduction polynomial WITHOUT its top term (AES x^8+x^4+x^3+x+1 -> "0x1B";
    GF(2^4) x^4+x+1 -> "0x3").
  - gf2_linear: {{"matrix": [[0/1,...],...], "index_in": [word,...], "index_out": [word,...]}} - a
    BIT-level GF(2) linear map (a word_bitsize x word_bitsize binary matrix) applied to each listed
    word. Use this for a tweakey/key LFSR that mixes the BITS of a word (SKINNY/Deoxys TK2/TK3),
    NOT for a GF(2^n) diffusion matrix over words (that is "matrix"). "index_out" defaults to
    "index_in" (in place).
  - add_round_key: {{"operator": "xor"/"modadd"}}
  - equal: {{"input_indices": [[a]], "output_indices": [c]}} - copy a word unchanged
    (w[c] = w[a]), e.g. to save a word for an ARX feed-forward.
  - aes_round: {{"input_indices": [[16 words],...], "output_indices": [[16 words],...]}} - a
    whole AES round (SubBytes+ShiftRows+MixColumns, NO key) as ONE fused operator over 16-byte
    states. Each group is exactly 16 words (one 128-bit state). For AES-based designs like Rocca;
    any AddRoundKey is a SEPARATE add_round_key/xor layer. Plain AES is still built from
    sbox+matrix+permutation, NOT this.
  - add_identity: {{}} - an explicit do-nothing (identity) layer. Rarely emitted directly;
    prefer "only_rounds"/"except_rounds" below, which insert it automatically.
- ROUND-DEPENDENT layers (a layer active in only SOME rounds, e.g. AES/PRESENT omit the
  MixColumns/permutation in the LAST round, LED adds the round key every 4th round): add
  "only_rounds" or "except_rounds" NEXT TO layer_type/params (not inside params). Both are
  1-based round-number lists; a negative number counts from the end (-1 = last round). In
  the rounds where the layer is inactive an identity layer fills its slot automatically, so
  every round keeps the same layer count. Examples: AES MixColumns -> {{"layer_type":"matrix",
  "params":{{...}}, "except_rounds":[-1]}}; LED add key -> {{"layer_type":"add_round_key",
  "params":{{...}}, "only_rounds":[1,5,9,...]}}. Omit both when the layer runs every round.
- sbox_tables: {{"name": [lookup_table]}}
- FIRST CLASSIFY THE KEY SCHEDULE (as deliberately as the data-path representation) and route
  to ONE mechanism - the round-function alone is never the whole cipher, and a missing/mis-built
  key schedule is why a definition "builds" but returns wrong or all-zero output:
  THE FIRST QUESTION is: does the key STATE change between rounds? If the key register is
  ROTATED / permuted / LFSR-updated each round, the schedule is EVOLVING (mechanism 3) - even if
  the cipher ALSO has whitening. Whitening by itself does NOT mean a static archetype.
  1. STATIC key (the key register is IDENTICAL every round) split into equal shares with an
     alternating round key + whitening + round constants (Midori / LED): you MUST use a
     "key_archetype" (rule 14) - this is REQUIRED for this family, not optional. Put ONLY the
     data path (SubCell/Shuffle/Mix) in operations and let the archetype add the alternating
     keys, the whitening AND the round constants. Do NOT hand-emit key_extract_indices, a
     pre_whitening/post_whitening flag, or add_round_key/add_constant layers here: the manual
     path repeatedly DROPS the round constants (giving a wrong cipher) and its whitening + key
     extraction overflow the state - both are exactly why hand-built Midori keeps failing the
     KAT. Use the archetype ONLY when the key does NOT evolve; if the key is rotated/updated each
     round it is mechanism 3, NOT this (static_alternating on an evolving-key cipher like FUTURE
     crashes the KAT).
  2. STATIC key selecting different words each round with NO shares/whitening/round-constants
     machinery (a plainer alternation than Midori): key_extract_indices as a LIST OF LISTS
     (rule 13). If the cipher has whitening OR round constants, it is family (1) - use the
     archetype, not this.
  3. EVOLVING key schedule - the key state is UPDATED every round by rotation / word permutation /
     LFSR / round constant (SPECK / PRESENT / AES / FUTURE): give key_schedule layers +
     key_extract_indices (below). FUTURE rotates its whole key register each round AND has
     pre-whitening: that is mechanism 3 (key_schedule rotation layers over the 1-bit key words) +
     pre_whitening = true, NOT a static_alternating archetype.
  4. CROSS-ROUND subkey (Simon reaches back to an earlier key state): {{"from": ks_round,
     "words": [...]}} entries (below).
  5. TWEAKEY (SKINNY / Deoxys): concatenate the tweak into the key (below).
  INDEPENDENTLY of 1-5, always check three things the extractions keep dropping: (a) a key added
  BEFORE round 1 or AFTER the last round is WHITENING -> set pre_whitening / post_whitening (do
  NOT fold it into a normal round); (b) per-round CONSTANTS added to the state are an add_constant
  layer (or the archetype's round_constants) - a dropped constant yields wrong/all-zero output,
  so never omit them silently (if the table is missing, list it in ambiguities); (c) under
  cell_layout the state is bit-expanded, so the KEY is BIT-LEVEL too: key_word_bitsize = 1 and
  key_nbr_words = key_size (a key_word_bitsize equal to the cell size is the #1 key mistake there).
- For block ciphers: key_size, key_nbr_words, key_schedule, key_extract_indices. An
  EVOLVING key schedule (SPECK/PRESENT/AES/FUTURE) is a list of FIXED layers applied
  every round to the key state - typically rotation + add_constant (per-round
  constant_table) + a word permutation - with key_extract_indices pulling the subkey.
  The round-dependence must come from the constant_table and word permutation, NOT from
  changing a layer's params per round (unsupported). If the schedule alternates between
  key words (FUTURE's K0/K1), let the word permutation rotate them into a fixed slot the
  fixed layers act on. Do NOT emit a lone rotation with round-varying amount/word_index.
  key_extract_indices is any list of key-state word indices (NOT required to be contiguous;
  GIFT/SKINNY pull an interleaved subset) - the subkey is those words of the CURRENT round's
  key state, so a fixed index list plus an evolving key schedule already gives per-round subkeys.
  For a key that does NOT evolve but SELECTS different words each round (Midori/LED alternate
  K0 and K1), make key_extract_indices a LIST OF LISTS: round i uses phase (i-1) % period.
  E.g. two 64-bit halves as 16+16 cells -> [[0..15],[16..31]] extracts K0,K1,K0,K1,... All
  phases must have the same length. With no key evolution, omit key_schedule (the key is
  propagated unchanged automatically).
  CROSS-ROUND subkey (the subkey is NOT the current key state - Simon reaches back to an
  earlier key-schedule state): make each entry {{"from": <ks_round>, "words": [indices]}} to
  read KS.vars[<ks_round>] instead of the current round. Give ONE entry per cipher round (a
  full list, length nbr_rounds), computing <ks_round> from the paper's rule (Simon: word 0 of
  vars[i-m+1] once i > m, m = key words). If the key schedule runs fewer rounds than the
  cipher (Simon: nbr_rounds - m + 1), set "key_nbr_rounds" to that count.
  STRUCTURE FROM CODE: when such a plan (or any layer's index table / permutation table) is
  LONG and follows a RULE, don't hand-list dozens of entries - set the value to
  {{"code": "<program>", "count": nbr_rounds}} instead. The program runs in the sandbox (same
  rules as round-constant code: int/bit-ops, for/range, if, list AND dict literals, append)
  and must set `result` to the concrete list (e.g. the whole key_extract_indices list of
  {{"from":..,"words":..}} entries, or an sbox index [[...],...]). `count` and the cipher dims
  (nbr_rounds/nbr_words/word_bitsize/key_nbr_words/...) are in scope. The KAT verifies it, so
  prefer a short program over a long literal whenever the structure is regular.
- WHITENING: a round key added OUTSIDE the round function - before round 1 (FUTURE's WK) or
  after the last round (PRESENT's final subkey). Set "pre_whitening": true and/or
  "post_whitening": true and keep nbr_rounds at the paper's real count; the build models each
  as one extra round in which only the add_round_key layer runs. Do NOT hand-write that extra
  round or inflate nbr_rounds yourself.
- For a TWEAKABLE cipher (SKINNY/Deoxys tweakey framework): OCP has no separate tweak input -
  concatenate the tweak with the key so key_size = key_bits + tweak_bits and treat the whole
  thing as the key state (branches TK1..TKz laid out consecutively). PREFERRED: declare the whole
  tweakey schedule with the "tweakey_lfsr" key_archetype instead of hand-writing it:
  {{"type": "tweakey_lfsr", "branches": z, "cells_per_branch": nbr_words, "subkey_cells": K,
    "permutation": [per-branch cell permutation], "lfsr_matrices": [null, mat_TK2, mat_TK3]}}
  - branches*cells_per_branch MUST equal key_nbr_words. "permutation" defaults to the SKINNY P_T
    [9,15,8,13,10,14,12,11,0,1,2,3,4,5,6,7]; give one lfsr_matrices entry per branch (null for
    TK1's no-LFSR branch, a word_bitsize x word_bitsize GF(2) bit matrix for TK2/TK3). The
    archetype generates the evolving key_schedule AND the per-round subkey = XOR of each branch's
    top subkey_cells cells; do NOT also set key_schedule or key_extract_indices. Because SKINNY
    adds the subkey MID-round, round_structure MUST still contain its own add_round_key at the
    correct position (after SubCell and the round constant, before ShiftRows) - the archetype does
    NOT emit it. FALLBACK (non-SKINNY tweakey shapes): hand-write key_schedule (a branch word
    permutation + per-branch "gf2_linear" LFSR) with key_extract_indices {{"xor": [branch0_words,
    branch1_words, ...]}}.
- For a PARAMETERIZED FAMILY (several versions like 256/384/512, or SPECK's word sizes): add "versions": {{"256": {{scalar overrides such as block_size/word_bitsize/nbr_rounds plus a "params" dict}}, ...}} and "default_version", and reference per-version values in round params as "$name" (e.g. rotation "amount": "$rot"). One version is built at a time.
- FIRST CLASSIFY the cipher and pick EXACTLY ONE data-path representation - they are mutually
  exclusive and setting two is rejected: ARX (add-rotate-xor, ChaCha/Salsa/Forro) -> "arx";
  bit-sliced SPN (S-box down each column of a bit grid, KNOT/RECTANGLE) -> "layout"; cell-
  oriented SPN (n-bit-cell S-box + GF(2^n) MixColumn, FUTURE/Midori) -> "cell_layout"; a plain
  word-based cipher (AES word-level, SPECK, Simon) -> NONE of them (use state + explicit
  layers). Do NOT hand a spec with several candidate representations and let the builder guess.
- THE ROUND RECIPE (`operations`) IS MANDATORY. It is the ordered list of steps in ONE round.
  Extracting the S-box / matrix / permutation TABLES is NOT enough - you MUST also emit the
  OPERATIONS that apply them. An empty `operations` for a cipher that has a round function is an
  EXTRACTION FAILURE, not an acceptable "unknown": the round structure is always defined in the
  paper's round-function section. Read that section and map EACH named step to exactly one entry:
  - cell/word SPN (AES / Midori / PRINCE / GIFT / SKINNY / FUTURE): SubBytes/SubCell -> subcell_sbox
    (cell_layout) or sbox; ShiftRows/ShuffleCell -> cell_shiftrow or permutation; MixColumns ->
    mixcolumn or matrix; AddRoundKey -> add_round_key; round constant -> add_constant. Usually
    3-4 layers per round; if the paper names N steps per round, emit N entries in that order.
  - ARX (LEA / SPECK / ChaCha / Salsa): modular additions -> modadd, rotations -> rotation, XORs
    -> xor, over the state WORDS. EVERY word index MUST be < nbr_words - an index >= nbr_words
    means you mis-read which words the operation combines (re-read the round; do not invent a
    word). LEA-128 has 4 words indexed 0..3.
  - Feistel (SIMON / DES / TWINE): the F-function (and / andxor / rotation / sbox) then xor into
    the other branch; updating only part of the state each round is normal and correct.
  Never leave `operations` empty and expect the tables alone to define the cipher.
- THIS APPLIES TO VERSIONED FAMILIES TOO. Even when you build a `versions` map, `operations`
  MUST still contain the ONE shared round skeleton, referencing any per-version value as a
  "$name" placeholder resolved from each version's params (e.g. subcell_sbox {{"sbox_name":
  "$sbox"}}, cell_shiftrow {{"table": "$shuffle"}}, mixcolumn {{"matrix": "$matrix", ...}}).
  Putting the S-box name / shuffle table / matrix ONLY in the version params while leaving
  `operations` empty is the SAME extraction failure - the round function must appear as
  operations, with versions supplying only the values that differ between members.
- For a BIT-SLICED cipher (KNOT/RECTANGLE/ASCON class: an S-box down each column of a rows x cols bit grid, diffusion by per-row rotation, optional LFSR round constants): DO NOT hand-expand the S-box index groups or the bit-permutation table. Instead give "layout": {{"rows": R, "cols": C}} (omit block_size/word_bitsize/nbr_words; they are derived as R*C bits) and high-level layers: subcolumn_sbox {{"sbox_name": "S"}}; shift_rows {{"offsets": [o0,..,o(R-1)], "direction": "l"/"r"}}; add_round_constant {{"d": D, ...}} whose per-round D-bit constant (XORed into the first row) comes from EITHER "constants": [c0, c1, ...] (an explicit sequence copied from the paper or reference implementation - MOST RELIABLE, and it sidesteps LFSR-convention mistakes) OR "lfsr": {{"width": W, "taps": [..], "init": N, "mode": "fibonacci"|"galois", "direction": "left"|"right"}} (defaults fibonacci/left). Prefer "constants" whenever the paper lists a round-constant table. OCP expands these into the concrete word_bitsize=1 layers.
- A CELL-ORIENTED SPN (n-bit cells + cell S-box + cell permutation + MixColumn: Midori, SKINNY,
  AES, GIFT) is by DEFAULT a WORD-LEVEL cipher: set word_bitsize = n, nbr_words = number of cells,
  and use WORD layers - "sbox", "permutation" (the ShiftRows/ShuffleCell cell permutation), and
  "matrix" (the MixColumn, with its GF "polynomial"; a binary 0/1 matrix uses "0x0") - plus a
  key_archetype (Midori/LED) or explicit key layers. The "matrix" layer already does GF(2^n), so a
  GF MixColumn does NOT by itself require bit-level modeling. Reach for cell_layout ONLY in the
  narrow FUTURE case below. (Word-level Midori/SKINNY/AES is simpler and is what verifies.)
- For a CELL-SLICED cipher with a GF(2^n) diffusion MATRIX over cells (FUTURE class: an n-bit-cell S-box AND a GF(2^n) MixColumn, but a key schedule that rotates a whole key register across cell boundaries, which forces bit-level modeling): give "cell_layout": {{"cell_bits": N, "nbr_cells": M}} (omit block_size/word_bitsize/nbr_words; state is N*M bits) and high-level CELL layers, DO NOT hand-write the bit tables: subcell_sbox {{"sbox_name": "S"}} (the cell S-box on each cell); mixcolumn {{"matrix": [[int GF coeffs]], "polynomial": "0xNN" (reduction poly minus top term, GF(2^4) x^4+x+1 -> "0x3"), "columns": [[cell,...],...]}} (a GF(2^cell_bits) matrix over each column's cells); cell_shiftrow {{"table": [cell permutation]}}. These auto-expand to word_bitsize=1 layers (bit-level S-box groups, the GF(2) MixColumn bit-matrix, the ShiftRow bit-permutation). Put except_rounds:[-1] on mixcolumn if the last round omits it (AES/FUTURE). The KEY schedule stays bit-level (key_word_bitsize=1, key_nbr_words=key_size) and is EVOLVING, NOT a static_alternating archetype. Express each whole-register (or half-register) BIT rotation DECLARATIVELY - do NOT hand-write the 128-entry permutation table: key_schedule layer {{"layer_type": "bit_rotation", "params": {{"amount": A, "direction": "l"|"r", "start": S (default 0), "width": W (default the whole key register)}}}} rotates bits [S, S+W) by A and leaves the rest. FUTURE-64's schedule is exactly two of these: {{"amount": 64}} (swap the two 64-bit halves) then {{"amount": 5, "width": 64}} (rotate the low half by 5). Give a flat key_extract_indices selecting the round-key bits (FUTURE extracts the low 64: [0,1,...,63]) and pre_whitening/post_whitening for the whitening key. FUTURE's key is NOT Midori's fixed K0/K1 - it rotates every round, so do NOT use key_archetype (that models a static key and crashes the KAT).

Prefer routing a new-cipher description to the dedicated definition flow
(cipher_dialogue for a chat description, cipher_extraction for an uploaded file),
which supplies worked format examples and a reviewable draft. Do not inline a full
CipherSpec here unless the user already gave every field.

## File Import
When the user names a file to import a cipher from, use the cipher_extraction skill:
- cipher_extraction: {{"file_path": "spec.md", "focus": "optional section", "pages": "1-5", "auto_build": false}}
- file_path may be an absolute path, OR just a filename the user placed in the files/ folder (it is resolved there automatically). So "extract the cipher from spec.md" works if spec.md is in files/.
- Supports .tex, .md, .txt, .pdf, .png, .jpg. Prefer .tex / .md / pasted text; PDF and image extraction is lossy.
- Do not set auto_build=true.

## Current Session State
(This is the only part that changes between turns; everything above is static so
providers with automatic prefix caching can reuse it.)
{session_context}

Return ONLY valid JSON, no extra text.
"""


def build_parse_prompt(
    user_message: str,
    available_skills: List[dict],
    session_context: dict,
) -> str:
    """Build the system prompt for parsing user requests."""
    return SYSTEM_PROMPT_TEMPLATE.format(
        cipher_catalog=_format_cipher_catalog_for_prompt(),
        skills=json.dumps(available_skills, indent=2),
        diff_goals=DIFFERENTIAL_GOALS,
        linear_goals=LINEAR_GOALS,
        session_context=json.dumps(session_context, separators=(",", ":")),
        schema=json.dumps(INTENT_RESPONSE_SCHEMA, separators=(",", ":")),
    )


TEXT_CIPHER_FACTS_PROMPT_TEMPLATE = """\
You are extracting a cryptographic primitive specification for OCP.

OUTPUT CONTRACT (critical): return EXACTLY ONE valid JSON object and NOTHING else - no prose,
no explanation, no reasoning, no markdown, before/after/or BETWEEN fields. NEVER break out of the
JSON to think or justify a choice in words: that runs the output past its length limit and the
whole response is lost (this is the #1 extraction failure). If a value is uncertain or needs a
derivation you cannot do inline (e.g. an S-box defined by a figure, an unclear key rotation), put
a SHORT string in the "ambiguities" array and MOVE ON - do not pause to reason. Keep going until
the JSON object is closed. For a hard key schedule, prefer the compact declarative forms (a
key_schedule "bit_rotation" layer, a key_archetype) over a long hand-written table.

{classification}Return ONLY valid JSON matching this schema:
{schema}

Rules:
1. Extract facts from the provided text. Do not invent missing values.
2. Use primitive_type "permutation" or "blockcipher" only when supported by the text.
3. Put state size facts in state: block_size, word_bitsize, nbr_words, and any layout notes.
4. Put round count facts in rounds: nbr_rounds and any naming notes.
5. Put each round operation in operations with type and params. Supported types:
   xor, and, or, not, n_xor, andxor, rotation, shift, modadd, sbox, permutation,
   matrix, add_round_key, add_constant. Use andxor for out = (in0 & in1) ^ in2
   (e.g. SIMON), and n_xor for XOR of more than two inputs. For "matrix" (a GF(2^n)
   diffusion matrix, AES MixColumns style), params are {{"matrix": [[int,...],...],
   "indices": [[word,...],...], "polynomial": "0xNN"}}: INTEGER coefficients (the GF
   element's integer form, e.g. AES 2/3/1; alpha^3 -> 8, alpha^3+1 -> 9), NEVER
   symbols; "indices" groups the words each application acts on; "polynomial" is the
   reduction polynomial minus its top term (AES -> "0x1B", GF(2^4) x^4+x+1 -> "0x3").
6. Put S-box, permutation, matrix, constants, and test vectors under tables or
   test_vectors. Preserve table order exactly. Extract any known-answer test
   vectors (they let us verify the definition). Format each as
   {{"input": "<hex>", "output": "<hex>"}} for a permutation, or
   {{"plaintext": "<hex>", "key": "<hex>", "output": "<hex>"}} for a block cipher.
   COPY THE PAPER'S HEX STRING VERBATIM as a JSON string - do NOT split it into
   words yourself, do NOT convert to decimal, do NOT pad or truncate. A deterministic
   parser splits the hex into words by word_bitsize (MSB-first), so you cannot make a
   miscount: just transcribe exactly the hex the paper prints (e.g. "3c9cceda2bbd449a").
   The hex's bit length must equal the block size (plaintext/output) or key size (key).
   Keep each cipher variant's vectors SEPARATE - never concatenate a different variant's
   (e.g. Midori128's) hex onto this one. If (and only if) the paper gives a vector already
   as per-word integers, you may instead use a list [word0, word1, ...] of DECIMAL values
   each fitting word_bitsize bits.
7. Put uncertain or missing details in ambiguities instead of guessing. NEVER invent these
   high-risk values when the paper does not state them explicitly - a wrong guess yields a
   cipher that may still "build" but is WRONG, and the KAT cannot save you if the test vectors
   are themselves guessed: the MixColumn/GF reduction POLYNOMIAL, the bit/word ENDIANNESS or
   cell ordering, the ROUND CONSTANTS (copy the paper's table or its generating rule; do not
   fabricate), and the TEST VECTORS (only use known-answer pairs printed in the paper or its
   reference code). If any of these is not in the source, list it in ambiguities as unknown.
   NEVER emit a PLACEHOLDER matrix/permutation - especially not an IDENTITY matrix for a
   diffusion (MixColumn/M) layer, which silently does nothing and makes the cipher wrong while
   still "building". If the real diffusion matrix or permutation is not clearly in the source,
   put it in ambiguities; do not fill it with identity or zeros.
8. Output ONLY the structured facts. Do NOT copy source sentences, paragraphs, or
   quoted spans of the paper into the JSON - long quotes burn the output budget and
   can truncate the response before operations/versions/layout are emitted. Prefer
   emitting the core fields (operations, tables, versions, layout) first.
9. If the cipher is a PARAMETERIZED FAMILY (several members like 256/384/512, or
   different word sizes), set "versions" to a map version -> {{scalar overrides
   such as block_size/word_bitsize/nbr_words/nbr_rounds (and key_* for a block
   cipher), plus a "params" object of the per-version numbers}} and set
   "default_version". In operations, reference per-version numbers as "$name"
   (e.g. a rotation "amount": "$c1"). Leave the top-level state/rounds empty when
   using versions. Keep the shared S-box tables at the top level. EACH version MUST
   set "nbr_rounds" (the round count the built primitive actually uses); a scalar
   override may reference a param, e.g. "nbr_rounds": "$nr0". When a spec lists
   several phase counts (e.g. KNOT's nr/nr0/nrf), nbr_rounds is the PERMUTATION's own
   round count (nr0), not the AEAD/hash phase counts.
   MODE vs PERMUTATION: when the paper describes an AEAD / hash / MAC MODE built on an
   internal PERMUTATION, extract the underlying PERMUTATION and version it ONLY by the
   permutation's state/block width b - exactly one version per distinct width, named
   "<NAME>-<b>" (e.g. KNOT-256, KNOT-384, KNOT-512). Do NOT create a version per mode
   (AEAD/Hash) or per key/rate/tag length; those belong to the mode, not the
   permutation. Collapse members that share the same width into a single version, and
   use that width's permutation round count (e.g. nr0) for nbr_rounds. Round-constant
   width d / LFSR do not affect analysis, so if same-width members differ there, keep
   one (prefer the one covering the most rounds).
10. If the cipher is BIT-SLICED (KNOT/RECTANGLE/ASCON class: an S-box down each
   column of a rows x cols bit grid, diffusion by per-row rotation, optional LFSR
   round constants), set "layout": {{"rows": R, "cols": C}} (leave state empty; the
   size is R*C bits) and use these high-level operations instead of a hand-expanded
   S-box index or bit-permutation table: subcolumn_sbox {{"sbox_name": "S"}};
   shift_rows {{"offsets": [o0,...], "direction": "l"/"r"}}; add_round_constant
   {{"d": D, ...}} whose per-round constant comes from EITHER "constants": [c0,...]
   (an explicit table from the paper/reference - most reliable) OR "lfsr": {{"width":
   W, "taps": [..], "init": N, "mode": "fibonacci"|"galois", "direction":
   "left"|"right"}} (defaults fibonacci/left). Prefer "constants" when the paper
   lists them; otherwise give the LFSR recurrence. Keep S-box tables at the top level. If it is ALSO a parameterized family, layout dimensions and op
   params may be "$name" placeholders (a lone "$name" may resolve to a list, e.g.
   "taps": "$taps"), and a dimension may be arithmetic on a param, e.g.
   "cols": "$b/4"; per-version numbers (b, offsets, d, taps, nr0, ...) go in each
   version's "params", and remember rule 9's per-version "nbr_rounds". A bit-sliced
   version needs ONLY "nbr_rounds" and "params" - do NOT add block_size/word_bitsize/
   nbr_words to versions; the state size is derived from rows x cols at expansion.
11. If the cipher has an n-bit-CELL S-box AND a GF(2^n) diffusion MATRIX over cells (AES-in-
   bits / FUTURE class), and its key schedule rotates a whole key register by an amount that
   is NOT a multiple of the cell size (crossing cell boundaries), the whole cipher must be
   bit-sliced. Set "cell_layout": {{"cell_bits": N, "nbr_cells": M}} (leave state empty; size
   = N*M bits) and use HIGH-LEVEL cell operations - do NOT hand-expand bit tables:
   subcell_sbox {{"sbox_name": "S"}}; mixcolumn {{"matrix": [[int GF coeffs]], "polynomial":
   "0xNN" (reduction poly minus top term), "columns": [[cell,...],...]}}; cell_shiftrow
   {{"table": [cell permutation]}}. Put "except_rounds": [-1] on mixcolumn when the last round
   omits it. CRITICAL: with cell_layout use ONLY these cell operations for the data path.
   NEVER hand-write bit-level "sbox"/"matrix"/"permutation" with cell_layout - a bit-level
   16x16 MixColumn matrix with 4-cell column groups (mixing bit and cell granularity) is the
   #1 mistake and fails at build ("input vector does not match matrix size"). The KEY is bit
   level (1-bit words); for a static-key family you may still use a key_archetype (rule 14) -
   it composes with cell_layout and emits the bit-level key add + constants for you.
12. WHITENING - a key added OUTSIDE the round function, before round 1 (FUTURE's WK) or after
   the last round (PRESENT's final subkey): set "pre_whitening": true and/or "post_whitening":
   true and keep nbr_rounds at the paper's count. Do NOT invent an extra round for it.
13. A KEY that SELECTS different words each round WITHOUT evolving (Midori/LED alternate two
   halves K0,K1): make key_schedule.key_extract_indices a LIST OF LISTS [[K0 words],[K1
   words]] - round i uses phase (i-1) % period - and omit key_schedule.round_structure (the
   key is kept unchanged). A COMBINED whitening key like Midori's WK=K0^K1 is just two
   AddRoundKeys (add K0 then K1), so it needs no special field.
14. PREFERRED for the Midori/LED static-key family (a fixed key split into equal shares, an
   alternating round key, whitening, and pi-derived round constants): instead of hand-writing
   the extraction table and the key-add/constant layers, DECLARE a "key_archetype" and put ONLY
   the data path (SubCell/Shuffle/Mix, NO add_round_key, NO add_constant) in "operations":
     "key_archetype": {{"type": "static_alternating", "shares": <N>, "whitening": "<W>",
                       "round_constants": {{"source": "pi_hex", "count": <nbr_rounds-1>}}}}
   - shares: how many equal parts the key is split into (Midori64 = 2 for K0,K1; a single
     fixed key = 1). shares must divide key_nbr_words.
   - whitening: "xor_shares" (WK = XOR of the two shares, Midori64), "whole_key" (WK = the key,
     Midori128), or "none".
   - key_period: N to add the round key only ONCE per N-round step (rounds 1, 1+N, ...) plus a
     trailing key-only round, with the share alternating per key-add EVENT - this is LED (N=4,
     shares=1 for LED-64, shares=2 alternating K0/K1 for LED-128). Omit (or 1) to add a key
     every round (Midori). With key_period the round constants usually differ from Midori's
     pi_hex, so give LED's own via round_constants "table"/"code", or put an add_constant layer
     directly in operations. Reminder: an add_constant "constant_mask" marks a word inactive
     with null/None (NOT 0); each constant_table row has one value per active (non-null) word.
   - round_constants: {{"source": "pi_hex", "count": K}} generates Midori's 4x4 pi-matrix
     constants (added to each cell's LSB); use {{"source": "table", "table": [[...],...]}} for an
     explicit per-round cell table; use {{"source": "code", "count": K, "code": "..."}} to DERIVE
     them - a small Python program that sets `result` to the list of K cell-rows, run in a
     sandbox (int/bit-ops, for/range, list comprehensions + append only; no imports/attributes).
     Prefer "code" over copying a long table when the constants follow a rule; the KAT verifies it.
     Omit round_constants if there are none.
   The expander produces the pre-whitening round, the alternating round keys, the pi constants,
   the final SubCell-only round and the post-whitening round for you. Set nbr_rounds to the
   paper's round count R; keep key_size/key_word_bitsize/key_nbr_words. This is far more
   reliable than emitting the full per-round table by hand - prefer it whenever it fits.
   The archetype's "whitening" ALREADY adds the whitening rounds, so do NOT also set
   pre_whitening/post_whitening (that applies whitening twice and breaks the build).
15. ARX PERMUTATION family (ChaCha, Salsa, Forro, BLAKE-like: an add-rotate-xor (sub)round
   applied to rotating groups of 32-bit words): DECLARE an "arx" block and leave "operations"
   EMPTY - do NOT hand-write 12*nbr_rounds index layers:
     "arx": {{"word_bitsize": 32, "nbr_words": 16, "temp_per_lane": 0,
             "selections": [ [[0,4,8,12],[1,5,9,13],[2,6,10,14],[3,7,11,15]],   # phase 0 (columns)
                             [[0,5,10,15],[1,6,11,12],[2,7,8,13],[3,4,9,14]] ], # phase 1 (diagonals)
             "ops": [ {{"op":"modadd","in":[0,1],"out":0}}, {{"op":"xor","in":[0,3],"out":3}},
                      {{"op":"rotl","in":[3],"out":3,"amount":16}}, ... ],       # ONE (sub)round
             "feedforward": false}}
   - selections is a PERIODIC list of selection-sets; round r uses selections[(r-1) % period]
     (ChaCha/Salsa alternate 2 sets, Forro cycles 8). Each set lists equal-length "lane" tuples;
     every op runs on all lanes at once. op positions index INTO the lane tuple.
   - ops give ONE (sub)round: op in {{modadd, xor, and, or, n_xor, rotl, rotr}}; rotl/rotr need
     "amount". Use {{"temp": k}} as a per-lane scratch word (Salsa's b ^= rot(a+d, r) needs one).
   - feedforward: true for the keystream/hash variant (save the input state, add it back at the
     end); set nbr_rounds = (sub)rounds + 1. Give word_bitsize/nbr_words inside "arx", not state.
16. BIT-LINEAR DIFFUSION layer (ASCON's Sigma, SPEEDY's MixColumn, any "x ^= rot(x,a) ^ rot(x,b)
    ..." circulant rotate-and-XOR): use ONE "linear_diffusion" operation instead of hand-writing
    hundreds of n_xor index tuples:
      {{"type": "linear_diffusion", "params": {{"shape": [n_groups, group_size],
          "axis": "within" | "across", "taps": [...], "direction": "r" | "l"}}}}
    - The state is viewed as n_groups rows of group_size bits (row-major: bit index = g*group_size
      + e). Each output bit = XOR of the same bit and its rotations by each tap.
    - axis "within": rotate the bit position inside its group (over group_size) - ASCON Sigma_i
      over each 64-bit word. axis "across": rotate the group index (over n_groups) - SPEEDY's
      MixColumn mixing across the 32 rows at a fixed bit.
    - taps: a flat list [a, b, ...] applies to every group; a list-of-lists [[..],[..],...] gives
      per-group taps (ASCON's five words each have their own two rotation amounts).
    - direction "r" = rotate toward higher index (the paper's >>>), "l" = the other way.

Before returning, SELF-CHECK the facts against the hard constraints the build enforces, and
fix them now (this avoids a later repair round):
- Every rotation/shift "amount" is a positive integer < word_bitsize. An amount >=
  word_bitsize means the rotation is over a wider unit than one word (e.g. a whole 64-bit
  key half); it is NOT a word rotation - record it in ambiguities with a note instead of
  emitting an illegal word rotation.
- For add_round_key, the "mask" (which state words receive the subkey) must have exactly as
  many 1s as the subkey has words. If unsure of the subkey size, OMIT the mask (a matching
  default is applied) rather than guessing a length.
- Round operations are in the SAME order the paper applies them (e.g. SubCell, MixColumn,
  ShiftRow, AddRoundKey). If the LAST round omits a layer (e.g. no MixColumn), NOTE that in
  ambiguities rather than duplicating the whole round list.
- Every operation includes all its params (rotation/shift need word_index; matrix needs
  indices; sbox needs sbox_name; add_constant needs the constant table).
- A key added BEFORE round 1 or AFTER the last round is a whitening key - note it; do not
  invent an extra round for it.
- Test-vector words are DECIMAL, one per word, each < 2**word_bitsize.

Worked examples (format reference):
{facts_examples}

Input metadata:
- source_type: {source_type}
- format_hint: {format_hint}
- language_hint: {language_hint}
- source_name: {source_name}

Cipher text:
{normalized_text}
"""


# --- Stage 1: architecture classification -----------------------------------------------
# A first, cheap LLM pass decides the cipher's STRUCTURAL archetype so the second (formalize)
# pass can be told which representation to build - instead of the model defaulting to the
# familiar "repeated SPN" template for every cipher (the PRINCE failure). Each entry is the
# one-line directive injected into the formalize prompt for that archetype.
CIPHER_ARCHETYPES = {
    "standard_spn": "A word-level SPN: give state + explicit sbox / permutation / matrix / "
                    "add_round_key layers. No special representation field.",
    "bitsliced_spn": "A bit-sliced SPN (S-box down each column of a rows x cols bit grid, "
                     "KNOT/RECTANGLE/GIFT): use \"layout\": {\"rows\":R,\"cols\":C} with "
                     "subcolumn_sbox / shift_rows / add_round_constant. Do NOT hand-expand bit tables.",
    "cell_sliced_spn": "A cell-oriented SPN: n-bit cells, an n-bit S-box, a cell permutation "
                       "(ShiftRows/ShuffleCell) and a MixColumn/matrix over cells (Midori/SKINNY/"
                       "AES/GIFT/FUTURE/LED). MODEL AT WORD LEVEL BY DEFAULT: word_bitsize = n "
                       "(the cell size), nbr_words = number of cells, and use WORD layers - sbox, "
                       "permutation (the cell permutation), matrix (the MixColumn, carrying its "
                       "GF(2^n) \"polynomial\"; a binary 0/1 matrix uses polynomial \"0x0\"). Keep "
                       "key_word_bitsize = n, and for a static split-key + whitening + round "
                       "constants (Midori/LED) add a key_archetype. Use the BIT-LEVEL cell_layout "
                       "(subcell_sbox / mixcolumn / cell_shiftrow, key_word_bitsize = 1) ONLY when "
                       "the KEY SCHEDULE rotates a whole key register ACROSS cell boundaries "
                       "(FUTURE) - that alone forces bit-level modeling; Midori/SKINNY/AES do NOT.",
    "arx": "An ARX cipher (LEA/SPECK/ChaCha/Salsa): modadd + rotation + xor over the state WORDS, "
           "every word index < nbr_words. For a permutation family use the \"arx\" block.",
    "feistel": "A Feistel cipher (SIMON/DES/TWINE): an F-function (and/andxor/rotation/sbox) then "
               "xor into the OTHER branch - updating only part of the state each round is correct.",
    "gfn": "A generalized Feistel network (several branches, e.g. TWINE/CLEFIA): each round applies "
           "F to some branches, xors into others, then a branch permutation. Partial-state updates.",
    "reflection_spn": "A REFLECTION / alpha-reflection cipher (PRINCE class): pre-whitening, a run "
                      "of FORWARD rounds, a MIDDLE involution, a run of BACKWARD rounds (inverse "
                      "S-box / inverse MixColumn), post-whitening - it is NOT a uniform repeated "
                      "round. OCP cannot yet express this as one repeated round_structure: extract "
                      "the facts faithfully (forward layers, middle layers, backward layers, both "
                      "whitening keys, the round constants) and RECORD IN ambiguities that the "
                      "structure is a reflection cipher needing an asymmetric layout. Do NOT flatten "
                      "it into N identical rounds - that silently produces the wrong cipher.",
    "unknown": "Could not be classified confidently: apply the general rules and put every "
               "uncertain structural decision in ambiguities rather than guessing.",
}

CIPHER_CLASSIFICATION_PROMPT_TEMPLATE = """\
You are classifying the STRUCTURE of a cryptographic primitive for OCP, as a first pass before
a detailed extraction. Read the text and decide which ONE structural archetype it is. Do NOT
extract tables or operations yet - only classify and read the top-level sizes.

Return ONLY valid JSON:
{{"archetype": "<one of: standard_spn, bitsliced_spn, cell_sliced_spn, arx, feistel, gfn,
 reflection_spn, unknown>", "cipher_type": "blockcipher"|"permutation", "confidence": 0.0-1.0,
 "reason": "<one sentence: the structural evidence>", "name": "<cipher name or null>",
 "block_size": <int or null>, "key_size": <int or null>, "nbr_rounds": <int or null>,
 "is_versioned": true|false}}

How to tell the archetypes apart:
- reflection_spn: the round sequence is NOT uniform - forward rounds, a distinct MIDDLE layer,
  then backward/inverse rounds (inverse S-box or inverse MixColumn), usually with an alpha
  constant and two whitening keys (PRINCE, MANTIS, QARMA). If you see "reflection", "involution",
  "middle round", or forward-then-inverse structure, it is this - NOT standard_spn.
- cell_sliced_spn: an n-bit-cell S-box PLUS a GF(2^n) MixColumn/matrix over cells (Midori, FUTURE,
  LED, SKINNY, AES viewed at cell level).
- bitsliced_spn: the S-box runs down each column of a bit grid, diffusion is per-row bit rotation
  (KNOT, RECTANGLE, GIFT, ASCON).
- arx: no S-box; confusion comes from modular addition + rotation + xor (LEA, SPECK, ChaCha, Salsa).
- feistel / gfn: the state splits into halves/branches; each round updates part of it via an
  F-function and swaps/permutes branches (SIMON, DES; GFN = more than two branches).
- standard_spn: a plain word-level substitution-permutation network that does NOT fit the above.
Prefer a SPECIFIC archetype over standard_spn whenever the evidence fits; use unknown only when
the text is too incomplete to tell. When in doubt between standard_spn and reflection_spn, look
for the inverse/middle structure - a wrong "standard" guess silently flattens a reflection cipher.

Cipher text:
{normalized_text}
"""


CIPHER_REFERENCE_PROMPT_TEMPLATE = """\
Write a SMALL, plain-Python REFERENCE implementation of the following cipher's ENCRYPTION, purely
for CORRECTNESS (an independent oracle to verify a separate model). Optimize for being obviously
right, not fast or general.

OUTPUT CONTRACT - return ONLY the Python program, nothing else (no prose, no markdown fences):
- It is a STRAIGHT-LINE program (a round loop), NOT a function definition. NO def, lambda, import,
  while, f-strings, or attributes. Only: assignment, for-over-range, if, list literals/indexing,
  arithmetic and bit ops (+ - * // % ** & | ^ ~ << >>), and the calls below.
- INPUTS are already defined for you as variables: `plaintext` (list of integer words) and `key`
  (list of integer words). Do NOT redefine them.
- HELPERS available (call them, do not reimplement): rol(x, n, w) / ror(x, n, w) rotate the w-bit
  value x by n bits; gf_mul(a, b, poly, w) multiplies in GF(2^w) mod the FULL polynomial poly
  (GF(2^4) x^4+x+1 -> 0x13, AES -> 0x11B). Also range/len/int/min/max/list/sum/pow.
- Define any S-box / permutation / constant as an inline list literal.
- Maintain the state as a list of words. After EACH round, append a COPY of the current state to a
  `trace` list. The trace must have one entry per round, each the same length as the state.
- Set the final result:  result = {{"output": <ciphertext words>, "trace": trace}}
  where output is the ciphertext as a list of words in the SAME representation as the test vectors.

Cipher:
{normalized_text}
"""


def build_cipher_reference_prompt(cipher_input) -> str:
    """Block 2 of Tier 1b: the focused, LAZY prompt (used only when the OCP KAT fails) that asks
    the LLM for a straight-line reference cipher runnable by run_reference() in the sandbox."""
    return CIPHER_REFERENCE_PROMPT_TEMPLATE.format(normalized_text=cipher_input.normalized_text)


def build_cipher_classification_prompt(cipher_input) -> str:
    """Build the small stage-1 prompt that classifies the cipher's structural archetype."""
    return CIPHER_CLASSIFICATION_PROMPT_TEMPLATE.format(
        normalized_text=cipher_input.normalized_text,
    )


def _classification_directive(classification) -> str:
    """The archetype directive block injected at the top of the formalize prompt (empty when
    there is no classification, so behavior is unchanged)."""
    if not isinstance(classification, dict):
        return ""
    arch = classification.get("archetype")
    directive = CIPHER_ARCHETYPES.get(arch)
    if not directive:
        return ""
    reason = classification.get("reason") or ""
    return (
        f"## CLASSIFIED ARCHETYPE: {arch}\n"
        f"A first-pass classifier identified this cipher as **{arch}**"
        f"{f' ({reason})' if reason else ''}. Build the spec for THIS archetype:\n"
        f"{directive}\n"
        f"Follow that archetype's rules below and do NOT force the cipher into a plain repeated-SPN "
        f"template. If the text CLEARLY contradicts this classification, follow the text and note "
        f"the correction in ambiguities.\n\n"
    )


def build_cipher_facts_extraction_prompt(cipher_input, classification=None) -> str:
    """Build the text-first prompt for extracting CipherFacts.

    When `classification` (the stage-1 result) is given, an archetype directive is prepended so
    the model builds the right representation instead of defaulting to a repeated SPN.
    """
    return TEXT_CIPHER_FACTS_PROMPT_TEMPLATE.format(
        schema=json.dumps(TEXT_CIPHER_FACTS_RESPONSE_SCHEMA, separators=(",", ":")),
        classification=_classification_directive(classification),
        source_type=cipher_input.source_type,
        format_hint=cipher_input.format_hint,
        language_hint=cipher_input.language_hint,
        source_name=cipher_input.source_name or "",
        normalized_text=cipher_input.normalized_text,
        facts_examples=few_shot_facts_text(cipher_input.normalized_text),
    )


CIPHER_REPAIR_PROMPT_TEMPLATE = """\
You previously produced a CipherSpec for OCP that is not correct yet. Fix it.

## Current CipherSpec
{spec}

## Problems to fix
{problems}

## Schema and format rules (the SAME rules the spec must follow)
{rules}

## Worked example
{examples}

How to fix:
- A problem may include a TRACEBACK (its last frame names the failing operation, e.g.
  `v_1_0 = v_0_0 ^ RC[i][0]` + IndexError -> the round-constant table RC is shorter than
  nbr_rounds; `Sb0_Sbox[vs_3_0]` + IndexError -> a value exceeds the S-box's input range;
  a MatrixLayer/mixcolumn frame -> the matrix dimension != its index-group length). Use it to
  find the EXACT layer to fix, then fix THAT layer's params.
- Read EACH problem above and change exactly the field it names. The messages are precise
  (they name the layer index and the missing/mismatched param), so fix that param - do not
  guess elsewhere. Examples of the mapping:
  - "layer N ('rotation') is missing required param(s) ['word_index']" -> add "word_index" to that layer's params.
  - "add_round_key mask has X active but subkey has Y words" -> make the mask have exactly Y ones (or set key_extract_indices to length X).
  - "amount A must satisfy 0 < amount < word_bitsize (W)" -> the rotation is over a wider unit than one word; it cannot be a word rotation at this width.
  - "unresolved placeholder(s) ['$name']" -> replace with the concrete value (this is not a versioned family).
  - "`operations` (the ordered round recipe) is EMPTY, but you extracted the round tables ..." ->
    you captured the INGREDIENTS (the S-box / permutation / matrix tables) but not the RECIPE.
    ADD the ordered `operations` (round_structure) list that applies them, one layer per step.
    For an SPN the order is sbox/subcell_sbox -> permutation/cell_shiftrow (ShuffleCell) ->
    matrix/mixcolumn (MixColumn) -> add_round_key (+ add_constant when the round has constants);
    reference the tables by the names the message lists. Confirm the exact order/layers against
    the paper - the KAT is the check. For a versioned family, put this shared skeleton in the
    top-level `operations`/`round_structure` (use $placeholders for per-version values); do NOT
    leave it empty with only table names under each version's params. Adding these layers is
    REQUIRED here and does NOT violate hard constraint 2 (that forbids DELETING layers).
- Change ONLY what the problems require; keep every other field byte-for-byte identical.
- Obey the schema rules above (layer param shapes, integer GF matrix coeffs, etc.).
- HARD CONSTRAINTS (a fix that breaks any of these is discarded and you will be asked again):
  1. NEVER edit test_vectors. They are the known-answer ground truth from the paper. If the
     KATs fail, the ROUND STRUCTURE is wrong, not the vectors - fix the structure to match them.
  2. NEVER delete a confusion/diffusion layer (sbox, matrix/MixColumn, permutation,
     rotation, shift, and/or/andxor/modadd) to make an error go away. Those layers ARE the
     algorithm; without one the cipher still builds but computes the wrong value. Fix the
     failing layer's PARAMETERS instead. (Removing a duplicate add_round_key/add_constant IS ok.)
  3. NEVER change word_bitsize or key_word_bitsize to "fit" an operation. The word/cell size
     is fixed by the cipher. A rotation that crosses word boundaries must be modeled with
     cell_layout / bit-slicing, not by shrinking the word size.
- Return ONLY the full corrected CipherSpec as one JSON object, no extra text.
"""


def build_repair_prompt(spec: dict, problems: List[str]) -> str:
    """Build a small, targeted prompt to fix a specific CipherSpec, not re-extract it."""
    from agent.skills.cipher_examples import few_shot_spec_text

    cipher_type = spec.get("cipher_type", "permutation")
    hint = cipher_type + " " + " ".join(
        (layer.get("layer_type") or "") for layer in spec.get("round_structure", [])
    )
    # Reuse the EXACT schema rules the draft prompt uses, so repair has the same full format
    # knowledge (layer param shapes, matrix coeffs, round-dependent/whitening, ...) instead
    # of just one example. Pulled from SYSTEM_PROMPT_TEMPLATE so the two never drift.
    start = SYSTEM_PROMPT_TEMPLATE.index("## Custom Cipher Definition")
    end = SYSTEM_PROMPT_TEMPLATE.index("## File Import")
    rules = SYSTEM_PROMPT_TEMPLATE[start:end].strip().replace("{{", "{").replace("}}", "}")
    return CIPHER_REPAIR_PROMPT_TEMPLATE.format(
        spec=json.dumps(spec, separators=(",", ":")),
        problems="\n".join(f"- {p}" for p in problems) or "- (unspecified)",
        rules=rules,
        examples=few_shot_spec_text(hint, k=1),
    )


RESPONSE_PROMPT_TEMPLATE = """\
You are an assistant for the OCP cryptanalysis tool. Summarize the results of the following analysis operations for the user.
Be concise and focus on the key findings (trail counts, weights, generated files, etc.).

## Results
{results}

## Session
{session_context}

Respond in a helpful, natural tone. If there were errors, explain what went wrong and suggest fixes.
"""


def build_response_prompt(
    results: List[dict],
    session_context: dict,
) -> str:
    """Build the prompt for generating user-facing responses."""
    results_str = json.dumps(
        [{"skill": r["skill"], "success": r["success"], "summary": r["summary"], "error": r.get("error")}
         for r in results],
        indent=2,
    )
    return RESPONSE_PROMPT_TEMPLATE.format(
        results=results_str,
        session_context=json.dumps(session_context, indent=2),
    )
