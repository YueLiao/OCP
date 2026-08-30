"""Skill that dynamically builds an OCP Primitive from a CipherSpec.

This is the core skill that bridges the gap between a structured cipher description
and an actual OCP cipher object that can be analyzed, visualized, and implemented.
"""

import math
import re
import traceback as _tb
from typing import Any, Dict, List

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.base import BaseSkill
from agent.skills.cipher_spec import CipherSpec, LayerSpec, _sanitize_identifier


def create_sbox_class(name, table):
    """Create an Sbox operator class from a lookup table at runtime.

    Args:
        name: Name for the S-box class.
        table: Lookup table (list of ints). Length must be a power of 2.

    Returns:
        A new Sbox subclass with the given table.
    """
    from operators.Sbox import Sbox

    input_bitsize = int(math.log2(len(table)))
    output_bitsize = input_bitsize  # assume square S-box

    class CustomSbox(Sbox):
        def __init__(self, input_vars, output_vars, ID=None):
            super().__init__(input_vars, output_vars, input_bitsize, output_bitsize, ID=ID)
            self.table = list(table)

    # OCP assigns probability-weighted S-box models (e.g. XORDIFF_PR for
    # DIFFERENTIALPATH_PROB) only to operators whose class name ends with "Sbox"
    # (see tools/model_configuration.set_model_versions). Every built-in follows
    # the "<NAME>_Sbox" convention, so custom S-boxes must too or they silently
    # fall back to the validity-only model and report weight 0.
    class_name = name if name.endswith("Sbox") else f"{name}_Sbox"
    CustomSbox.__name__ = class_name
    CustomSbox.__qualname__ = class_name
    return CustomSbox


def _norm_dir(d):
    """OCP's RotationLayer/ShiftLayer accept only 'l'/'r'; an LLM commonly writes the natural
    'left'/'right'. Normalize those synonyms so the build does not reject a correct spec. (Only
    for word rotation/shift - the LFSR direction legitimately uses 'left'/'right'.)"""
    return {"left": "l", "right": "r"}.get(d, d)


def _apply_layer(func, round_idx, layer_idx, layer_spec, sbox_classes):
    """Apply a single LayerSpec to a Layered_Function.

    Args:
        func: OCP Layered_Function instance.
        round_idx: Current round number.
        layer_idx: Current layer index within the round.
        layer_spec: LayerSpec describing the operation.
        sbox_classes: Dict mapping S-box names to Sbox operator classes.
    """
    from operators.boolean_operators import XOR, AND, OR, NOT, N_XOR, ANDXOR
    from operators.modular_operators import ModAdd
    from operators.operators import Equal
    from operators.AESround import AESround

    # Bitwise/arithmetic operators applied through SingleOperatorLayer. Each maps
    # input_indices (groups of source word indices) to output_indices. Binary ops
    # (xor/and/or/modadd) take a 2-word group; unary (not/equal) a 1-word group; n-ary
    # (n_xor) any group; andxor takes a 3-word group as out = (in0 & in1) ^ in2.
    # "equal" copies a word (used to save state for an ARX feed-forward).
    SINGLE_OPERATORS = {
        "xor": XOR, "and": AND, "or": OR, "modadd": ModAdd,
        "not": NOT, "n_xor": N_XOR, "andxor": ANDXOR, "equal": Equal,
    }

    lt = layer_spec.layer_type
    p = layer_spec.params

    # Fail with a clear, layer-specific message instead of a bare KeyError when the
    # extraction left out a required parameter (common when an LLM under-specifies a
    # key-schedule or round layer).
    _required = {
        "rotation": ("direction", "amount", "word_index"),
        "shift": ("direction", "amount", "word_index"),
        "sbox": ("sbox_name",),
        "permutation": ("table",),
        "matrix": ("matrix", "indices"),
        "gf2_linear": ("matrix", "index_in"),
        "add_constant": ("constant_mask", "constant_table"),
        "aes_round": ("input_indices", "output_indices"),
    }
    _req = () if (lt == "rotation" and (p or {}).get("rotations") is not None) else _required.get(lt, ())
    missing = [k for k in _req if k not in (p or {})]
    if missing:
        raise ValueError(
            f"'{lt}' layer is missing required param(s) {missing}. Got: "
            f"{sorted((p or {}).keys())}. Fix it in the JSON editor or with 'Fix with AI'."
        )
    unresolved = [k for k, v in (p or {}).items() if isinstance(v, str) and v.startswith("$")]
    if unresolved:
        raise ValueError(
            f"'{lt}' layer has unresolved placeholder(s) {unresolved} but the cipher is "
            f"not a parameterized family - replace them with concrete values."
        )

    if lt == "rotation":
        # Multi-word form: {"rotations": [[dir, amount, in, out], ...]} rotates several words
        # in one layer (ARX quarter-rounds rotate 4 lanes at once). Single-word form otherwise.
        if p.get("rotations") is not None:
            rots = [[_norm_dir(r[0])] + list(r[1:]) for r in p["rotations"]]
            func.RotationLayer(f"ROT_{layer_idx}", round_idx, layer_idx, rots)
        else:
            direction = _norm_dir(p["direction"])
            amount = p["amount"]
            word_index = p["word_index"]
            out_index = p.get("out_index")
            rot = [direction, amount, word_index, out_index] if out_index is not None else [direction, amount, word_index]
            func.RotationLayer(f"ROT_{layer_idx}", round_idx, layer_idx, rot)

    elif lt == "shift":
        direction = _norm_dir(p["direction"])
        amount = p["amount"]
        word_index = p["word_index"]
        out_index = p.get("out_index")
        if out_index is not None:
            sh = [direction, amount, word_index, out_index]
        else:
            sh = [direction, amount, word_index]
        func.ShiftLayer(f"SH_{layer_idx}", round_idx, layer_idx, sh)

    elif lt in SINGLE_OPERATORS:
        input_indices = p["input_indices"]
        output_indices = p["output_indices"]
        func.SingleOperatorLayer(f"{lt.upper()}_{layer_idx}", round_idx, layer_idx, SINGLE_OPERATORS[lt], input_indices, output_indices)

    elif lt == "sbox":
        sbox_name = p["sbox_name"]
        index = p.get("index")
        mask = p.get("mask")
        sbox_cls = sbox_classes.get(sbox_name)
        if sbox_cls is None:
            # Not a custom table - the spec may REFERENCE a built-in OCP S-box by name (e.g.
            # AES_Sbox, PRESENT_Sbox, Midori128_SSb0). Resolve + cache it so a version whose
            # 8-bit S-box (etc.) is not in the paper as a table can still build.
            from operators.Sbox import builtin_sbox_class, builtin_sbox_names
            sbox_cls = builtin_sbox_class(sbox_name)
            if sbox_cls is None:
                raise ValueError(
                    f"S-box '{sbox_name}' is not in sbox_tables ({sorted(sbox_classes)}) and is not a "
                    f"built-in OCP S-box. Provide its table under sbox_tables, or reference a built-in "
                    f"by name - available: {', '.join(builtin_sbox_names())}.")
            sbox_classes[sbox_name] = sbox_cls
        func.SboxLayer(f"SB_{layer_idx}", round_idx, layer_idx, sbox_cls, mask=mask, index=index)

    elif lt == "permutation":
        table = p["table"]
        func.PermutationLayer(f"P_{layer_idx}", round_idx, layer_idx, table)

    elif lt == "matrix":
        mat = p["matrix"]
        indices = p["indices"]
        polynomial = p.get("polynomial")
        func.MatrixLayer(f"MAT_{layer_idx}", round_idx, layer_idx, mat, indices, polynomial=polynomial)

    elif lt == "gf2_linear":
        # Bit-level GF(2) linear transform of individual words (e.g. a tweakey LFSR in
        # SKINNY/Deoxys): "matrix" is a word_bitsize x word_bitsize binary matrix applied
        # to each word in "index_in", writing into "index_out" (defaults to in place).
        mat = p["matrix"]
        index_in = p["index_in"]
        index_out = p.get("index_out", index_in)
        constants = p.get("constants")
        func.GF2Linear_TransLayer(
            f"GF2_{layer_idx}", round_idx, layer_idx, index_in, index_out, mat, constants=constants
        )

    elif lt == "aes_round":
        # Fused AES round (SubBytes + ShiftRows + MixColumns, no key) as one operator over
        # 16-byte state groups - used by AES-based designs like Rocca that treat a whole AES
        # round as a single primitive. input_indices/output_indices are grouped exactly like
        # the boolean operators, but each group MUST list 16 word positions (one 128-bit AES
        # state); AESround validates that. Any AddRoundKey is a separate add_round_key/xor
        # layer. Routed through SingleOperatorLayer exactly as primitives/rocca.py does.
        input_indices = p["input_indices"]
        output_indices = p["output_indices"]
        func.SingleOperatorLayer(f"AESR_{layer_idx}", round_idx, layer_idx, AESround, input_indices, output_indices)

    elif lt == "add_round_key":
        operator = p.get("operator", "xor")
        mask = p.get("mask")
        op_cls = XOR if operator == "xor" else ModAdd
        SK = func._parent_cipher.functions["SUBKEYS"]
        func.AddRoundKeyLayer(f"ARK_{layer_idx}", round_idx, layer_idx, op_cls, SK, mask=mask)

    elif lt == "add_constant":
        add_type = p.get("add_type", "xor")
        constant_mask = p["constant_mask"]
        constant_table = p["constant_table"]
        func.AddConstantLayer(f"C_{layer_idx}", round_idx, layer_idx, add_type, constant_mask, constant_table)

    elif lt == "add_identity":
        # Identity (do-nothing) layer: fills a layer slot in rounds where an operation
        # is skipped, so every round keeps the same number of layers (OCP's requirement).
        func.AddIdentityLayer(f"ID_{layer_idx}", round_idx, layer_idx)

    else:
        raise ValueError(f"Unknown layer type: {lt}")


def build_permutation_from_spec(spec):
    """Build an OCP Permutation from a CipherSpec.

    Args:
        spec: CipherSpec with cipher_type="permutation".

    Returns:
        An OCP Permutation primitive.
    """
    from primitives.primitives import Permutation
    import variables.variables as var

    # Instantiate a versioned family first (its top-level dimensions are placeholder 0s).
    if spec.versions:
        spec = spec.instantiate(spec.default_version or next(iter(spec.versions)))

    # A bit-sliced `layout` (KNOT/RECTANGLE) lowers to word_bitsize=1 layers via its own
    # expander; do it here so EVERY build path (execute, _kat_problems preflight,
    # verify_all_versions) handles it, not only execute. No-op without a layout.
    if spec.layout:
        spec = spec.expand_bitsliced()

    # Single canonical lowering chain (code params -> ARX / linear_diffusion / cell layout /
    # ...), shared with the block-cipher builder and the exporter so they never drift.
    spec = spec.compile()

    # Create S-box classes
    sbox_classes = {}
    for sbox_name, table in spec.sbox_tables.items():
        sbox_classes[sbox_name] = create_sbox_class(sbox_name, table)

    # Create input/output variables
    s_input = [var.Variable(spec.word_bitsize, ID=f"in{i}") for i in range(spec.nbr_words)]
    s_output = [var.Variable(spec.word_bitsize, ID=f"out{i}") for i in range(spec.nbr_words)]

    nbr_layers = len(spec.round_structure)
    config = [nbr_layers, spec.nbr_words, spec.nbr_temp_words, spec.word_bitsize]

    # Create permutation using a dynamic subclass
    class DynamicPermutation(Permutation):
        def __init__(self, name, s_in, s_out, nbr_rounds, cfg):
            super().__init__(name, s_in, s_out, nbr_rounds, cfg)
            S = self.functions["PERMUTATION"]
            for i in range(1, nbr_rounds + 1):
                for layer_idx, layer_spec in enumerate(spec.round_structure):
                    if layer_spec.is_active(i, nbr_rounds):
                        _apply_layer(S, i, layer_idx, layer_spec.for_round(i), sbox_classes)
                    else:
                        S.AddIdentityLayer(f"ID_{layer_idx}", i, layer_idx)

    perm = DynamicPermutation(
        f"{_sanitize_identifier(spec.name)}_PERM", s_input, s_output, spec.nbr_rounds, config
    )
    if spec.test_vectors:
        perm.test_vectors = spec.test_vectors
    perm.post_initialization()
    return perm


def build_blockcipher_from_spec(spec):
    """Build an OCP Block_cipher from a CipherSpec.

    Args:
        spec: CipherSpec with cipher_type="blockcipher".

    Returns:
        An OCP Block_cipher primitive.
    """
    from primitives.primitives import Block_cipher
    import variables.variables as var
    import operators.operators as op

    # A versioned family carries placeholder 0 dimensions at top level (the real block_size /
    # word_bitsize / nbr_words / nbr_rounds live per version); instantiate the chosen version
    # first, or the build would run with 0 rounds/words and crash on empty variable arrays.
    if spec.versions:
        spec = spec.instantiate(spec.default_version or next(iter(spec.versions)))

    # Bit-sliced `layout` expands here too, so every build path handles it (no-op without one).
    if spec.layout:
        spec = spec.expand_bitsliced()

    # Single canonical lowering chain (code params -> archetype / linear_diffusion / cell layout
    # / whitening / ...), shared with the permutation builder and the exporter so they never drift.
    spec = spec.compile()

    # Create S-box classes
    sbox_classes = {}
    for sbox_name, table in spec.sbox_tables.items():
        sbox_classes[sbox_name] = create_sbox_class(sbox_name, table)

    key_word_bitsize = spec.key_word_bitsize or spec.word_bitsize
    key_nbr_words = spec.key_nbr_words or (spec.key_size // key_word_bitsize)

    # Create input/output variables
    p_input = [var.Variable(spec.word_bitsize, ID=f"p{i}") for i in range(spec.nbr_words)]
    k_input = [var.Variable(key_word_bitsize, ID=f"k{i}") for i in range(key_nbr_words)]
    c_output = [var.Variable(spec.word_bitsize, ID=f"c{i}") for i in range(spec.nbr_words)]

    s_nbr_layers = len(spec.round_structure)
    k_nbr_layers = len(spec.key_schedule) if spec.key_schedule else 1
    # key_extract_indices is either a flat list (same words every round), a list of entries
    # (ROUND-DEPENDENT: round i extracts entry (i-1) % period, e.g. Midori/LED alternating
    # K0/K1), or entries that are {"xor": [share0_idx, share1_idx]} meaning the subkey is the
    # XOR of two extracted key slices (e.g. Midori's whitening key WK = K0 (+) K1, built inside
    # SUBKEYS). Every entry must yield the same subkey word count.
    _extract = spec.key_extract_indices
    _extract_periodic = bool(_extract) and isinstance(_extract[0], (list, dict))

    def _entry_words(e):
        if isinstance(e, dict):
            return len(e["words"]) if "from" in e else len(e["xor"][0])
        return len(e)

    # A combined subkey is the XOR of n shares (Midori WK = K0^K1 is n=2; SKINNY-384
    # subtweakey = TK1^TK2^TK3 is n=3). SUBKEYS holds all n*sk_nbr_words extracted shares,
    # then reduces them to sk_nbr_words in a second layer.
    _xor_n = (max((len(e["xor"]) for e in _extract if isinstance(e, dict) and "xor" in e),
                  default=1) if _extract_periodic else 1)
    _has_xor = _xor_n >= 2
    sk_nbr_words = _entry_words(_extract[0]) if _extract_periodic else len(_extract)
    sk_nbr_layers = 2 if _has_xor else 1
    sk_nbr_temp = (_xor_n - 1) * sk_nbr_words if _has_xor else 0

    s_config = [s_nbr_layers, spec.nbr_words, spec.nbr_temp_words, spec.word_bitsize]
    k_config = [k_nbr_layers, key_nbr_words, spec.key_nbr_temp_words, key_word_bitsize]
    sk_config = [sk_nbr_layers, sk_nbr_words, sk_nbr_temp, spec.word_bitsize]

    # Key schedule usually runs once per cipher round, but Simon's runs fewer rounds
    # (nbr_rounds - m + 1) and the subkey for round i reaches back to a historical KS state.
    k_nbr_rounds = spec.key_nbr_rounds or spec.nbr_rounds

    class DynamicBlockCipher(Block_cipher):
        def __init__(self, name, p_in, k_in, c_out, nbr_rounds, k_rounds, s_cfg, k_cfg, sk_cfg):
            super().__init__(name, p_in, k_in, c_out, nbr_rounds, k_rounds, s_cfg, k_cfg, sk_cfg)

            S = self.functions["PERMUTATION"]
            KS = self.functions["KEY_SCHEDULE"]
            SK = self.functions["SUBKEYS"]

            # Subkey extraction (round-dependent when key_extract_indices is a list of
            # entries; an entry may be {"xor": [share0, share1]} to build a combined subkey)
            from operators.boolean_operators import XOR, N_XOR
            for i in range(1, nbr_rounds + 1):
                e = _extract[(i - 1) % len(_extract)] if _extract_periodic else _extract
                if isinstance(e, dict) and "from" in e:   # extract from a historical KS state
                    SK.ExtractionLayer("SK_EX", i, 0, e["words"], KS.vars[e["from"]][0])
                    if _has_xor:                          # keep SK 2-layer if the family uses xor
                        SK.AddIdentityLayer("SK_ID", i, 1)
                elif isinstance(e, dict):      # subkey = XOR of the n shares, computed in SUBKEYS
                    flat = [idx for sh in e["xor"] for idx in sh]
                    SK.ExtractionLayer("SK_EX", i, 0, flat, KS.vars[i][0])
                    if _xor_n == 2:
                        SK.SingleOperatorLayer("SK_XOR", i, 1, XOR,
                                               [[j, sk_nbr_words + j] for j in range(sk_nbr_words)],
                                               list(range(sk_nbr_words)))
                    else:
                        SK.SingleOperatorLayer("SK_XOR", i, 1, N_XOR,
                                               [[k * sk_nbr_words + j for k in range(_xor_n)]
                                                for j in range(sk_nbr_words)],
                                               list(range(sk_nbr_words)))
                elif _has_xor:                 # keep SK 2-layer: extract (padded), then identity
                    SK.ExtractionLayer("SK_EX", i, 0, list(e) * _xor_n, KS.vars[i][0])
                    SK.AddIdentityLayer("SK_ID", i, 1)
                else:
                    SK.ExtractionLayer("SK_EX", i, 0, e, KS.vars[i][0])

            # Key schedule (k_rounds may be < cipher rounds, e.g. Simon's nbr_rounds - m + 1)
            if spec.key_schedule:
                for i in range(1, k_rounds):
                    for layer_idx, layer_spec in enumerate(spec.key_schedule):
                        if layer_spec.is_active(i, k_rounds):
                            _apply_layer(KS, i, layer_idx, layer_spec.for_round(i), sbox_classes)
                        else:
                            KS.AddIdentityLayer(f"ID_{layer_idx}", i, layer_idx)
            else:
                # No key evolution (e.g. Midori/LED keep the key fixed and just select
                # different words each round): propagate the key unchanged so round-dependent
                # extraction still sees the key state at every round, like LED's AddIdentity.
                for i in range(1, k_rounds):
                    KS.AddIdentityLayer("K_ID", i, 0)

            # Round function - store parent ref for add_round_key layers
            S._parent_cipher = self
            for i in range(1, nbr_rounds + 1):
                for layer_idx, layer_spec in enumerate(spec.round_structure):
                    if layer_spec.is_active(i, nbr_rounds):
                        _apply_layer(S, i, layer_idx, layer_spec.for_round(i), sbox_classes)
                    else:
                        S.AddIdentityLayer(f"ID_{layer_idx}", i, layer_idx)

    cipher = DynamicBlockCipher(
        _sanitize_identifier(spec.name), p_input, k_input, c_output,
        spec.nbr_rounds, k_nbr_rounds,
        s_config, k_config, sk_config,
    )
    if spec.test_vectors:
        cipher.test_vectors = spec.test_vectors
    cipher.post_initialization()
    return cipher


def _hex_to_words(value, word_bitsize):
    """Deterministically split a hex string into MSB-first words of `word_bitsize` bits.

    This takes the mechanical hex->word conversion OFF the LLM. The model's job is to copy
    the raw hex string of a test vector from the paper verbatim (a value it can quote), and
    THIS function does the splitting - so the mis-counts we kept hitting (Midori's 31/32-word
    outputs, a doubled variant appended, silent zero-padding) become impossible. Standard
    big-endian cipher convention: the most-significant `word_bitsize` bits are word 0.

    Works for any word_bitsize (1-bit lanes through 64-bit words) via the same shift formula.
    A non-string `value` is returned unchanged, so an already-split integer word list still
    passes through. Raises ValueError when the hex is malformed or its bit length is not a
    whole number of words - the caller surfaces that as a test-vector error instead of
    silently dropping the vector (a dropped KAT is worse than a rejected one).
    """
    if not isinstance(value, str):
        return value
    s = re.sub(r"[\s_,]", "", value.strip().lower())
    if s.startswith("0x"):
        s = s[2:]
    if s == "":
        raise ValueError("empty hex string")
    if not re.fullmatch(r"[0-9a-f]+", s):
        raise ValueError(f"{value!r} is not a hex string")
    total_bits = len(s) * 4
    if not isinstance(word_bitsize, int) or word_bitsize <= 0:
        raise ValueError(f"cannot split hex without a positive word_bitsize (got {word_bitsize!r})")
    if total_bits % word_bitsize != 0:
        raise ValueError(
            f"hex value {value!r} is {total_bits} bits, not a whole number of "
            f"{word_bitsize}-bit words. Copy the exact hex from the paper; do not pad or truncate.")
    n = total_bits // word_bitsize
    v = int(s, 16)
    mask = (1 << word_bitsize) - 1
    return [(v >> (word_bitsize * (n - 1 - i))) & mask for i in range(n)]


def _effective_word_sizes(spec):
    """The (word_bitsize, key_word_bitsize) to split hex test vectors with.

    For a versioned family the top-level sizes are 0/None until the builder instantiates the
    chosen version, but test vectors are normalized BEFORE that - so resolve the default
    version's sizes here, otherwise a hex vector cannot be split (word size unknown).
    """
    # A bit-sliced `layout` cipher (KNOT/RECTANGLE) has a 1-bit word (the state is rows*cols
    # bits), so its hex test vectors split into individual bits.
    if getattr(spec, "layout", None):
        return 1, 1
    wb, kwb = spec.word_bitsize, spec.key_word_bitsize
    versions = getattr(spec, "versions", None)
    if versions and not (isinstance(wb, int) and wb > 0):
        v = versions.get(getattr(spec, "default_version", None)) or next(iter(versions.values()), {})
        params = v.get("params", {}) if isinstance(v, dict) else {}
        # A cell-level cipher's "word" for splitting a hex vector is its CELL (cell_bits); the
        # version may carry cell_bits instead of word_bitsize.
        wb = (v.get("word_bitsize") or params.get("word_bitsize")
              or v.get("cell_bits") or params.get("cell_bits") or wb)
        kwb = v.get("key_word_bitsize") or params.get("key_word_bitsize") or kwb
    if not (isinstance(wb, int) and wb > 0):
        cl = getattr(spec, "cell_layout", None)
        if isinstance(cl, dict) and isinstance(cl.get("cell_bits"), int) and cl["cell_bits"] > 0:
            wb = cl["cell_bits"]
    return wb, (kwb or wb)


def _effective_state_counts(spec):
    """The (nbr_words, key_nbr_words) of the version being built - the default version for a
    family (top-level counts are 0 until the builder instantiates). Used to drop test vectors
    that belong to a different variant."""
    versions = getattr(spec, "versions", None)
    vdef = {}
    if versions:
        vdef = versions.get(getattr(spec, "default_version", None)) or next(iter(versions.values()), {})
    # A bit-sliced `layout` cipher's word-count is rows*cols = the block size in bits, and that
    # trumps any (stale/default) top-level nbr_words. Resolve it FIRST.
    lay = getattr(spec, "layout", None)
    if lay:
        vparams = vdef.get("params", {}) if isinstance(vdef, dict) else {}
        rows = (vdef.get("rows") if isinstance(vdef, dict) else None) or lay.get("rows")
        cols = (vdef.get("cols") if isinstance(vdef, dict) else None) or lay.get("cols")
        if isinstance(rows, int) and isinstance(cols, int) and rows > 0 and cols > 0:
            return rows * cols, 0
        b = vparams.get("b") or (spec.block_size if isinstance(spec.block_size, int) else None)
        if isinstance(b, int) and b > 0:
            return b, 0

    nw, kw = spec.nbr_words, spec.key_nbr_words
    if versions and not (isinstance(nw, int) and nw > 0):
        params = vdef.get("params", {}) if isinstance(vdef, dict) else {}
        # A cell cipher counts cells (nbr_cells), which is the state's word count for a vector.
        nw = (vdef.get("nbr_words") or params.get("nbr_words")
              or vdef.get("nbr_cells") or params.get("nbr_cells") or nw)
        kw = vdef.get("key_nbr_words") or params.get("key_nbr_words") or kw
    if not (isinstance(nw, int) and nw > 0):
        cl = getattr(spec, "cell_layout", None)
        if isinstance(cl, dict) and isinstance(cl.get("nbr_cells"), int) and cl["nbr_cells"] > 0:
            nw = cl["nbr_cells"]
    return nw, kw


def _drop_cross_variant_vectors(vectors, exp_state, exp_key, cipher_type):
    """Drop normalized [inputs, output] vectors whose block/key word-count matches a DIFFERENT
    variant than the one being built (a family paper lists all variants' KATs in one place, and
    the LLM keeps them together). Only drop when a MATCHING vector remains - otherwise the
    declared size is the wrong one, and validate() should surface that rather than us silently
    discarding every vector. Returns (kept_vectors, dropped_count)."""
    if not vectors or not (isinstance(exp_state, int) and exp_state > 0):
        return vectors, 0
    matched, mismatched = [], []
    for tv in vectors:
        ok = True
        try:
            ins, out = tv[0], tv[1]
            if isinstance(out, list) and len(out) != exp_state:
                ok = False
            elif ins and isinstance(ins[0], list) and len(ins[0]) != exp_state:
                ok = False
            elif (cipher_type == "blockcipher" and isinstance(exp_key, int) and exp_key > 0
                    and len(ins) > 1 and isinstance(ins[1], list) and len(ins[1]) != exp_key):
                ok = False
        except (IndexError, TypeError):
            ok = True
        (matched if ok else mismatched).append(tv)
    if mismatched and matched:
        return matched, len(mismatched)
    return vectors, 0


def _normalize_test_vectors(test_vectors, cipher_type, word_bitsize=None, key_word_bitsize=None):
    """Coerce assorted test-vector shapes into the canonical [inputs, output] form.

    Canonical form (what code generation and verification consume): each vector is
    ``[inputs, output]`` where for a permutation ``inputs = [[in_words]]`` and for a
    block cipher ``inputs = [[plaintext_words], [key_words]]``; ``output`` is the
    list of output words. Also accepts dicts keyed by input/output (or
    plaintext/key/ciphertext) and flat input word lists.

    When `word_bitsize` (and, for the key, `key_word_bitsize`) is given, any field supplied
    as a raw HEX STRING is split into words deterministically via `_hex_to_words` - the LLM
    is meant to copy the paper's hex verbatim and let this do the arithmetic. Hex parsing is
    A positive word_bitsize enables hex splitting: cell/word ciphers (>= 4) and bit-sliced
    layout ciphers (== 1, where a hex vector splits into the state's individual bits).

    Vectors whose SHAPE cannot be interpreted are dropped; a MALFORMED hex value raises
    ValueError (surfaced by the caller) rather than being dropped, so a mis-copied KAT is
    reported instead of silently vanishing.
    """
    if not test_vectors:
        return test_vectors

    wb = word_bitsize if (isinstance(word_bitsize, int) and word_bitsize >= 1) else None
    # The KEY may be bit-level (key_word_bitsize == 1) even when the STATE is cell-level (a
    # cell_layout cipher's key is XORed into the bit-expanded state), so split the key by its
    # OWN size down to 1 - only fall back to the state size when key_word_bitsize is absent.
    kwb = key_word_bitsize if (isinstance(key_word_bitsize, int) and key_word_bitsize >= 1) else wb

    def _field(val, bits):
        """A single plaintext/key/output field -> a word list (hex string -> split words)."""
        if val is None:
            return None
        if isinstance(val, str):
            if bits is None:
                raise ValueError(f"field {val!r} is a hex string but the word size is unknown "
                                 f"here; give it as a list of integer words")
            return _hex_to_words(val, bits)
        return list(val)

    normalized = []
    errors = []
    for i, tv in enumerate(test_vectors):
        try:
            if isinstance(tv, dict):
                out = tv.get("output") or tv.get("ciphertext") or tv.get("out") or tv.get("expected")
                if cipher_type == "blockcipher":
                    pt = tv.get("plaintext") or tv.get("input") or tv.get("pt")
                    key = tv.get("key")
                    if pt is None or key is None or out is None:
                        continue
                    normalized.append([[_field(pt, wb), _field(key, kwb)], _field(out, wb)])
                else:
                    inp = tv.get("input") or tv.get("plaintext") or tv.get("in")
                    if inp is None or out is None:
                        continue
                    inp = _field(inp, wb)
                    if inp and not isinstance(inp[0], list):
                        inp = [inp]
                    normalized.append([inp, _field(out, wb)])
            elif isinstance(tv, (list, tuple)) and len(tv) == 2:
                inp, out = tv[0], tv[1]
                if isinstance(inp, str):
                    inp = [_field(inp, wb)]
                elif isinstance(inp, (list, tuple)) and inp and isinstance(inp[0], (list, tuple, str)):
                    # Nested inputs, one entry per input block; for a block cipher the second
                    # block is the key and uses the key word size.
                    inp = [_field(sub, kwb if (cipher_type == "blockcipher" and j == 1) else wb)
                           for j, sub in enumerate(inp)]
                else:
                    inp = [_field(inp, wb)]
                normalized.append([inp, _field(out, wb)])
        except ValueError as exc:
            errors.append(f"Test vector {i + 1}: {exc}")
        except (TypeError, IndexError):
            continue
    if errors:
        raise ValueError("; ".join(errors))
    return normalized


def _spec_needs_unroll(spec):
    """True if the spec has round-dependent layers (only_rounds/except_rounds).

    Such layers make rounds NON-isomorphic (e.g. FUTURE/AES skip a layer in the last
    round). The default loop-compressed code generation assumes every round is identical
    and would apply the active-round layer on the differing rounds too, producing wrong
    output. Generating with unroll=True emits each round explicitly and stays correct.
    """
    if spec is None:
        return False
    # An ARX permutation with more than one selection phase (ChaCha columns/diagonals, Forro's
    # 8 selections) has per-round layer params, and a feed-forward one has a distinct first/last
    # round - both need unrolling. Same for any layer that carries phase_params.
    _arx = getattr(spec, "arx", None)
    if _arx and (len(_arx.get("selections", [[]])) > 1 or _arx.get("feedforward")):
        return True
    if any(getattr(l, "phase_params", None) for l in (spec.round_structure or [])):
        return True
    # A key_archetype expands into pre/post-whitening rounds + a final round that differ from
    # the middle rounds, so it always needs unrolling.
    if getattr(spec, "key_archetype", None):
        return True
    # Whitening expands (at build time) into an extra round whose non-key layers are
    # round-dependent, so it needs unrolling even though the raw spec shows no such layer.
    if getattr(spec, "pre_whitening", False) or getattr(spec, "post_whitening", False):
        return True
    # Round-dependent key extraction (key_extract_indices as a list of entries, incl. an
    # {"xor": ...} combined-subkey entry) extracts different words per round; the
    # loop-compressed form can't express that.
    ext = getattr(spec, "key_extract_indices", None)
    if isinstance(ext, list) and ext and isinstance(ext[0], (list, dict)):
        return True
    layers = list(spec.round_structure or []) + list(spec.key_schedule or [])
    return any(
        getattr(l, "only_rounds", None) is not None or getattr(l, "except_rounds", None) is not None
        for l in layers
    )


def extract_ocp_round_states(cipher, inputs, func_name="PERMUTATION"):
    """Concrete per-round DATA state of a built OCP cipher for one input, for divergence checks.

    Generates the UNROLLED implementation (every intermediate v_<round>_<layer>_<word> is a named
    variable), execs the module prelude (S-box tables + ROTL/ROTR helpers) and then the cipher
    function's BODY in a namespace with the inputs bound, and reads the state AFTER each round by
    the OCP model's own variable IDs (functions[func].vars[r][nbr_layers][w].ID). Returns
    {"states": [state_after_round_1, ...], "output": last_state} where each state is a word list,
    or {"error": ...} on failure. `inputs` is [plaintext_words] (permutation) or
    [plaintext_words, key_words] (block cipher).
    """
    import ast
    import io as _io
    from contextlib import redirect_stdout as _rs
    import implementations.implementations as imp
    from tools.paths import get_files_dir
    try:
        S = cipher.functions[func_name]
        nbr_rounds, nbr_layers, nbr_words = S.nbr_rounds, S.nbr_layers, S.nbr_words
        fn = get_files_dir() / f"{cipher.name}_trace.py"
        with _rs(_io.StringIO()):
            imp.generate_implementation(cipher, fn, "python", True)   # unroll=True
        tree = ast.parse(fn.read_text())
        # The main cipher function takes an input + output list arg (permutation: IN_/OUT_; block
        # cipher: plaintext/key/ciphertext); ROTL/ROTR/GMUL/MAT_/tables are the prelude before it.
        # Exec the prelude, then the main body with the inputs bound by matching arg name.
        _IN = {"IN_", "plaintext", "s_input", "p_input"}
        _KEY = {"K_", "key", "k_input"}
        _OUT = {"OUT_", "ciphertext", "s_output", "c_output"}
        main = None
        prelude = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                aset = {a.arg for a in node.args.args}
                if (aset & _IN) and (aset & _OUT):
                    main = node
                    break
            prelude.append(node)
        if main is None:
            return {"error": "could not locate the generated cipher function"}
        ns = {}
        exec(compile(ast.Module(prelude, []), "<ocp-prelude>", "exec"), ns)
        for a in (arg.arg for arg in main.args.args):
            if a in _IN:
                ns[a] = list(inputs[0])
            elif a in _KEY:
                ns[a] = list(inputs[1]) if len(inputs) > 1 else []
            elif a in _OUT:
                ns[a] = [0] * nbr_words
        exec(compile(ast.Module(main.body, []), "<ocp-body>", "exec"), ns)
        states = []
        for r in range(1, nbr_rounds + 1):
            states.append([ns[S.vars[r][nbr_layers][w].ID] for w in range(nbr_words)])
        return {"states": states, "output": states[-1] if states else list(ns["OUT_"])}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def first_divergence(ocp_states, ref_states):
    """First round (1-based, from the start) where the OCP model's per-round state differs from the
    reference oracle's. Both are lists of [state-after-round-r] word lists (aligned by the prereq
    work). Returns {round, ocp, ref, ocp_rounds, ref_rounds, length_mismatch}; round is None when
    they agree up to the shorter length. A round-count mismatch is reported too - it is itself a
    signal (e.g. a doubled whitening round makes OCP one round longer than the correct cipher)."""
    n = min(len(ocp_states), len(ref_states))
    diff = next((i for i in range(n) if ocp_states[i] != ref_states[i]), None)
    return {
        "round": (diff + 1) if diff is not None else None,
        "ocp": ocp_states[diff] if diff is not None else None,
        "ref": ref_states[diff] if diff is not None else None,
        "ocp_rounds": len(ocp_states),
        "ref_rounds": len(ref_states),
        "length_mismatch": len(ocp_states) != len(ref_states),
    }


def verify_reference(code, spec):
    """Run the LLM-supplied reference against the spec's KATs (block 3). Returns {ran, passed,
    total, all_passed, failures}. all_passed => the reference reproduces the paper's answers, so
    the paper UNDERSTANDING is correct and it can be trusted as a per-round oracle; NOT all_passed
    => the failure is in understanding the cipher, not in the OCP encoding."""
    from agent.skills.cipher_spec import run_reference
    passed, failures = 0, []
    tvs = spec.test_vectors or []
    for tv in tvs:
        inputs, expected = tv[0], tv[1]
        pt = inputs[0]
        key = inputs[1] if len(inputs) > 1 else None
        out, _ = run_reference(code, pt, key)
        if out is None:
            failures.append({"input": inputs, "error": "reference produced no usable output"})
        elif list(out) == list(expected):
            passed += 1
        else:
            failures.append({"input": inputs, "expected": list(expected), "computed": list(out)})
    return {"ran": True, "passed": passed, "total": len(tvs),
            "all_passed": bool(tvs) and passed == len(tvs), "failures": failures}


def localize_divergence(cipher, spec, reference_code, func_name="PERMUTATION"):
    """Blocks 5+6: given a built OCP cipher whose KAT FAILS and a reference whose KAT PASSES, find
    the FIRST round where the OCP model diverges from the reference (on the first vector the OCP
    gets wrong) and return a repair-ready message localizing it, or None if it cannot localize.
    """
    from agent.skills.cipher_spec import run_reference
    for tv in (spec.test_vectors or []):
        inputs, expected = tv[0], tv[1]
        pt = inputs[0]
        key = inputs[1] if len(inputs) > 1 else None
        ocp = extract_ocp_round_states(cipher, inputs, func_name)
        if ocp.get("error") or not ocp.get("states"):
            continue
        if ocp["states"][-1] == list(expected):
            continue                                   # OCP already right on this one - skip
        _, ref_trace = run_reference(reference_code, pt, key)
        if not ref_trace:
            continue
        dv = first_divergence(ocp["states"], ref_trace)
        lines = []
        if dv["length_mismatch"]:
            lines.append(
                f"The OCP model runs {dv['ocp_rounds']} internal round(s) but the correct cipher "
                f"(reference) has {dv['ref_rounds']} - a round-count difference (often a doubled or "
                f"missing whitening round). Reconcile the round count / whitening first.")
        if dv["round"] is not None:
            lines.append(
                f"Reference-oracle divergence: the OCP model FIRST disagrees with a KAT-correct "
                f"reference implementation at round {dv['round']} - after that round the OCP state "
                f"is {dv['ocp']} but the correct state is {dv['ref']}. Fix the layer(s) applied in "
                f"round {dv['round']} (compare which words changed); everything up to round "
                f"{dv['round'] - 1} already matches, so do NOT touch earlier rounds.")
        elif not dv["length_mismatch"]:
            continue                                   # aligned everywhere yet KAT failed - unhelpful
        return " ".join(lines)
    return None


def _concise_traceback(frames=5):
    """The last few OCP-code traceback frames of the CURRENT exception - enough to point repair at
    the FAILING OPERATOR/LAYER (e.g. operators/boolean_operators.py in SboxLayer) instead of a bare
    'list index out of range'. Filters out importlib/frozen/site-packages noise. Called in except."""
    import sys
    exc_type, exc, tb = sys.exc_info()
    stack = _tb.extract_tb(tb)
    ocp = [f for f in stack if any(p in (f.filename or "") for p in
           ("/agent/", "/operators/", "/primitives/", "/implementations/", "/files/"))]
    use = (ocp or stack)[-frames:]
    lines = [f"  {(f.filename or '').split('/')[-1]}:{f.lineno} in {f.name}: {(f.line or '').strip()}"
             for f in use]
    return "\n".join(lines + [f"{exc_type.__name__ if exc_type else 'Error'}: {exc}"])


def verify_cipher_test_vectors(cipher, spec):
    """Check that a freshly built cipher reproduces the spec's test vectors.

    A custom cipher always *builds* as long as its structure is well-formed, even
    when the layers, indices, or order are wrong. The only objective correctness
    signal is a known input/output pair: we generate a Python implementation and
    run each provided test vector through it, comparing the computed output to the
    expected one.

    Returns a result dict:
      - {"tested": False, "reason": "no_test_vectors"} when the spec has none
        (custom ciphers have no built-in reference to check against).
      - {"tested": False, "reason": "codegen_failed", "error": ...} if the Python
        implementation could not be generated.
      - {"tested": True, "passed": p, "total": n, "failed": n-p,
         "all_passed": bool, "impl_file": path} otherwise.
    """
    if not spec.test_vectors:
        return {"tested": False, "reason": "no_test_vectors"}

    import io
    from contextlib import redirect_stdout
    import implementations.implementations as imp
    from tools.paths import get_files_dir

    files_dir = get_files_dir()
    try:
        files_dir.mkdir(parents=True, exist_ok=True)
        filename = files_dir / f"{cipher.name}.py"
        with redirect_stdout(io.StringIO()):
            imp.generate_implementation(cipher, filename, "python", _spec_needs_unroll(spec))
    except Exception as exc:
        return {"tested": False, "reason": "codegen_failed", "error": str(exc),
                "traceback": _concise_traceback()}

    passed = 0
    failures = []
    total = len(spec.test_vectors)
    # Let the CIPHER produce its NATURAL output length (output_len=None) rather than sizing the
    # buffer from len(expected): a wrong expected length must not corrupt the buffer (it produced
    # e.g. 31 computed words and a raw "list assignment index out of range"). spec.nbr_words is
    # NOT reliable here - a layout/cell_layout spec carries a placeholder until expansion - so we
    # compare against the actual computed length and report a mismatch readably.
    for idx, test_vector in enumerate(spec.test_vectors):
        inputs, expected = test_vector[0], test_vector[1]
        try:
            with redirect_stdout(io.StringIO()):
                computed = imp.evaluate_python(cipher, inputs, output_len=None)
        except Exception as exc:
            failures.append({"input": inputs, "error": str(exc), "traceback": _concise_traceback()})
            continue
        if isinstance(expected, list) and isinstance(computed, list) and len(expected) != len(computed):
            failures.append({"input": inputs, "expected": expected,
                             "error": f"expected output has {len(expected)} word(s); the cipher "
                                      f"produced {len(computed)} - fix the vector's length"})
        elif computed == expected:
            passed += 1
        else:
            failures.append({"input": inputs, "expected": expected, "computed": computed})

    return {
        "tested": True,
        "passed": passed,
        "total": total,
        "failed": total - passed,
        "all_passed": passed == total,
        "impl_file": str(filename),
        "failures": failures,
    }


def _diagnose_unbuilt_version(spec, vname, error_str=""):
    """Best-effort, GENERAL explanation of why a family version failed to build, phrased so the
    user knows exactly what to supply. Structurally-divergent versions (Midori128 vs Midori64)
    fail because the SHARED round skeleton names a small S-box / key shape that does not fit the
    version's bigger cell - the most actionable signal is 'this version's S-box is the wrong size
    / not defined'. Returns a short hint string, or "" (caller falls back to the raw error).
    Never raises."""
    try:
        vspec = spec.instantiate(vname)
    except Exception:
        return ""
    try:
        cell_bits = None
        if getattr(vspec, "cell_layout", None) and isinstance(vspec.cell_layout, dict):
            cell_bits = vspec.cell_layout.get("cell_bits")
        if not isinstance(cell_bits, int) or cell_bits <= 0:
            cell_bits = vspec.word_bitsize if isinstance(vspec.word_bitsize, int) else None
        tables = vspec.sbox_tables or {}
        # S-box names the round actually references + any name the version params carry.
        referenced = []
        for layer in (vspec.round_structure or []):
            if "sbox" in (layer.layer_type or ""):
                nm = (layer.params or {}).get("sbox_name")
                if nm and nm not in referenced:
                    referenced.append(nm)
        vparams = ((spec.versions or {}).get(vname) or {}).get("params") or {}
        pname = vparams.get("sbox_name")
        if pname and pname not in tables and pname not in referenced:
            # The version WANTS a distinct S-box (e.g. Midori128's SSb) that was never provided.
            avail = ", ".join(tables.keys()) or "none"
            return (f"{vname} references S-box '{pname}' in its params, but sbox_tables has only "
                    f"[{avail}]. Provide the '{pname}' table(s) for this version.")
        if isinstance(cell_bits, int) and cell_bits > 0:
            need = 1 << cell_bits
            for nm in referenced:
                t = tables.get(nm)
                if isinstance(t, list) and len(t) != need:
                    return (f"{vname} has {cell_bits}-bit cells but its S-box '{nm}' has {len(t)} "
                            f"entries (a {cell_bits}-bit cell needs a {need}-entry S-box). This "
                            f"version uses a different S-box than the default - supply its "
                            f"{cell_bits}-bit table(s) via the Editable JSON.")
                if t is None:
                    avail = ", ".join(tables.keys()) or "none"
                    return (f"{vname} references S-box '{nm}' which is not in sbox_tables "
                            f"[{avail}].")
    except Exception:
        return ""
    return ""


def verify_all_versions(spec):
    """Build and KAT-verify EVERY version of a family separately, returning
    {version_name: verification_result}. Each version is instantiated on its own (so a family
    whose versions differ in STRUCTURE - Midori64's 1 S-box vs Midori128's 4 - is fully checked,
    not just the default), its test vectors normalized + filtered to that version's sizes, then
    built and run. Empty {} for a non-versioned spec (the caller uses the single-build result)."""
    results = {}
    versions = getattr(spec, "versions", None)
    if not versions:
        return results
    import io as _io
    from contextlib import redirect_stdout as _rs
    for vname in versions:
        try:
            vspec = spec.instantiate(vname)
            wb, kwb = _effective_word_sizes(vspec)
            vspec.test_vectors = _normalize_test_vectors(
                vspec.test_vectors, vspec.cipher_type, wb, kwb)
            ns, nk = _effective_state_counts(vspec)
            vspec.test_vectors, _ = _drop_cross_variant_vectors(
                vspec.test_vectors, ns, nk, vspec.cipher_type)
            with _rs(_io.StringIO()):
                vcipher = (build_blockcipher_from_spec(vspec) if vspec.cipher_type == "blockcipher"
                           else build_permutation_from_spec(vspec))
                results[vname] = verify_cipher_test_vectors(vcipher, vspec)
        except Exception as exc:
            results[vname] = {"tested": False, "reason": "build_failed", "error": str(exc),
                              "hint": _diagnose_unbuilt_version(spec, vname, str(exc))}
    return results


def key_schedule_needs_bitslicing(spec):
    """Reason string if a block cipher's key schedule cannot be expressed at its word
    granularity, else None.

    Some ciphers (FUTURE) rotate a whole key half by a bit amount that crosses word/cell
    boundaries (5-bit rotation over 4-bit cells). AddRoundKey needs the subkey and state to
    share a word width, so the FULL block cipher can only be modeled bit-sliced (word=1).
    BUT the keyless internal permutation (the data path, no key) is still expressible at word
    level - this is the signal to drop from the L0 full-block-cipher path to the L1 word-level
    permutation path (see build_with_downgrade)."""
    if spec.cipher_type != "blockcipher" or not spec.key_schedule:
        return None
    kwb = spec.key_word_bitsize or spec.word_bitsize
    if not kwb:
        return None
    for idx, layer in enumerate(spec.key_schedule):
        if layer.layer_type in ("rotation", "shift"):
            amt = (layer.params or {}).get("amount")
            if isinstance(amt, int) and not (0 < amt < kwb):
                return (
                    f"key_schedule layer {idx} ('{layer.layer_type}') rotates by {amt} on a "
                    f"{kwb}-bit word, crossing word boundaries. The full block cipher needs "
                    f"bit-sliced (word_bitsize=1) modeling; its keyless internal permutation "
                    f"is still expressible at word level."
                )
    return None


def build_with_downgrade(spec):
    """Build a cipher, degrading gracefully across granularity levels.

    Returns a dict describing what was built:
      - {"level": "L0", "cipher": <block cipher>} when the full block cipher builds at its
        word granularity (AES/SKINNY/GIFT: data and key share a granularity).
      - {"level": "L1", "cipher": <permutation>, "permutation_spec": <spec>,
         "reason": <why the full cipher was not built at word level>} when the key schedule
        crosses word boundaries (FUTURE): the full block cipher is skipped and the keyless
        internal permutation is built at word level instead. Bit-sliced full modeling (L2)
        is a separate, heavier step.
    A permutation spec (no key) always builds directly and is returned as L0.
    """
    if spec.cipher_type == "blockcipher":
        reason = key_schedule_needs_bitslicing(spec)
        if reason:
            perm_spec = spec.to_permutation()
            return {
                "level": "L1",
                "cipher": build_permutation_from_spec(perm_spec),
                "permutation_spec": perm_spec,
                "reason": reason,
            }
        return {"level": "L0", "cipher": build_blockcipher_from_spec(spec)}
    return {"level": "L0", "cipher": build_permutation_from_spec(spec)}


def derive_permutation(block_spec, block_cipher=None, sample_input=None):
    """From a VERIFIED block cipher, build its keyless permutation and CROSS-CHECK it against
    the block cipher run with all-zero keys.

    A cipher like Midori must be modeled bit-level because its key schedule crosses cells, but
    the keyless permutation (round function with the key removed) is the analysis target. This:
      1. Expands the block spec the SAME way the build did (archetype / cell / whitening), so
         round constants and the (now keyless) round function are concrete layers - then drops
         add_round_key + the key schedule. Works for cell_layout / archetype ciphers, which the
         old code silently failed on (it built a broken cell-layers-without-cell_layout spec).
      2. Generates the permutation's KAT by evaluating the VERIFIED BLOCK CIPHER with a zero key
         (an INDEPENDENT reference), not by evaluating the permutation itself.
      3. Builds the permutation and VERIFIES its output equals that reference.
    Returns (perm_spec_with_kat, built_permutation, error_or_None). error is a message string
    when derivation/verification fails - never silently swallowed.
    """
    if block_spec.versions:
        block_spec = block_spec.instantiate(block_spec.default_version or next(iter(block_spec.versions)))

    try:
        import io
        from contextlib import redirect_stdout
        import implementations.implementations as imp
        from tools.paths import get_files_dir

        expanded = block_spec.compile()                  # same canonical lowering chain as build
        bit_perm_spec = expanded.to_permutation()        # always-valid bit-level fallback

        files_dir = get_files_dir()
        files_dir.mkdir(parents=True, exist_ok=True)

        def _run(spec, inputs):
            cipher = build_permutation_from_spec(spec)
            with redirect_stdout(io.StringIO()):
                imp.generate_implementation(cipher, files_dir / f"{cipher.name}.py", "python",
                                            _spec_needs_unroll(spec))
                out = imp.evaluate_python(cipher, inputs)
            return cipher, out

        # independent reference: the verified block cipher with an all-zero key
        if block_cipher is not None and getattr(block_cipher, "test_vectors", None):
            sample_input = [list(block_cipher.test_vectors[0][0][0])]
            zero_key = [0] * len(block_cipher.test_vectors[0][0][1])
            with redirect_stdout(io.StringIO()):
                reference = imp.evaluate_python(block_cipher, [sample_input[0], zero_key])
        else:  # no block cipher to reference: fall back to the perm's own output (regression anchor)
            reference = None

        # Prefer a WORD-LEVEL (cell-granularity) permutation - cleaner for analysis - but only
        # when it reproduces the block cipher EXACTLY; otherwise use the bit-level permutation.
        # The bit sample plaintext is repacked to cells for the word-level model.
        word_spec = block_spec.to_word_permutation() if reference is not None else None
        if word_spec is not None:
            cb = word_spec.word_bitsize
            cells = [int("".join(str(b) for b in sample_input[0][cb * c:cb * c + cb]), 2)
                     for c in range(word_spec.nbr_words)]
            try:
                w_cipher, w_out = _run(word_spec, [cells])
                w_out_bits = [(v >> (cb - 1 - j)) & 1 for v in w_out for j in range(cb)]
                if w_out_bits == reference:
                    word_spec.test_vectors = [[[cells], w_out]]
                    return word_spec, w_cipher, None     # word-level, cross-checked
            except Exception:
                pass                                     # fall through to the bit-level permutation

        if sample_input is None:
            modulus = 1 << bit_perm_spec.word_bitsize
            sample_input = [[(i + 1) % modulus for i in range(bit_perm_spec.nbr_words)]]
        perm_cipher, perm_out = _run(bit_perm_spec, sample_input)
        if reference is None:
            reference = perm_out
    except Exception as exc:
        return None, None, f"{type(exc).__name__}: {exc}"

    if perm_out != reference:
        return bit_perm_spec, perm_cipher, ("permutation output does not match the block cipher "
                                            "with zero keys - the keyless-permutation derivation is wrong")
    bit_perm_spec.test_vectors = [[sample_input, reference]]
    return bit_perm_spec, perm_cipher, None


class _ExportNotApplicable(ValueError):
    """The cipher's shape is not yet supported by the primitive exporter (benign; the
    build still succeeds, just without a persisted stand-alone primitive)."""


def _persist_primitive(export_spec):
    """Write a self-contained OCP primitive file (primitives/<name>.py) and register it in
    files/custom_ciphers.json, returning the primitive's path.

    New S-box classes go to operators/generated_sboxes.py and the generated primitive is
    rewritten to import them from there, so the central, tracked operators/Sbox.py is NEVER
    bloated with per-cipher classes. Raises _ExportNotApplicable when the exporter does not
    support the cipher's shape yet.
    """
    import re
    from pathlib import Path
    import primitives.primitives as _prim_pkg
    import operators.Sbox as _sbox_mod
    from agent.skills.cipher_primitive_export import generate_primitive_source

    try:
        p_filename, p_source, sbox_appends, catalog_entry = generate_primitive_source(export_spec)
    except ValueError as exc:
        raise _ExportNotApplicable(str(exc))

    if sbox_appends:
        new_names = {name for name, _ in sbox_appends}
        gen_path = Path(_sbox_mod.__file__).parent / "generated_sboxes.py"
        header = ('"""Agent-generated S-box classes, kept OUT of the tracked '
                  'operators/Sbox.py."""\nfrom operators.Sbox import Sbox\n')
        current = gen_path.read_text(encoding="utf-8") if gen_path.exists() else header
        additions = "".join(src for name, src in sbox_appends if f"class {name}(" not in current)
        if additions:
            gen_path.write_text(current + additions, encoding="utf-8")

        def _rewrite(match):  # split the import: keep existing, move new ones to the gen module
            names = [n.strip() for n in match.group(1).split(",") if n.strip()]
            keep = [n for n in names if n not in new_names]
            moved = [n for n in names if n in new_names]
            lines = []
            if keep:
                lines.append("from operators.Sbox import " + ", ".join(keep))
            if moved:
                lines.append("from operators.generated_sboxes import " + ", ".join(moved))
            return "\n".join(lines)

        p_source = re.sub(r"from operators\.Sbox import ([^\n]+)", _rewrite, p_source, count=1)

    p_path = Path(_prim_pkg.__file__).parent / p_filename
    p_path.write_text(p_source)

    import json as _json
    import os as _os
    from tools.paths import get_files_dir as _get_files_dir
    reg_path = _get_files_dir() / "custom_ciphers.json"
    registry = {}
    if reg_path.exists():
        try:
            registry = _json.loads(reg_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            registry = {}
    registry.update(catalog_entry)
    # atomic replace: write a temp file then rename, so a crash mid-write never leaves a
    # truncated registry that would break instantiation of ALL custom ciphers.
    tmp = reg_path.with_suffix(".json.tmp")
    tmp.write_text(_json.dumps(registry, indent=1), encoding="utf-8")
    _os.replace(tmp, reg_path)

    # Make the new cipher usable BY NAME in THIS process: the catalog is loaded once at import,
    # so a fresh entry written to disk is invisible until restart unless we also update the
    # in-memory map. invalidate_caches lets a subsequently-written primitive module be imported.
    try:
        import importlib
        import agent.skills.cipher_instantiation as _ci
        for _name, _entry in catalog_entry.items():
            _ci.CIPHER_CATALOG.setdefault(_name, _entry)   # built-ins stay authoritative
        importlib.invalidate_caches()
    except Exception:
        pass
    return str(p_path)


class CipherDefinitionSkill(BaseSkill):
    """Build an OCP cipher from a CipherSpec specification."""

    @property
    def name(self) -> SkillName:
        return SkillName.CIPHER_DEFINITION

    @property
    def description(self) -> str:
        return (
            "Define and build a custom cipher from a structured specification (CipherSpec). "
            "Supports permutations and block ciphers with arbitrary round structures "
            "including S-boxes, rotations, XOR, modular addition, permutations, and matrices."
        )

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "spec": {
                "type": "object",
                "required": True,
                "description": "CipherSpec as a dict. See agent/skills/cipher_spec.py for the full schema.",
            },
        }

    def execute(self, request: SkillRequest, session: Session) -> SkillResult:
        params = request.params

        # Accept spec as dict or from session metadata
        spec_data = params.get("spec")
        if spec_data is None:
            spec_data = session.get_metadata("pending_cipher_spec")

        if spec_data is None:
            return SkillResult(
                success=False,
                skill=self.name,
                error="No cipher specification provided. Pass 'spec' parameter or use cipher_dialogue first.",
            )

        # Build CipherSpec from dict
        if isinstance(spec_data, dict):
            spec = CipherSpec.from_dict(spec_data)
        elif isinstance(spec_data, CipherSpec):
            spec = spec_data
        else:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Invalid spec type: {type(spec_data)}. Expected dict or CipherSpec.",
            )

        # Keep the original (pre-instantiation) spec so we can export a reusable OCP
        # primitive file covering the whole parameterized family, not just one member.
        export_spec = spec

        # If this is a parameterized family (has "versions"), resolve the requested
        # (or default) version into one concrete member before building.
        if spec.versions:
            try:
                spec = spec.instantiate(params.get("version"))
            except (ValueError, KeyError, TypeError) as exc:
                return SkillResult(success=False, skill=self.name,
                                   error=f"Version selection failed: {exc}")
        # The round count is user-specified: a "rounds" param overrides the spec's
        # own default, which is the design's full round count (for a family, the
        # chosen version's nbr_rounds, e.g. KNOT's nr0). Blank/absent keeps that
        # default. Applied before layout expansion, which consumes nbr_rounds.
        user_rounds = params.get("rounds")
        if user_rounds not in (None, "", 0):
            try:
                spec.nbr_rounds = int(user_rounds)
            except (TypeError, ValueError):
                return SkillResult(success=False, skill=self.name,
                                   error=f"Invalid rounds value: {user_rounds!r} (expected a positive integer).")

        # If this is a bit-sliced layout, expand it into a concrete word_bitsize=1 spec.
        if spec.layout:
            try:
                spec = spec.expand_bitsliced()
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                return SkillResult(success=False, skill=self.name,
                                   error=f"Bit-sliced expansion failed: {exc}")

        # Normalize any provided test vectors into the canonical form consumed by
        # verification and code generation. Hex-string fields are split deterministically
        # here (not by the LLM); a malformed hex value is reported, not silently dropped.
        try:
            _wb, _kwb = _effective_word_sizes(spec)
            spec.test_vectors = _normalize_test_vectors(
                spec.test_vectors, spec.cipher_type, _wb, _kwb)
        except ValueError as exc:
            return SkillResult(success=False, skill=self.name,
                               error=f"Test vector parsing failed: {exc}")
        # A family paper's KATs for other variants (Midori128 vectors on a Midori64 build) can
        # never pass this cipher and cannot be repaired (vectors are immutable), so drop them
        # now that the version's word counts are known - keeping only same-variant vectors.
        _ns, _nk = _effective_state_counts(spec)
        spec.test_vectors, _dropped_variant = _drop_cross_variant_vectors(
            spec.test_vectors, _ns, _nk, spec.cipher_type)

        # Validate
        errors = spec.validate()
        if errors:
            return SkillResult(
                success=False,
                skill=self.name,
                error="Cipher specification validation failed:\n" + "\n".join(f"  - {e}" for e in errors),
            )

        # Build the cipher
        try:
            if spec.cipher_type == "permutation":
                cipher = build_permutation_from_spec(spec)
            elif spec.cipher_type == "blockcipher":
                cipher = build_blockcipher_from_spec(spec)
            else:
                return SkillResult(
                    success=False,
                    skill=self.name,
                    error=f"Unsupported cipher_type: {spec.cipher_type}",
                )

            session.set_cipher(cipher)
            session.set_metadata("cipher_spec", spec.to_dict())

            # VERIFY BEFORE PERSISTING. Only a definition whose known-answer tests actually
            # PASS is written to primitives/ or registered in the catalog. A KAT-failing spec,
            # AND one with NO runnable test vectors (none provided, or code generation failed to
            # run them), is NOT persisted - an unverified primitive silently pollutes the
            # built-ins (this is exactly how a broken 'midori' with no MixColumn and no vectors
            # got registered). No verified vectors -> not saved; the summary says to add them.
            verification = verify_cipher_test_vectors(cipher, spec)
            verified = bool(verification.get("all_passed"))

            # Multi-version family: KAT-verify EVERY version (not just the default built above).
            # A version that BUILDS but fails its KAT blocks persistence (a wrong cipher). A version
            # that cannot even BUILD is SPURIOUS/incomplete (e.g. a Midori128 entry carrying
            # Midori64's structure + S-box) - drop it from the exported family rather than block the
            # working versions, as long as the DEFAULT is among the buildable ones. Use export_spec:
            # `spec` was already instantiated to the default (and layout-expanded), losing versions.
            version_results = verify_all_versions(export_spec)
            dropped_versions = {}
            if version_results:
                built = {v: r for v, r in version_results.items() if r.get("tested")}
                dropped_versions = {v: r for v, r in version_results.items() if not r.get("tested")}
                default_ok = (export_spec.default_version in built) if export_spec.default_version else bool(built)
                verified = bool(built) and default_ok and all(r.get("all_passed") for r in built.values())
                if verified and dropped_versions:
                    import copy as _copy
                    export_spec = _copy.deepcopy(export_spec)
                    for v in dropped_versions:
                        export_spec.versions.pop(v, None)

            primitive_file = None
            export_error = None
            if verified:
                try:
                    primitive_file = _persist_primitive(export_spec)
                except _ExportNotApplicable as exc:
                    export_error = f"not applicable: {exc}"      # unsupported shape - benign
                except Exception as exc:                          # surfaced, never swallowed
                    export_error = f"{type(exc).__name__}: {exc}"

            base = (f"Built custom cipher: {cipher.name} ({spec.cipher_type}, "
                    f"{spec.block_size}-bit, {spec.nbr_rounds} rounds, "
                    f"{len(spec.round_structure)} layers/round)")
            if verification.get("tested"):
                if verification["all_passed"]:
                    summary = base + (f" | Verified: {verification['passed']}/{verification['total']} "
                                      f"test vectors passed.")
                else:
                    summary = base + (f" | WARNING: only {verification['passed']}/{verification['total']} "
                                      f"test vectors passed. The definition likely does NOT match the "
                                      f"intended cipher, so it was NOT saved to primitives/ or the "
                                      f"catalog. Review the round structure, word indices, and layer order.")
            elif verification.get("reason") == "codegen_failed":
                summary = base + (f" | Not verified: could not generate a reference implementation "
                                  f"({verification.get('error', '')}), so it was NOT saved to "
                                  f"primitives/ or the catalog.")
            else:
                summary = base + (" | Not verified: no test vectors provided, so it was NOT saved "
                                  "to primitives/ or the catalog. Add test_vectors (known "
                                  "input/output pairs) to confirm the definition and persist it.")
            if version_results:
                # Report each version's KAT so a partially-passing family is clear.
                parts = []
                for vname, r in version_results.items():
                    if r.get("tested"):
                        parts.append(f"{vname} {r.get('passed', 0)}/{r.get('total', 0)}")
                    else:
                        parts.append(f"{vname} not-built ({r.get('reason', '?')})")
                summary += " | Versions: " + ", ".join(parts)
                if verified and dropped_versions:
                    # Name WHY each excluded version failed, in user-actionable terms: the
                    # structural diagnosis when we have one, else the raw build error (truncated),
                    # so the note is never an opaque "could not be built".
                    reasons = []
                    for v, r in dropped_versions.items():
                        why = r.get("hint") or (r.get("error") or "").strip()
                        reasons.append(f"{v}: {why}" if why else v)
                    summary += (" (excluded from the saved family because these versions could not "
                                "be built from this spec - " + "; ".join(reasons)
                                + ". Supply the missing per-version structure via the Editable JSON "
                                "and re-send to include them.)")
                elif not verified:
                    summary += " - NOT saved until the default and all buildable versions pass."
            if export_error and not export_error.startswith("not applicable"):
                summary += f" | NOTE: primitive export failed ({export_error})."

            # After a block cipher verifies, derive its keyless permutation and a
            # known-answer test vector (the block cipher with zero subkeys), so it
            # is ready for differential/linear analysis.
            permutation_info = None
            if spec.cipher_type == "blockcipher" and verification.get("all_passed"):
                perm_spec, perm_cipher, perm_err = derive_permutation(spec, cipher)
                if perm_spec is not None and perm_err is None:
                    session.set_metadata("derived_permutation_spec", perm_spec.to_dict())
                    permutation_info = {
                        "name": perm_cipher.name,
                        "test_vector": perm_spec.test_vectors[0],
                    }
                    summary += (f" | Derived the keyless permutation {perm_cipher.name} and "
                                f"cross-checked it against this cipher with zero keys - its "
                                f"known-answer vector is ready for differential/linear analysis.")
                elif perm_err:
                    summary += f" | Note: could not derive/verify the keyless permutation ({perm_err})."

            if primitive_file:
                summary += f" | Saved OCP primitive definition: {primitive_file}"

            data = {"cipher_name": cipher.name, "type": spec.cipher_type,
                    "rounds": spec.nbr_rounds, "block_size": spec.block_size,
                    "verification": verification}
            # Distinguish the FOUR distinct outcomes the UI used to conflate as "success":
            # built in memory, KAT-verified, exported to primitives/, registered in the catalog.
            data["status"] = {
                "built": True,
                "verified": bool(verification.get("all_passed")),
                "exported": primitive_file is not None,
                "registered": primitive_file is not None,
                "export_error": export_error,
            }
            if permutation_info:
                data["permutation"] = permutation_info
            if primitive_file:
                data["primitive_file"] = primitive_file

            # Attach the generated Python implementation so the UI can show the code for
            # the built cipher. Prefer the UNROLLED form (each round written out) as it is
            # more readable; if unrolled codegen fails (a known OCP issue when a round layer's
            # constant/other table is shorter than nbr_rounds), fall back to the loop form so
            # the displayed file is always COMPLETE rather than truncated mid-write.
            from pathlib import Path as _Path
            impl_path = verification.get("impl_file")
            try:
                from tools.paths import get_files_dir
                import implementations.implementations as _impl
                import io as _io
                from contextlib import redirect_stdout as _redirect
                impl_path = str(get_files_dir() / f"{cipher.name}.py")
                with _redirect(_io.StringIO()):
                    try:
                        _impl.generate_implementation(cipher, impl_path, "python", True)
                    except Exception:
                        _impl.generate_implementation(cipher, impl_path, "python", False)
            except Exception:
                impl_path = verification.get("impl_file")
            if impl_path and _Path(impl_path).exists():
                try:
                    data["implementation"] = {
                        "language": "python",
                        "path": impl_path,
                        "code": _Path(impl_path).read_text(encoding="utf-8"),
                    }
                except OSError:
                    pass

            return SkillResult(
                success=True,
                skill=self.name,
                data=data,
                summary=summary,
            )
        except (KeyError, ValueError, RuntimeError, OSError) as e:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Failed to build cipher: {e}",
            )
        except Exception as e:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Unexpected cipher definition failure: {e}",
            )
