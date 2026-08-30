"""Data model for describing custom cipher algorithms.

A CipherSpec fully describes a cipher's structure in a way that can be:
1. Constructed from natural language via LLM dialogue
2. Written as JSON/dict by the user directly
3. Used to dynamically build an OCP Primitive object

Example - SPECK32 as a CipherSpec:
    spec = CipherSpec(
        name="MySpeck32",
        cipher_type="permutation",
        block_size=32,
        word_bitsize=16,
        nbr_words=2,
        nbr_rounds=22,
        round_structure=[
            LayerSpec("rotation", {"direction": "r", "amount": 7, "word_index": 0}),
            LayerSpec("modadd", {"input_indices": [[0, 1]], "output_indices": [0]}),
            LayerSpec("rotation", {"direction": "l", "amount": 2, "word_index": 1}),
            LayerSpec("xor", {"input_indices": [[0, 1]], "output_indices": [1]}),
        ],
    )
"""

import ast
import operator
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


_ARITH_BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}


def _safe_arith(expr):
    """Evaluate a pure-arithmetic expression (numbers and + - * / // % ** with
    parentheses only). Returns the numeric result, or None if `expr` contains
    anything else (names, calls, attributes). No eval(); a restricted AST walk.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return None

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _ARITH_BINOPS:
            return _ARITH_BINOPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            operand = _eval(node.operand)
            return -operand if isinstance(node.op, ast.USub) else operand
        raise ValueError("unsupported expression")

    try:
        return _eval(tree)
    except (ValueError, ZeroDivisionError, TypeError):
        return None


_SAFE_BINOPS = {
    ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
    ast.FloorDiv: lambda a, b: a // b, ast.Mod: lambda a, b: a % b, ast.Pow: lambda a, b: a ** b,
    ast.Div: lambda a, b: a // b if b else 0,
    ast.LShift: lambda a, b: a << b, ast.RShift: lambda a, b: a >> b,
    ast.BitOr: lambda a, b: a | b, ast.BitAnd: lambda a, b: a & b, ast.BitXor: lambda a, b: a ^ b,
}
_SAFE_CMP = {
    ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b,
}
def _rol(x, n, w):
    """Rotate the w-bit value x left by n bits (bit 0 = LSB). For a reference cipher's ARX."""
    n %= w
    return ((x << n) | (x >> (w - n))) & ((1 << w) - 1) if n else x & ((1 << w) - 1)


def _ror(x, n, w):
    """Rotate the w-bit value x right by n bits."""
    n %= w
    return ((x >> n) | (x << (w - n))) & ((1 << w) - 1) if n else x & ((1 << w) - 1)


def _gf_mul(a, b, poly, bits):
    """Multiply a*b in GF(2^bits) modulo `poly` (FULL polynomial incl. top term: GF(2^4) x^4+x+1
    -> 0x13, AES GF(2^8) -> 0x11B). For a reference cipher's MixColumn/GF matrix."""
    res, mask, top = 0, (1 << bits) - 1, 1 << (bits - 1)
    for _ in range(bits):
        if b & 1:
            res ^= a
        b >>= 1
        hi = a & top
        a = (a << 1) & mask
        if hi:
            a ^= poly & mask
    return res


_SAFE_CALLS = {"range": range, "len": len, "int": int, "min": min, "max": max, "abs": abs,
               "list": list, "sum": sum, "pow": pow,
               # cipher-common arithmetic helpers so a straight-line reference need not inline the
               # error-prone parts (ARX rotations, GF(2^n) MixColumn multiply):
               "rol": _rol, "ror": _ror, "gf_mul": _gf_mul}


def safe_eval_program(code, env=None, max_steps=2_000_000, max_len=200_000):
    """Run a SMALL, restricted Python program (e.g. an LLM-supplied round-constant computation)
    and return its `result` variable - so a cipher can DERIVE a constant table from the paper's
    RULE (pi hex, an LFSR, a counter) instead of hand-copying it. Verified afterward by the KAT.

    Whitelisted AST only: int arithmetic + bit ops (>> << & | ^ ~), comparisons, and/or/not,
    for-over-range/list, if, list/tuple literals and comprehensions, subscripting, local
    assignment, ternary, and the builtins range/len/int/min/max/abs/list/sum/pow. NO imports,
    attributes, f-strings, while, def/lambda, or any other call. A step/length budget bounds it.
    Returns None on any violation or error (the caller falls back / the KAT catches a wrong result).
    """
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError:
        return None
    ns = dict(env or {})
    steps = [0]

    def tick():
        steps[0] += 1
        if steps[0] > max_steps:
            raise ValueError("step budget exceeded")

    def ev(node):
        tick()
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, bool, str)):
            return node.value                       # str allowed for dict keys/labels ({"from": ..})
        if isinstance(node, ast.Name):
            if node.id in ns:
                return ns[node.id]
            raise ValueError(f"unknown name {node.id}")
        if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_BINOPS:
            r = _SAFE_BINOPS[type(node.op)](ev(node.left), ev(node.right))
            if isinstance(r, (str, list)) and len(r) > max_len:  # bound "a"*huge / list growth
                raise ValueError("value too large")
            return r
        if isinstance(node, ast.UnaryOp):
            v = ev(node.operand)
            if isinstance(node.op, ast.USub):
                return -v
            if isinstance(node.op, ast.UAdd):
                return v
            if isinstance(node.op, ast.Invert):
                return ~v
            if isinstance(node.op, ast.Not):
                return not v
        if isinstance(node, ast.BoolOp):
            vals = [ev(v) for v in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _SAFE_CMP:
            return _SAFE_CMP[type(node.ops[0])](ev(node.left), ev(node.comparators[0]))
        if isinstance(node, ast.IfExp):
            return ev(node.body) if ev(node.test) else ev(node.orelse)
        if isinstance(node, (ast.List, ast.Tuple)):
            out = [ev(e) for e in node.elts]
            if len(out) > max_len:
                raise ValueError("list too large")
            return out if isinstance(node, ast.List) else tuple(out)
        if isinstance(node, ast.Dict):                # for structure entries like {"from": r, "words": [..]}
            return {ev(k): ev(v) for k, v in zip(node.keys, node.values)}
        if isinstance(node, ast.Subscript):
            return ev(node.value)[ev(node.slice)]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _SAFE_CALLS:
            if node.keywords:
                raise ValueError("keyword args not allowed")
            return _SAFE_CALLS[node.func.id](*[ev(a) for a in node.args])
        # Narrow method whitelist: list.append/extend only (so `result.append(row)` works),
        # never arbitrary attributes (no __class__, no imports).
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("append", "extend") and not node.keywords):
            obj = ev(node.func.value)
            if not isinstance(obj, list):
                raise ValueError("append/extend only on lists")
            args = [ev(a) for a in node.args]
            if node.func.attr == "append":
                obj.append(*args)
            else:
                obj.extend(*args)
            if len(obj) > max_len:
                raise ValueError("list too large")
            return None
        if isinstance(node, ast.ListComp) and len(node.generators) == 1:
            gen = node.generators[0]
            if gen.is_async or not isinstance(gen.target, ast.Name):
                raise ValueError("bad comprehension")
            out = []
            for item in ev(gen.iter):
                tick()
                ns[gen.target.id] = item
                if all(ev(c) for c in gen.ifs):
                    out.append(ev(node.elt))
                    if len(out) > max_len:
                        raise ValueError("list too large")
            return out
        raise ValueError(f"unsupported expression {type(node).__name__}")

    def _assign_target(target, value):
        if isinstance(target, ast.Name):
            ns[target.id] = value
        elif isinstance(target, ast.Subscript):
            ev(target.value)[ev(target.slice)] = value
        else:
            raise ValueError("unsupported assignment target")

    def run(stmts):
        for st in stmts:
            tick()
            if isinstance(st, ast.Assign):
                v = ev(st.value)
                for t in st.targets:
                    _assign_target(t, v)
            elif isinstance(st, ast.AugAssign):
                cur = ev(st.target if isinstance(st.target, (ast.Name, ast.Subscript)) else st.target)
                _assign_target(st.target, _SAFE_BINOPS[type(st.op)](cur, ev(st.value)))
            elif isinstance(st, ast.For):
                if not isinstance(st.target, ast.Name):
                    raise ValueError("for-target must be a name")
                for item in ev(st.iter):
                    tick()
                    ns[st.target.id] = item
                    run(st.body)
            elif isinstance(st, ast.If):
                run(st.body if ev(st.test) else st.orelse)
            elif isinstance(st, ast.Expr):
                ev(st.value)                    # evaluate for side effects (e.g. result.append(...))
            elif isinstance(st, ast.Pass):
                continue
            else:
                raise ValueError(f"unsupported statement {type(st).__name__}")

    try:
        run(tree.body)
    except (ValueError, KeyError, IndexError, TypeError, ZeroDivisionError, RecursionError):
        return None
    return ns.get("result")


def run_reference(code, plaintext, key=None):
    """Run an LLM-supplied STRAIGHT-LINE reference cipher in the sandbox, for Tier-1b's oracle.

    The reference reads `plaintext` and `key` (word lists) from the environment and sets
        result = {"output": [ciphertext words], "trace": [[state after round 1], ...]}
    (a bare `result = [ciphertext]` with no trace is also accepted). It may call the sandbox
    helpers rol/ror/gf_mul. Returns (output_words, trace_or_None), or (None, None) if it did not
    produce a usable output (the caller then knows the reference itself failed - a paper-
    UNDERSTANDING problem, distinct from an OCP-encoding one).
    """
    env = {"plaintext": list(plaintext), "key": list(key or [])}
    res = safe_eval_program(code, env=env)
    if isinstance(res, dict) and isinstance(res.get("output"), list):
        trace = res.get("trace")
        return list(res["output"]), (trace if isinstance(trace, list) else None)
    if isinstance(res, list):
        return list(res), None
    return None, None


def _sanitize_identifier(name, fallback="Cipher"):
    """Reduce a name to a valid Python identifier. The cipher name becomes the
    generated implementation's function/file name, so version keys or user names
    with dashes, parentheses, or commas (e.g. "KNOT-AEAD(128,256,64)") would emit
    invalid Python. Keep [A-Za-z0-9_], collapse other runs to a single '_', trim,
    and prefix if it would start with a digit.
    """
    cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", str(name)).strip("_")
    if not cleaned:
        cleaned = fallback
    if cleaned[0].isdigit():
        cleaned = "C_" + cleaned
    return cleaned


def _lfsr_constants(lfsr, count):
    """Generate `count` states from an LFSR spec {width, taps, init, mode, direction}.

    LFSR conventions vary between ciphers, so all the common ones are supported:
      mode="fibonacci" (default): the feedback bit is the XOR of the state bits at
          `taps`, shifted into the vacated end.
      mode="galois": the state is shifted and, when the bit shifted out is 1, XORed
          with the tap polynomial (OR of 1<<t for t in taps).
      direction="left" (default) shifts toward the MSB; "right" toward the LSB.

    Because a wrong convention is easy to pick, when a paper or reference gives the
    actual constants prefer supplying them directly (see _round_constant_values);
    the LFSR here is only a generator and its convention must match the cipher.
    """
    width = lfsr["width"]
    taps = lfsr["taps"]
    state = lfsr.get("init", 1)
    mode = lfsr.get("mode", "fibonacci")
    direction = lfsr.get("direction", "left")
    mask = (1 << width) - 1
    polynomial = 0
    for tap in taps:
        polynomial |= 1 << tap
    sequence = []
    for _ in range(count):
        sequence.append(state & mask)
        if mode == "galois":
            if direction == "left":
                carry = (state >> (width - 1)) & 1
                state = (state << 1) & mask
            else:
                carry = state & 1
                state >>= 1
            if carry:
                state ^= polynomial
        else:  # fibonacci
            feedback = 0
            for tap in taps:
                feedback ^= (state >> tap) & 1
            if direction == "left":
                state = ((state << 1) | feedback) & mask
            else:
                state = ((state >> 1) | (feedback << (width - 1))) & mask
    return sequence


def _round_constant_values(rc, count):
    """Resolve `count` round-constant integer values from a round-constant spec,
    most reliable source first:
      1. {"constants": [c0, c1, ...]} - an explicit sequence (e.g. a table copied
         from the paper or reference implementation); used directly, cycled if
         shorter than `count`. This is the safest option - it avoids all
         LFSR-convention ambiguity.
      2. {"lfsr": {...}} - generated by _lfsr_constants.
      3. {"code": "..."} - a small LLM-supplied program that computes `result`, a list of
         `count` integers, run in the restricted sandbox (safe_eval_program) with `count`/
         `nbr_rounds` in scope. Lets the model DERIVE constants from the paper's rule (SIMON's
         z-sequence, a counter, pi bits) instead of copying them; the KAT is the safety net.
      4. neither - all zeros (round constants do not affect differential/linear
         analysis, so zeros are a safe default when the values are unknown).
    """
    if isinstance(rc, dict):
        constants = rc.get("constants")
        if constants:
            return [constants[i % len(constants)] for i in range(count)]
        if rc.get("code"):
            seq = safe_eval_program(rc["code"], {"count": count, "nbr_rounds": count})
            if isinstance(seq, list) and seq and all(isinstance(x, int) for x in seq):
                return [seq[i % len(seq)] for i in range(count)]
        if rc.get("lfsr"):
            return _lfsr_constants(rc["lfsr"], count)
    return [0] * count


# Fractional hex of pi (verified against the Midori64/128 designer test vectors).
_PI_FRAC_HEX = "243f6a8885a308d313198a2e03707344a4093822299f31d0082efa98ec4e6c89452821e638d0"


def pi_round_constant_cells(count):
    """Midori-style round constants generator: alpha_i is a 4x4 binary matrix read from
    four consecutive hex digits of the fractional part of pi, XORed to the LSB of each of
    the 16 cells. Row j of alpha_i is a hex digit; bit (msb = column 0) at (row j, col)
    hits cell 4*col + j (column-major). Returns `count` rows of 16 values in {0, 1}.

    This lets a spec declare round constants as {"source": "pi_hex", "count": N} instead
    of hand-copying the table (the error-prone part of extracting Midori-like ciphers).
    Verified: rows 0..14 reproduce Midori64's alpha_i, rows 0..18 reproduce Midori128's.
    """
    if count * 4 > len(_PI_FRAC_HEX):
        raise ValueError(f"pi_hex round constants are only defined up to {len(_PI_FRAC_HEX) // 4}")
    rows = []
    for i in range(count):
        digits = _PI_FRAC_HEX[4 * i:4 * i + 4]
        cells = [0] * 16
        for row in range(4):
            v = int(digits[row], 16)
            for col in range(4):
                cells[4 * col + row] = (v >> (3 - col)) & 1
        rows.append(cells)
    return rows


def _resolve_placeholders(value, params):
    """Recursively replace "$name" placeholders in a params value with params[name].

    Used to instantiate a version-parameterized family: round-structure params can
    reference per-version values (e.g. rotation amount "$rot0") that a chosen
    version fills in. A lone "$name" returns the param value with its type intact
    (so "$taps" can resolve to a list); a placeholder inside an arithmetic
    expression (e.g. cols "$b/4") is substituted and safely evaluated to a number.
    """
    if isinstance(value, str):
        stripped = value.strip()
        match = re.fullmatch(r"\$(\w+)", stripped)
        if match and match.group(1) in params:
            return params[match.group(1)]
        # Arithmetic on placeholders, e.g. "$b/4" or "$b/2 - 1": substitute every
        # known $name with its (numeric) value, then evaluate if the result is a
        # pure-arithmetic expression. Integral results are returned as int.
        if "$" in stripped:
            substituted = re.sub(
                r"\$(\w+)",
                lambda m: str(params[m.group(1)]) if m.group(1) in params else m.group(0),
                stripped,
            )
            if "$" not in substituted:
                result = _safe_arith(substituted)
                if result is not None:
                    if isinstance(result, float) and result.is_integer():
                        return int(result)
                    return result
        return value
    if isinstance(value, list):
        return [_resolve_placeholders(item, params) for item in value]
    if isinstance(value, dict):
        return {key: _resolve_placeholders(val, params) for key, val in value.items()}
    return value


@dataclass
class LayerSpec:
    """Specification of a single layer in a cipher round.

    Supported layer_type values and their params:

    "sbox":
        sbox_name: str - key into CipherSpec.sbox_tables
        index: List[List[int]] - grouping of word indices for S-box application
            e.g., [[0,1,2,3],[4,5,6,7]] applies 4-bit S-box to words 0-3, then 4-7
        mask: Optional[List[int]] - which groups to apply (1) vs identity (0)

    "permutation":
        table: List[int] - permutation mapping (output[j] = input[table[j]])

    "rotation":
        direction: str - "l" (left) or "r" (right)
        amount: int - rotation amount in bits
        word_index: int - which word to rotate
        out_index: Optional[int] - output position (defaults to word_index)

    "shift":
        direction: str - "l" (left) or "r" (right)
        amount: int - shift amount in bits (bits shifted out are lost; not bijective)
        word_index: int - which word to shift
        out_index: Optional[int] - output position (defaults to word_index)

    "xor" / "and" / "or":
        input_indices: List[List[int]] - groups of input word indices
        output_indices: List[int] - output word indices
        e.g., input_indices=[[0,1]], output_indices=[1] means w1 = XOR(w0, w1)

    "not":
        input_indices: List[List[int]] - single-word groups
        output_indices: List[int] - output word indices
        e.g., input_indices=[[0]], output_indices=[0] means w0 = NOT(w0)

    "n_xor":
        input_indices: List[List[int]] - one group of any number of input words
        output_indices: List[int] - output word index
        e.g., input_indices=[[0,1,2]], output_indices=[3] means w3 = w0 ^ w1 ^ w2

    "andxor":
        input_indices: List[List[int]] - one 3-word group (in0, in1, in2)
        output_indices: List[int] - output word index
        e.g., input_indices=[[0,1,2]], output_indices=[3] means w3 = (w0 & w1) ^ w2

    "modadd":
        input_indices: List[List[int]] - groups of input word indices
        output_indices: List[int] - output word indices
        e.g., input_indices=[[0,1]], output_indices=[0] means w0 = (w0 + w1) mod 2^n

    "matrix":
        matrix: List[List[int]] - square matrix for multiplication
        indices: List[List[int]] - groups of word indices to apply matrix to
        polynomial: Optional[int] - irreducible polynomial for GF(2^n)

    "add_round_key":
        operator: str - "xor" or "modadd"
        mask: Optional[List[int]] - which words get key addition (1) vs identity (0)

    "add_constant":
        add_type: str - "xor" or "modadd"
        constant_mask: List - which words receive constants (True/None)
        constant_table: List[List[int]] - per-round constant values

    "equal":
        input_indices: List[List[int]] - single-word groups (source word)
        output_indices: List[int] - output word indices
        Copies a word unchanged (out = in); used to save a word for an ARX feed-forward.

    "gf2_linear":
        matrix: List[List[int]] - a word_bitsize x word_bitsize binary (GF(2)) matrix
        index_in: List[int] - words the matrix is applied to (bit-level, e.g. a tweakey LFSR)
        index_out: Optional[List[int]] - output words (defaults to index_in, in place)
        constants: Optional - per-word constant added after the linear map
        For a BIT-level LFSR over a word's bits (SKINNY/Deoxys tweakey), NOT a GF(2^n)
        word-diffusion matrix (that is "matrix").

    "add_identity":
        (no params) - an explicit do-nothing layer that fills a layer slot. Prefer
        only_rounds/except_rounds, which insert identities automatically.

    "aes_round":
        input_indices: List[List[int]] - groups of exactly 16 word positions (each a
            128-bit AES state as 16 bytes)
        output_indices: List[List[int]] - matching 16-word output groups
        A whole AES round (SubBytes + ShiftRows + MixColumns, NO key) as one fused
        operator - used by AES-based designs like Rocca. AddRoundKey, if any, is a
        separate add_round_key/xor layer.
    """

    layer_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    # Round-relative activity, for layers that run in only SOME rounds (e.g. AES omits
    # MixColumns in the last round; LED adds the round key every 4th round). In rounds
    # where the layer is inactive an identity layer fills its slot, so every round keeps
    # the same number of layers. Both are 1-based round lists; negative counts from the
    # end (-1 == last round). None = active in every round.
    only_rounds: Optional[List[int]] = None
    except_rounds: Optional[List[int]] = None
    # Round-dependent PARAMS (general): when set, round r uses phase_params[(r-1) % period]
    # as this layer's params instead of `params`. This expresses a layer whose indices cycle
    # with a period - e.g. ChaCha's column/diagonal quarters (period 2), Forro's 8 subround
    # selections. `params` holds phase 0 (so a phase-unaware reader still sees a valid layer).
    phase_params: Optional[List[Dict[str, Any]]] = None

    def is_active(self, round_number: int, nbr_rounds: int) -> bool:
        """Whether this layer runs (vs. an identity placeholder) in `round_number`."""
        def _resolve(rounds):
            return {(r if r > 0 else nbr_rounds + 1 + r) for r in rounds}
        if self.only_rounds is not None:
            return round_number in _resolve(self.only_rounds)
        if self.except_rounds is not None:
            return round_number not in _resolve(self.except_rounds)
        return True

    def for_round(self, round_number: int) -> "LayerSpec":
        """This layer with its params resolved for `round_number` (picks the phase when
        phase_params is set). Returns self when there is no round-dependence."""
        if not self.phase_params:
            return self
        phase = self.phase_params[(round_number - 1) % len(self.phase_params)]
        return LayerSpec(self.layer_type, phase, self.only_rounds, self.except_rounds)

    def to_dict(self):
        d = {"layer_type": self.layer_type, "params": self.params}
        if self.only_rounds is not None:
            d["only_rounds"] = self.only_rounds
        if self.except_rounds is not None:
            d["except_rounds"] = self.except_rounds
        if self.phase_params is not None:
            d["phase_params"] = self.phase_params
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(layer_type=d["layer_type"], params=d.get("params", {}),
                   only_rounds=d.get("only_rounds"), except_rounds=d.get("except_rounds"),
                   phase_params=d.get("phase_params"))


@dataclass
class CipherSpec:
    """Complete specification of a cipher algorithm.

    This dataclass captures everything needed to dynamically build an OCP Primitive.
    """

    # Basic parameters
    name: str = "CustomCipher"
    cipher_type: str = "permutation"  # "permutation" or "blockcipher"
    block_size: int = 64
    word_bitsize: int = 32
    nbr_words: int = 2
    nbr_rounds: int = 16
    nbr_temp_words: int = 0

    # Round structure (applied identically each round)
    round_structure: List[LayerSpec] = field(default_factory=list)

    # Block cipher key parameters (only if cipher_type == "blockcipher")
    key_size: Optional[int] = None
    key_word_bitsize: Optional[int] = None
    key_nbr_words: Optional[int] = None
    key_nbr_temp_words: int = 0
    key_nbr_rounds: Optional[int] = None  # key-schedule rounds if != cipher rounds (Simon)
    key_schedule: Optional[List[LayerSpec]] = None  # layers per key round
    key_extract_indices: Optional[List[int]] = None  # which key words form the subkey

    # S-box tables: name -> lookup table
    sbox_tables: Dict[str, List[int]] = field(default_factory=dict)

    # Test vectors: list of ([inputs], outputs)
    test_vectors: Optional[list] = None

    # Parameterized family (like AES/SPECK/SIMON's version parameter): each version
    # supplies scalar overrides (block_size, word_bitsize, nbr_rounds, ...) and a
    # "params" dict whose values fill "$name" placeholders in round_structure.
    # instantiate(version) resolves this into one concrete member.
    versions: Optional[Dict[str, Any]] = None
    default_version: Optional[str] = None

    # Bit-sliced layout (PRESENT/GIFT/KNOT/RECTANGLE class): the state is a
    # rows x cols bit array. When set, expand_bitsliced() turns high-level layers
    # (subcolumn_sbox, shift_rows, add_round_constant with an lfsr) into a concrete
    # word_bitsize=1 CipherSpec (S-box index groups, bit-permutation, RC table).
    layout: Optional[Dict[str, Any]] = None

    # Cell-sliced layout (FUTURE / AES-in-bits class): the state is nbr_cells cells of
    # cell_bits bits each. When set, expand_cell_sliced() turns high-level CELL layers
    # (subcell_sbox, mixcolumn with a GF(2^cell_bits) integer matrix, cell_shiftrow) into
    # concrete word_bitsize=1 layers, deriving the bit-level S-box groups, the GF(2)
    # MixColumn bit-matrix and the ShiftRow bit-permutation. Use this instead of `layout`
    # when the diffusion is a GF(2^n) matrix over cells (not a per-row rotation like KNOT).
    # The key schedule stays at bit level (give it directly, with bit_rotation_perm helpers).
    cell_layout: Optional[Dict[str, Any]] = None

    # Whitening key additions OUTSIDE the round function: an AddRoundKey before the first
    # round (pre) and/or after the last round (post). PRESENT (post) and FUTURE (pre) do
    # this. OCP's "one subkey per round" model has no round-external slot, so expand_whitening()
    # models each as one extra round whose non-AddRoundKey layers are identity - the user keeps
    # the paper's real round count and need not hand-write that extra round.
    pre_whitening: bool = False
    post_whitening: bool = False

    # Declarative key-schedule archetype. When set, expand_key_archetype() lowers it into a
    # concrete key handling so the LLM declares the schedule in a few fields instead of
    # hand-writing the per-round extraction/evolution (the part it gets wrong). Two types:
    #
    # "static_alternating" (Midori / LED family - a FIXED key). Shape:
    #   {"type": "static_alternating", "shares": 2, "whitening": "xor_shares",
    #    "round_constants": {"source": "pi_hex", "count": 15}}
    # - shares: split the key into N equal shares; the round key alternates through them
    #   (shares=1 = one fixed key, e.g. Midori128). shares must divide key_nbr_words.
    # - whitening: "xor_shares" (WK = XOR of the two shares, Midori64), "whole_key" /
    #   "first_share" (WK = share 0, Midori128), or "none". Applied before round 1 and after
    #   the last round.
    # - round_constants: {"source": "pi_hex", "count": N} -> pi_round_constant_cells(N), or
    #   {"source": "table", "table": [[...16...], ...]} for an explicit table, or omit.
    # round_structure carries ONLY the data path (SubCell/Shuffle/Mix, no key add); this
    # archetype injects the AddRoundKey (key-add first) and the round constants, and applies
    # the MidoriCore layout (the final round applies only the first data-path layer).
    #
    # "tweakey_lfsr" (SKINNY / Deoxys tweakey - an EVOLVING key). Shape:
    #   {"type": "tweakey_lfsr", "branches": 3, "cells_per_branch": 16, "subkey_cells": 8,
    #    "permutation": [9,15,8,...], "lfsr_matrices": [null, mat_TK2, mat_TK3]}
    # - branches: number of parallel tweakey branches TK1..TKz; branches*cells_per_branch
    #   must equal key_nbr_words (the tweak is concatenated into the key state).
    # - cells_per_branch: cells in one branch (usually nbr_words); permutation is a
    #   cells_per_branch-length cell permutation applied per branch (default = SKINNY P_T).
    # - lfsr_matrices: one per branch, a per-cell GF(2) bit matrix (word_bitsize x
    #   word_bitsize) or null for no LFSR (TK1). subkey_cells (top cells) are extracted from
    #   each branch and XORed together (N_XOR for 3 branches) to form the round subkey.
    # Unlike static_alternating this does NOT emit the round add_round_key: SKINNY adds the
    # subkey mid-round, so round_structure MUST keep its own add_round_key at that position.
    key_archetype: Optional[Dict[str, Any]] = None

    # ARX permutation family (ChaCha / Salsa / Forro / BLAKE-like). expand_arx() lowers this
    # into concrete modadd/xor/rotation layers so the LLM declares the (sub)round ONCE instead
    # of hand-wiring 12*nbr_rounds index layers. Shape:
    #   {"word_bitsize": 32, "nbr_words": 16, "temp_per_lane": 0,
    #    "selections": [ [[0,4,8,12],[1,5,9,13],[2,6,10,14],[3,7,11,15]],   # phase 0 (columns)
    #                    [[0,5,10,15],[1,6,11,12],[2,7,8,13],[3,4,9,14]] ], # phase 1 (diagonals)
    #    "ops": [ {"op":"modadd","in":[0,1],"out":0}, {"op":"xor","in":[0,3],"out":3},
    #             {"op":"rotl","in":[3],"out":3,"amount":16}, ... ],        # ONE (sub)round
    #    "feedforward": false}
    # - selections is a PERIODIC list of selection-sets; round r uses selections[(r-1) % period]
    #   (ChaCha alternates 2, Forro cycles 8). Each set is a list of equal-length "lane" tuples;
    #   every op is applied to all lanes in parallel as one layer (using phase_params).
    # - op positions index INTO the lane tuple; {"temp": k} is per-lane scratch (Salsa's a+d).
    # - feedforward (keystream variant) adds the initial state back at the end.
    arx: Optional[Dict[str, Any]] = None

    def expand_linear_diffusion(self) -> "CipherSpec":
        """Lower every `linear_diffusion` round layer into a concrete bit-level `n_xor` layer.

        A linear_diffusion layer is a CIRCULANT rotate-and-XOR over a `shape` = [n_groups,
        group_size] state (bit-sliced, word=1, widx(g,e) = g*group_size + e): each element
        (g,e) becomes the XOR of itself and copies shifted by each `tap` along one `axis`
        ("within" = rotate inside a group / over group_size, "across" = rotate the group index /
        over n_groups). `taps` is a flat list (uniform) or one list per group. This compactly
        expresses ASCON's Sigma (axis "within", per-row taps) and SPEEDY's MixColumn (axis
        "across", uniform taps) without the LLM hand-writing hundreds of n_xor index tuples.
        """
        if not any(l.layer_type == "linear_diffusion" for l in (self.round_structure or [])):
            return self
        import copy

        def lower(p):
            ng, gs = p["shape"]
            axis = p.get("axis", "within")
            sign = -1 if p.get("direction", "l") == "l" else 1
            taps = p["taps"]
            per_group = bool(taps) and isinstance(taps[0], list)

            def widx(g, e):
                return g * gs + e

            def shifted(g, e, t):
                if axis == "within":
                    return widx(g, (e + sign * t) % gs)
                return widx((g + sign * t) % ng, e)

            groups, outs = [], []
            for g in range(ng):
                tg = taps[g] if per_group else taps
                for e in range(gs):
                    groups.append([shifted(g, e, t) for t in [0] + list(tg)])
                    outs.append(widx(g, e))
            return {"input_indices": groups, "output_indices": outs}

        new = copy.deepcopy(self)
        new.round_structure = [
            LayerSpec("n_xor", lower(l.params), l.only_rounds, l.except_rounds)
            if l.layer_type == "linear_diffusion" else l
            for l in self.round_structure
        ]
        return new

    def expand_key_bit_rotations(self) -> "CipherSpec":
        """Lower a declarative key_schedule "bit_rotation" layer into a concrete bit PERMUTATION.

        A FUTURE/LED-class cipher rotates its bit-level key register (or a HALF of it) by a BIT
        amount each round - the rotation crosses cell boundaries, so it is not a word/cell
        rotation. Instead of the LLM hand-writing the 128-entry permutation table, it declares
        {"layer_type": "bit_rotation", "params": {"amount": A, "direction": "l"|"r",
        "start": S (default 0), "width": W (default the whole key register)}} and this generates
        the table: bits [S, S+W) rotate by A, the rest stay in place. FUTURE-64's schedule is
        exactly two of these - {amount:64} (swap the two 64-bit halves) and {amount:5, width:64}
        (rotate the low half by 5). Only applied for a BIT-LEVEL key (key_word_bitsize == 1); left
        untouched otherwise so validate reports the size mismatch.
        """
        ks = self.key_schedule or []
        if not any(getattr(l, "layer_type", None) == "bit_rotation" for l in ks):
            return self
        if (self.key_word_bitsize or self.word_bitsize) != 1:
            return self  # not bit-level; leave it for validate to flag
        import copy
        total = self.key_nbr_words
        new = copy.deepcopy(self)
        new_ks = []
        for l in ks:
            if l.layer_type == "bit_rotation":
                amt = int(l.params.get("amount", 0))
                left = str(l.params.get("direction", "l")).lower() not in ("r", "right")
                start = int(l.params.get("start", 0))
                width = int(l.params.get("width", total))
                sign = 1 if left else -1
                table = list(range(total))          # identity outside the rotated window
                for j in range(width):               # new[start+j] <- old[start + (j +/- amt) % width]
                    table[start + j] = start + (j + sign * amt) % width
                new_ks.append(LayerSpec("permutation", {"table": table}, l.only_rounds, l.except_rounds))
            else:
                new_ks.append(l)
        new.key_schedule = new_ks
        return new

    @staticmethod
    def _is_code_param(v):
        """A {"code": "..."} (optionally with "count") value: an LLM program to run in the
        sandbox. The tight key-set keeps it from matching {"xor":...}/{"from":...} entries."""
        return isinstance(v, dict) and "code" in v and set(v) <= {"code", "count"}

    def _has_code_params(self) -> bool:
        if self._is_code_param(self.key_extract_indices):
            return True
        return any(self._is_code_param(v)
                   for l in (list(self.round_structure or []) + list(self.key_schedule or []))
                   for v in (l.params or {}).values())

    def resolve_code_params(self) -> "CipherSpec":
        """Materialize any {"code": "..."} STRUCTURE param by running the LLM-supplied program
        in the sandbox (safe_eval_program). Generalizes the code escape hatch from constants to
        structure: key_extract_indices and any layer param (index / table / indices /
        input_indices / ...) may be a program returning the concrete list, so a cipher whose
        structure follows a RULE (Simon's per-round key reach-back, a regular permutation) need
        not hand-list dozens of entries. The KAT verifies the produced structure.
        """
        if not self._has_code_params():
            return self
        import copy
        base_env = {k: v for k, v in {
            "nbr_rounds": self.nbr_rounds, "count": self.nbr_rounds,
            "nbr_words": self.nbr_words, "nbr_temp_words": self.nbr_temp_words,
            "word_bitsize": self.word_bitsize, "block_size": self.block_size,
            "key_nbr_words": self.key_nbr_words, "key_word_bitsize": self.key_word_bitsize,
            "key_size": self.key_size,
        }.items() if isinstance(v, int)}

        def run(v, what):
            env = dict(base_env)
            if isinstance(v.get("count"), int):
                env["count"] = v["count"]
            out = safe_eval_program(v["code"], env)
            if not isinstance(out, list):
                raise ValueError(
                    f"{what} code must return a list `result` (got {type(out).__name__}); "
                    f"the sandbox rejected it or it did not set `result`.")
            return out

        new = copy.deepcopy(self)
        if self._is_code_param(new.key_extract_indices):
            new.key_extract_indices = run(new.key_extract_indices, "key_extract_indices")
        for lyr in (list(new.round_structure or []) + list(new.key_schedule or [])):
            params = lyr.params or {}
            for k, v in list(params.items()):
                if self._is_code_param(v):
                    params[k] = run(v, f"layer '{lyr.layer_type}' param '{k}'")
        return new

    def compile(self) -> "CipherSpec":
        """The ONE canonical lowering chain, shared by build_permutation/blockcipher and the
        primitive exporter so they can never drift: resolve {"code"} structure params, then lower
        every declarative representation (ARX / key archetype / linear_diffusion / cell layout /
        whitening) to concrete layers. Each step is a no-op when not applicable, so a single
        order serves both permutations (ARX, no key) and block ciphers (archetype/whitening, no
        ARX). Instantiate a versioned family and apply any rounds override BEFORE calling this;
        a bit-sliced `layout` is expanded separately (expand_bitsliced) as its own family.
        """
        return (self.resolve_code_params()
                .expand_arx()
                .expand_key_archetype()
                .expand_linear_diffusion()
                .expand_key_bit_rotations()
                .expand_cell_sliced()
                .expand_whitening())

    def expand_arx(self) -> "CipherSpec":
        """Lower an `arx` declaration into concrete modadd/xor/rotation layers.

        Each op becomes ONE round layer applied to every lane in parallel; when there is more
        than one selection phase the layer carries phase_params so its indices cycle per round
        (ChaCha columns/diagonals, Forro's 8 selections). Scratch temps ({"temp": k}) and the
        optional feed-forward (save the input state, add it back at the end) are handled here.
        """
        arx = self.arx
        if not arx:
            return self
        import copy
        wb, nw = arx["word_bitsize"], arx["nbr_words"]
        selections = arx["selections"]
        lanes = len(selections[0])
        temp_per_lane = arx.get("temp_per_lane", 0)
        feedforward = bool(arx.get("feedforward", False))
        scratch = temp_per_lane * lanes                     # per-lane scratch words
        save = nw if feedforward else 0                     # saved initial state for feed-forward
        ntw = scratch + save
        period = len(selections)
        _ROT = {"rotl": "l", "rotr": "r"}

        def resolve(pos, lane_tuple, lane_j):
            if isinstance(pos, dict):                       # {"temp": k} -> per-lane scratch word
                return nw + pos["temp"] * lanes + lane_j
            return lane_tuple[pos]

        def op_params(op, sset):
            kind = op["op"]
            if kind in _ROT:
                rots = [[_ROT[kind], op["amount"], resolve(op["in"][0], t, j), resolve(op["out"], t, j)]
                        for j, t in enumerate(sset)]
                return "rotation", {"rotations": rots}
            inp = [[resolve(p, t, j) for p in op["in"]] for j, t in enumerate(sset)]
            out = [resolve(op["out"], t, j) for j, t in enumerate(sset)]
            return kind, {"input_indices": inp, "output_indices": out}

        layers = []
        for op in arx["ops"]:
            per_phase = [op_params(op, sset) for sset in selections]
            lt = per_phase[0][0]
            if period == 1:
                layers.append(LayerSpec(lt, per_phase[0][1]))
            else:
                layers.append(LayerSpec(lt, per_phase[0][1], phase_params=[pp[1] for pp in per_phase]))

        R = self.nbr_rounds
        new = copy.deepcopy(self)
        new.arx = None
        new.cipher_type = "permutation"
        new.word_bitsize, new.nbr_words, new.nbr_temp_words = wb, nw, ntw
        new.block_size = wb * nw
        if feedforward:
            # round 1: save the input state to the tail temps (an identity 'equal' copy);
            # last round: add the saved state back; middle rounds run the ARX (sub)round.
            save_idx = list(range(scratch, scratch + nw))
            save_layer = LayerSpec("equal", {"input_indices": [[i] for i in range(nw)],
                                             "output_indices": [nw + s for s in save_idx]},
                                    only_rounds=[1])
            add_layer = LayerSpec("modadd", {"input_indices": [[i, nw + scratch + i] for i in range(nw)],
                                             "output_indices": list(range(nw))}, only_rounds=[-1])
            body = [LayerSpec(l.layer_type, l.params, except_rounds=[R], phase_params=l.phase_params)
                    for l in layers]
            new.round_structure = [save_layer] + body + [add_layer]
        else:
            new.round_structure = layers
        return new

    def expand_key_archetype(self) -> "CipherSpec":
        """Lower a `key_archetype` declaration into a concrete spec (MidoriCore SPN layout).

        Produces the same structure as a hand-written Midori: a pre-whitening round, the
        round-function rounds with an alternating round key and pi-derived constants, a
        final round applying only the first data-path layer, and a post-whitening round.
        WK = XOR of shares is built inside SUBKEYS via {"xor": ...} extraction entries.
        """
        arch = self.key_archetype
        if not arch:
            return self
        atype = arch.get("type")
        if atype == "tweakey_lfsr":
            return self._expand_tweakey_lfsr()
        if atype != "static_alternating":
            raise ValueError(
                f"key_archetype: unknown type {atype!r} "
                f"(expected 'static_alternating' or 'tweakey_lfsr')")
        import copy
        shares = int(arch.get("shares", 1))
        whitening = arch.get("whitening", "none")
        R = self.nbr_rounds
        # With a cell_layout the data path is lowered to word_bitsize=1 (nc*cb bits) by
        # expand_cell_sliced AFTER this, so the key add / round constants this injects must be
        # BIT-level too: mask over all nc*cb bits, key modeled bit-sliced, and each cell's
        # constant placed at that cell's LSB bit. Otherwise it is a word-level cipher.
        if self.cell_layout:
            cb, nc = self.cell_layout["cell_bits"], self.cell_layout["nbr_cells"]
            nw = cb * nc                                  # state bits (becomes nbr_words at expand)
            knw = self.key_size                           # bit-sliced key
        else:
            cb = None
            nw = self.nbr_words
            knw = self.key_nbr_words or (self.key_size // (self.key_word_bitsize or self.word_bitsize))
        if shares <= 0 or knw % shares != 0:
            raise ValueError(f"key_archetype: shares={shares} must divide key words={knw}")
        sw = knw // shares
        if whitening == "xor_shares" and shares != 2:
            raise ValueError("key_archetype: whitening 'xor_shares' currently supports exactly 2 shares")

        def share_idx(s):
            return list(range(s * sw, (s + 1) * sw))

        has_wk = whitening in ("xor_shares", "whole_key", "first_share")
        wk_entry = {"xor": [share_idx(0), share_idx(1)]} if whitening == "xor_shares" else share_idx(0)
        # key_period P > 1 (LED): the round key is added only once per P-round "step" (rounds
        # 1, 1+P, 1+2P, ...) plus a trailing key-only round; the share alternates per key
        # ADDITION event, not per round. P == 1 (Midori) adds a key every round.
        period = int(arch.get("key_period", 1))
        if period < 1:
            raise ValueError("key_archetype: key_period must be >= 1")
        has_trailing = has_wk or period > 1
        new_R = R + 1 if has_trailing else R
        key_rounds = ([r for r in range(1, new_R + 1) if (r - 1) % period == 0]
                      if period > 1 else None)

        # per-round subkey extraction: pre-WK, alternating round keys, post-WK
        extract = []
        for r in range(1, new_R + 1):
            if has_wk and (r == 1 or r == new_R):
                extract.append(copy.deepcopy(wk_entry))
            elif period > 1:                             # share alternates per key-add event
                extract.append(share_idx(((r - 1) // period) % shares))
            else:
                i = (r - 2) if has_wk else (r - 1)       # MidoriCore loop index
                extract.append(share_idx(i % shares))

        # round constants apply only on the round-function rounds (not the WK rounds)
        rc = arch.get("round_constants")
        rc_layer = None
        if rc:
            count = rc.get("count", R - 1 if has_wk else R)
            src = rc.get("source", "pi_hex")
            if src == "pi_hex":
                cells = pi_round_constant_cells(count)
            elif src == "table":
                cells = rc["table"]
            elif src == "code":
                # LLM-supplied program computing `result` = a list of `count` cell-rows,
                # run in the restricted sandbox; the KAT verifies the values afterward.
                cells = safe_eval_program(rc["code"], {"count": count, "nbr_cells": nw})
                if not (isinstance(cells, list) and all(isinstance(r, list) for r in cells)):
                    raise ValueError("key_archetype round_constants code must return a list of rows")
            else:
                raise ValueError(f"key_archetype round_constants: unknown source {src!r}")
            first_rf = 2 if has_wk else 1                # first round-function round number
            table = [[0] * nw for _ in range(new_R)]     # ConstantXOR indexes table[round-1]
            for j, row in enumerate(cells):
                if first_rf - 1 + j < new_R:
                    if cb:                               # bit-sliced: cell c's constant -> its LSB bit
                        bitrow = [0] * nw
                        for c, v in enumerate(row):
                            bitrow[cb * c + cb - 1] = v
                        table[first_rf - 1 + j] = bitrow
                    else:
                        table[first_rf - 1 + j] = list(row)
            rc_layer = LayerSpec(
                "add_constant",
                {"add_type": "xor", "constant_mask": [1] * nw, "constant_table": table},
                except_rounds=([1, new_R] if has_wk else None))

        # assemble: AddRoundKey (every round, or only every P rounds) -> [round constant] ->
        # data path (trailing-round scoped)
        new_layers = [LayerSpec("add_round_key", {"operator": "xor", "mask": [1] * nw},
                                only_rounds=key_rounds)]
        if rc_layer:
            new_layers.append(rc_layer)
        for k, d in enumerate(self.round_structure):
            layer = copy.deepcopy(d)
            skip = set(layer.except_rounds or [])
            if has_trailing:
                skip.add(new_R)                          # trailing key-only round runs no data path
            if has_wk and k > 0:                         # Midori: linear layers skip the final-SubCell round
                skip.add(R)
            layer.except_rounds = sorted(skip) or None
            new_layers.append(layer)

        new = copy.deepcopy(self)
        new.key_archetype = None
        new.nbr_rounds = new_R
        new.round_structure = new_layers
        new.key_extract_indices = extract
        new.key_schedule = None                          # static key
        if cb:                                           # cell_layout: the key is bit-sliced too
            new.key_word_bitsize = 1
            new.key_nbr_words = knw
        return new

    def _expand_tweakey_lfsr(self) -> "CipherSpec":
        """Lower a `tweakey_lfsr` archetype (SKINNY / Deoxys tweakey) into an EVOLVING
        key_schedule + key_extract_indices, leaving round_structure (its add_round_key
        included) untouched.

        The tweakey state holds ``branches`` parallel branches (TK1, TK2, ...) of
        ``cells_per_branch`` cells each. Every round the schedule (a) permutes each branch's
        cells by ``permutation`` (the SKINNY P_T by default), then (b) for each branch that
        has an LFSR matrix, applies that per-cell GF(2) matrix to the branch's top
        ``lfsr_cells`` cells. The round subkey is the XOR, over all branches, of each
        branch's top ``subkey_cells`` cells; the generic SUBKEYS builder combines the shares
        (XOR for 2 branches, N_XOR for 3). Because extraction reads the key state at the
        START of each round (before that round's update), subkey_i is the top cells after
        i-1 updates - exactly SKINNY's schedule (which achieves the same with an identity
        first round and an nbr_rounds+1 key schedule).

        Unlike static_alternating this archetype does NOT emit the round-function
        add_round_key: SKINNY adds the subkey in the MIDDLE of the round (after SubCell and
        the round constant, before ShiftRows), a position only the hand-written data path
        knows, so round_structure keeps its own add_round_key.
        """
        import copy
        arch = self.key_archetype
        branches = int(arch.get("branches", 1))
        C = int(arch.get("cells_per_branch", self.nbr_words or 0))
        K = int(arch.get("subkey_cells", (C // 2) if C else 0))
        L = int(arch.get("lfsr_cells", K))
        # SKINNY's tweakey cell permutation P_T; override for a different tweakey family.
        perm = arch.get("permutation", [9, 15, 8, 13, 10, 14, 12, 11, 0, 1, 2, 3, 4, 5, 6, 7])
        lfsr_mats = arch.get("lfsr_matrices", [None] * branches)

        if branches < 1:
            raise ValueError("tweakey_lfsr: branches must be >= 1")
        if C <= 0:
            raise ValueError("tweakey_lfsr: cells_per_branch must be > 0 (set it or nbr_words)")
        knw = self.key_nbr_words or (self.key_size // (self.key_word_bitsize or self.word_bitsize or 1))
        if branches * C != knw:
            raise ValueError(
                f"tweakey_lfsr: branches*cells_per_branch ({branches}*{C}={branches * C}) must "
                f"equal the key word count ({knw}). Set key_nbr_words / key_size accordingly.")
        if len(perm) != C:
            raise ValueError(f"tweakey_lfsr: permutation must have cells_per_branch={C} entries "
                             f"(got {len(perm)}).")
        if sorted(perm) != list(range(C)):
            raise ValueError(f"tweakey_lfsr: permutation must be a permutation of 0..{C - 1}.")
        if len(lfsr_mats) != branches:
            raise ValueError(
                f"tweakey_lfsr: lfsr_matrices must have one entry per branch ({branches}); use "
                f"null for a branch with no LFSR (e.g. TK1). Got {len(lfsr_mats)}.")
        if not (1 <= K <= C):
            raise ValueError(f"tweakey_lfsr: subkey_cells must be in 1..{C} (got {K}).")
        if not (1 <= L <= C):
            raise ValueError(f"tweakey_lfsr: lfsr_cells must be in 1..{C} (got {L}).")

        # one permutation layer over the whole key state: branch b's block [b*C, b*C+C) is
        # permuted by perm, offset into that block.
        full_perm = [b * C + perm[i] for b in range(branches) for i in range(C)]
        layers = [LayerSpec("permutation", {"table": full_perm})]
        for b in range(branches):
            M = lfsr_mats[b]
            if M is not None:
                top = list(range(b * C, b * C + L))
                layers.append(LayerSpec("gf2_linear", {"matrix": M, "index_in": top}))

        if branches == 1:
            extract = list(range(K))                     # single branch: plain top-K extraction
        else:
            extract = [{"xor": [list(range(b * C, b * C + K)) for b in range(branches)]}]

        new = copy.deepcopy(self)
        new.key_archetype = None
        new.key_schedule = layers
        new.key_extract_indices = extract
        return new

    def expand_whitening(self) -> "CipherSpec":
        """Return an equivalent spec with pre/post whitening turned into extra round(s).

        Each whitening becomes one extra round in which only the add_round_key layer runs
        (the other layers are made identity via except_rounds), so the whitening key is a
        normal per-round subkey. nbr_rounds grows by the number of whitenings; the key
        schedule then naturally extracts one more subkey per added round.
        """
        if not (self.pre_whitening or self.post_whitening):
            return self
        import copy
        new = copy.deepcopy(self)
        new.pre_whitening = new.post_whitening = False
        skip_rounds = []
        if self.pre_whitening:
            skip_rounds.append(1)       # round 1 does only the key addition
        if self.post_whitening:
            skip_rounds.append(-1)      # last round does only the key addition
        new.nbr_rounds = self.nbr_rounds + len(skip_rounds)
        for layer in new.round_structure:
            if layer.layer_type != "add_round_key":
                existing = list(layer.except_rounds or [])
                layer.except_rounds = existing + skip_rounds
        return new

    def validate(self) -> List[str]:
        """Validate the spec and return a list of error messages (empty if valid)."""
        if self.versions:
            try:
                return self.instantiate().validate()
            except (ValueError, KeyError, TypeError) as exc:
                return [f"Version instantiation failed: {exc}"]
        # layout / cell_layout / arx are ALTERNATIVE data-path representations (bit-sliced
        # rows x cols, cell-oriented, and add-rotate-xor), each lowered by a DIFFERENT expander.
        # More than one is a conflict: the validate/build order would pick one and silently
        # ignore the rest, mis-expanding the operations (matrix-dimension / index errors). Catch
        # it before any expander runs. (key_archetype is NOT here - it composes with cell_layout,
        # e.g. Midori.)
        _reps = [name for name, present in
                 (("layout", self.layout), ("cell_layout", self.cell_layout), ("arx", self.arx))
                 if present]
        if len(_reps) > 1:
            return [f"{', '.join(_reps)} are mutually exclusive data-path representations; "
                    f"use exactly one (ARX -> arx, bit-sliced SPN -> layout, cell-oriented "
                    f"SPN -> cell_layout, plain word-based -> none)."]
        if self._has_code_params():
            try:
                return self.resolve_code_params().validate()
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                return [f"Code-param resolution failed: {exc}"]
        if self.key_archetype:
            # A key_archetype GENERATES key handling. If the spec ALSO provides the same handling
            # the archetype silently DOUBLES it (a hand-written add_round_key next to a
            # static_alternating archetype adds the key twice - the exact Midori mis-draft). Reject
            # such conflicts up front. Which handling is generated depends on the archetype TYPE:
            # static_alternating emits the round-function add_round_key itself, whereas tweakey_lfsr
            # only evolves the tweakey and REQUIRES round_structure to add the subkey mid-round.
            atype = self.key_archetype.get("type")
            if atype not in ("static_alternating", "tweakey_lfsr"):
                return [f"key_archetype: unknown type {atype!r} "
                        f"(expected 'static_alternating' or 'tweakey_lfsr')"]
            arch_conflicts = []   # handling PRESENT that this archetype also generates (would double)
            arch_errors = []      # other archetype misuse (standalone messages)
            layer_types = [l.layer_type for l in (self.round_structure or [])]
            if atype == "tweakey_lfsr":
                if "add_round_key" not in layer_types:
                    arch_errors.append(
                        "tweakey_lfsr evolves the tweakey and extracts the subkey, but round_structure "
                        "has NO add_round_key to ADD it. Put an add_round_key layer at the correct round "
                        "position (SKINNY: after SubCell and the round constant, before ShiftRows).")
            else:  # static_alternating: the archetype emits the add_round_key
                if "add_round_key" in layer_types:
                    arch_conflicts.append(
                        "an add_round_key layer. FIX by REMOVING that add_round_key layer and KEEPING "
                        "the archetype (it adds the round key AND the round constants AND the whitening "
                        "for you - all of which are easily lost if you instead delete the archetype and "
                        "hand-wire the key). round_structure must be the DATA PATH ONLY (SubCell / "
                        "Shuffle / MixColumn), with NO add_round_key")
            if self.key_archetype.get("round_constants") and "add_constant" in layer_types:
                arch_conflicts.append(
                    "an add_constant layer AND archetype round_constants (both add constants - keep one)")
            if self.key_extract_indices is not None:
                arch_conflicts.append(
                    "a hand-written key_extract_indices (the archetype generates it - remove the field)")
            if self.key_schedule:
                # Both archetypes GENERATE the key_schedule, so a hand-written one conflicts.
                if atype == "static_alternating":
                    # An EVOLVING schedule (updates the key each round) also CONTRADICTS a
                    # static_alternating archetype (a FIXED key); the right fix is to drop the
                    # archetype, not the schedule (the FUTURE/evolving-key class).
                    _update = {"rotation", "shift", "bit_rotation", "gf2_linear"}
                    if any(l.layer_type in _update for l in self.key_schedule):
                        kinds = sorted({l.layer_type for l in self.key_schedule if l.layer_type in _update})
                        arch_conflicts.append(
                            f"an EVOLVING key_schedule (it updates the key each round via {kinds}). A "
                            f"static_alternating archetype models a FIXED key, so the two CONTRADICT. "
                            f"FIX by REMOVING the key_archetype and keeping the key_schedule + "
                            f"pre_whitening/post_whitening (the FUTURE/evolving-key class) - do NOT use "
                            f"the archetype for a rotating/updating key")
                    else:
                        arch_conflicts.append(
                            "a non-empty key_schedule (the archetype models a static key - remove it)")
                else:  # tweakey_lfsr generates its own evolving schedule
                    arch_conflicts.append(
                        "a hand-written key_schedule (the tweakey_lfsr archetype generates the evolving "
                        "tweakey schedule - remove the field)")
            if arch_conflicts or arch_errors:
                return ["key_archetype conflicts with " + c for c in arch_conflicts] + arch_errors
            try:
                return self.expand_key_archetype().validate()
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                return [f"Key-archetype expansion failed: {exc}"]
        if self.arx:
            try:
                return self.expand_arx().validate()
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                return [f"ARX expansion failed: {exc}"]
        if any(l.layer_type == "linear_diffusion" for l in (self.round_structure or [])):
            try:
                return self.expand_linear_diffusion().validate()
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                return [f"linear_diffusion expansion failed: {exc}"]
        if self.layout:
            try:
                return self.expand_bitsliced().validate()
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                return [f"Bit-sliced expansion failed: {exc}"]
        if self.cell_layout:
            try:
                return self.expand_cell_sliced().validate()
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                return [f"Cell-sliced expansion failed: {exc}"]
        errors = []
        if not self.name:
            errors.append("Cipher name is required.")
        if self.cipher_type not in ("permutation", "blockcipher"):
            errors.append(f"Invalid cipher_type: '{self.cipher_type}'. Use 'permutation' or 'blockcipher'.")
        for field_name in ("block_size", "word_bitsize", "nbr_words", "nbr_rounds"):
            value = getattr(self, field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                errors.append(
                    f"{field_name} must be a positive integer (got {value!r}). "
                    "For a family with several values (e.g. KNOT's nr/nr0/nrf), pick one."
                    if field_name == "nbr_rounds" else
                    f"{field_name} must be a positive integer (got {value!r})."
                )
        if not self.round_structure:
            errors.append("round_structure must have at least one layer.")

        valid_layer_types = {"sbox", "permutation", "rotation", "shift", "xor", "and", "or", "not",
                             "n_xor", "andxor", "modadd", "matrix", "gf2_linear", "add_round_key",
                             "add_constant", "add_identity", "equal", "aes_round"}
        for i, layer in enumerate(self.round_structure):
            if layer.layer_type not in valid_layer_types:
                errors.append(f"Round layer {i}: invalid type '{layer.layer_type}'. Valid: {valid_layer_types}")

        # Validate required params per layer, in round_structure AND key_schedule, so a
        # missing param (e.g. rotation's word_index) or a leftover "$placeholder" surfaces
        # here - at draft time and to Fix with AI - instead of only failing later at build.
        _required_layer_params = {
            "rotation": ("direction", "amount", "word_index"),
            "shift": ("direction", "amount", "word_index"),
            "sbox": ("sbox_name",),
            "permutation": ("table",),
            "matrix": ("matrix", "indices"),
            "gf2_linear": ("matrix", "index_in"),
            "add_constant": ("constant_mask", "constant_table"),
            # boolean/arithmetic operators all take input_indices + output_indices; without them
            # the build raised a bare KeyError('input_indices') that validate never surfaced.
            "xor": ("input_indices", "output_indices"),
            "and": ("input_indices", "output_indices"),
            "or": ("input_indices", "output_indices"),
            "modadd": ("input_indices", "output_indices"),
            "n_xor": ("input_indices", "output_indices"),
            "andxor": ("input_indices", "output_indices"),
            "not": ("input_indices", "output_indices"),
            "equal": ("input_indices", "output_indices"),
            # fused AES round: input_indices/output_indices are groups of exactly 16 words
            # (AESround enforces the 16 at build); routed through SingleOperatorLayer.
            "aes_round": ("input_indices", "output_indices"),
        }
        # exact input-group size each operator needs (n_xor takes any >= 1)
        _op_arity = {"xor": 2, "and": 2, "or": 2, "modadd": 2, "andxor": 3, "not": 1, "equal": 1}

        def _check_layer_params(layers, where, word_bitsize, state_size=None):
            for idx, lyr in enumerate(layers or []):
                params = lyr.params or {}
                # A rotation given in multi-word form ({"rotations": [...]}, e.g. an ARX quarter
                # round rotating 4 lanes) has no direction/amount/word_index.
                req = () if (lyr.layer_type == "rotation" and params.get("rotations") is not None) \
                    else _required_layer_params.get(lyr.layer_type, ())
                missing = [k for k in req if k not in params]
                if missing:
                    errors.append(
                        f"{where} layer {idx} ('{lyr.layer_type}') is missing required "
                        f"param(s) {missing}."
                    )
                unresolved = [k for k, v in params.items() if isinstance(v, str) and v.startswith("$")]
                if unresolved:
                    errors.append(
                        f"{where} layer {idx} ('{lyr.layer_type}') has unresolved placeholder(s) "
                        f"{unresolved} - this cipher is not a parameterized family, use concrete values."
                    )
                # A rotation/shift acts on ONE word, so the amount must be < that word's
                # bit width. A larger amount means the operation is really over a WIDER unit
                # than a word (e.g. FUTURE rotates the whole 64-bit key by 5 bits, which no
                # 4-bit-word rotation can express) - flag it at draft time, not only at build.
                if lyr.layer_type in ("rotation", "shift") and word_bitsize:
                    amount = params.get("amount")
                    if isinstance(amount, int) and not (0 < amount < word_bitsize):
                        steer = (" This is the FUTURE-class case: the whole key register is "
                                 "rotated by a BIT amount that crosses cell boundaries, so the "
                                 "cipher CANNOT be word-level. Use \"cell_layout\" for the data "
                                 "path and model the key schedule BIT-sliced (word_bitsize=1) - "
                                 "the rotation becomes a bit PERMUTATION over the key bits, NOT a "
                                 "word/cell rotation (a 5-bit rotation is NOT a 5-word shift)."
                                 if where == "key_schedule" else
                                 " Model it bit-sliced (word_bitsize=1) as a bit permutation, not "
                                 "a word rotation.")
                        errors.append(
                            f"{where} layer {idx} ('{lyr.layer_type}') amount {amount} must "
                            f"satisfy 0 < amount < word_bitsize ({word_bitsize}).{steer}")
                # A rotation/shift direction is a code, not free text: OCP only understands
                # left/right. A typo ("up", "L ") would silently mis-generate.
                if lyr.layer_type in ("rotation", "shift"):
                    dirs = ([params["direction"]] if isinstance(params.get("direction"), str) else []) + \
                           [r[0] for r in (params.get("rotations") or []) if isinstance(r, (list, tuple)) and r]
                    for d in dirs:
                        if d not in ("l", "r", "left", "right"):
                            errors.append(
                                f"{where} layer {idx} ('{lyr.layer_type}') direction {d!r} must be "
                                f"one of 'l'/'r'/'left'/'right'.")
                # Every WORD index a layer names must be a real state word (0 .. state_size-1,
                # temp words included). An out-of-range index is a wrong model that either
                # crashes at build or silently reads a scratch word. Only params that index in
                # the cipher's word unit are checked here; a `permutation` table is deliberately
                # EXCLUDED - it may index bits (a bit-permutation over a word-level state) or be a
                # partial permutation (Simon's key rotation [4,0,1,2]), so its range is not the
                # word count. Its correctness is left to the KAT.
                if state_size:
                    idxs = []
                    for grp in (params.get("input_indices") or []):
                        idxs += grp if isinstance(grp, list) else [grp]
                    idxs += params.get("output_indices") or []
                    idxs += params.get("index_in") or []                  # gf2_linear
                    idxs += params.get("index_out") or []
                    for grp in (params.get("indices") or []):             # matrix
                        idxs += grp if isinstance(grp, list) else [grp]
                    for key in ("word_index", "out_index"):
                        if isinstance(params.get(key), int):
                            idxs.append(params[key])
                    for r in (params.get("rotations") or []):             # [dir, amount, in, out]
                        idxs += [v for v in r[2:] if isinstance(v, int)]
                    bad = sorted({v for v in idxs if isinstance(v, int) and not 0 <= v < state_size})
                    if bad:
                        errors.append(
                            f"{where} layer {idx} ('{lyr.layer_type}') references word index/indices "
                            f"{bad} outside the state (0 .. {state_size - 1}).")
                # Operator ARITY: xor/and/or/modadd take 2-word input groups, andxor 3, not/equal
                # 1, n_xor any >= 1; and there is one output per input group. A wrong group size
                # is a mis-modeled operator that fails opaquely at build.
                if lyr.layer_type in _required_layer_params and "input_indices" in params \
                        and lyr.layer_type in ("xor", "and", "or", "modadd", "andxor",
                                               "not", "equal", "n_xor"):
                    groups = params.get("input_indices")
                    outs = params.get("output_indices")
                    need = _op_arity.get(lyr.layer_type)
                    if isinstance(groups, list):
                        for g in groups:
                            if isinstance(g, list) and need is not None and len(g) != need:
                                errors.append(
                                    f"{where} layer {idx} ('{lyr.layer_type}') input group {g} must "
                                    f"have exactly {need} word(s) ({need}-ary operator).")
                            elif isinstance(g, list) and not g:
                                errors.append(
                                    f"{where} layer {idx} ('{lyr.layer_type}') has an empty input group.")
                        if isinstance(outs, list) and len(outs) != len(groups):
                            errors.append(
                                f"{where} layer {idx} ('{lyr.layer_type}') has {len(groups)} input "
                                f"group(s) but {len(outs)} output index/indices (need one per group).")
                # add_constant builds one ConstantXOR per masked word, indexing each round's
                # constant row by that word's position. So every constant_table row must have
                # exactly as many values as the mask has active positions - otherwise codegen
                # indexes past the row end (a raw IndexError at build). Flag it at draft time.
                # A position is active when it is NOT None (matching OCP's ConstantXOR), so a
                # 0 placeholder for "inactive" is a mistake - it still selects the word and the
                # row must account for it; use None (or omit) to skip a word.
                if lyr.layer_type == "add_constant":
                    mask = params.get("constant_mask")
                    table = params.get("constant_table")
                    if isinstance(mask, list) and isinstance(table, list) and table:
                        active = sum(1 for m in mask if m is not None)
                        bad = sorted({len(r) for r in table if isinstance(r, list) and len(r) != active})
                        if bad:
                            errors.append(
                                f"{where} layer {idx} ('add_constant') has constant_table rows of "
                                f"length {bad} but the mask selects {active} word(s). Each row must "
                                f"have exactly {active} values (one per masked word)."
                            )
                # A matrix layer multiplies each index group by the matrix, so the matrix must
                # be SQUARE and its dimension must equal every column group's length. A 16x16
                # matrix with 4-word groups (mixing bit-level and cell-level) fails at build with
                # "input vector does not match matrix size" - flag it at draft time instead.
                if lyr.layer_type == "matrix":
                    matrix = params.get("matrix")
                    groups = params.get("indices")
                    if isinstance(matrix, list) and matrix:
                        dim = len(matrix)
                        if any(not isinstance(r, list) or len(r) != dim for r in matrix):
                            errors.append(
                                f"{where} layer {idx} ('matrix') matrix must be square; got "
                                f"{dim} rows with differing lengths.")
                        elif isinstance(groups, list) and groups:
                            bad = sorted({len(g) for g in groups
                                          if isinstance(g, list) and len(g) != dim})
                            if bad:
                                errors.append(
                                    f"{where} layer {idx} ('matrix') has a {dim}x{dim} matrix but "
                                    f"column index groups of length {bad}. Each group must list "
                                    f"exactly {dim} words (one per matrix row). Keep ONE granularity: "
                                    f"a word-level MixColumn over m cells is an mxm matrix with "
                                    f"m-word groups (word_bitsize = cell bits); a bit-sliced one is "
                                    f"(m*c)x(m*c) with each group listing all m*c bits (word_bitsize=1)."
                                )

        _state = ((self.nbr_words or 0) + (self.nbr_temp_words or 0)) or None
        _check_layer_params(self.round_structure, "round_structure", self.word_bitsize, _state)
        if self.cipher_type == "blockcipher":
            _key_state = ((self.key_nbr_words or 0) + (self.key_nbr_temp_words or 0)) or None
            _check_layer_params(self.key_schedule, "key_schedule",
                                self.key_word_bitsize or self.word_bitsize, _key_state)

        # Validate S-box references + index-group SIZE. An S-box consumes its input width in
        # bits; each index group lists the state words that form one S-box input, so a group
        # must hold exactly (S-box input bits / word_bitsize) words. This is a PERMANENT
        # invariant, not the Midori-specific "one cell": a per-cell S-box at cell granularity
        # is 1 word/group [[0],[1],...]; a bit-sliced n-bit S-box groups all n bits; an m-bit
        # S-box over w-bit words groups m/w words. Catching this deterministically stops the
        # common error of reusing MixColumn's per-column grouping for the S-box.
        for i, layer in enumerate(self.round_structure):
            if layer.layer_type == "sbox":
                sbox_name = layer.params.get("sbox_name", "")
                if sbox_name and sbox_name not in self.sbox_tables:
                    from operators.Sbox import builtin_sbox_class
                    if builtin_sbox_class(sbox_name) is None:
                        errors.append(
                            f"Round layer {i}: S-box '{sbox_name}' not found in sbox_tables and is not a "
                            f"built-in OCP S-box (e.g. AES_Sbox, PRESENT_Sbox, Midori128_SSb0).")
                table = self.sbox_tables.get(sbox_name)
                index = layer.params.get("index")
                if (isinstance(table, list) and table and isinstance(index, list)
                        and isinstance(self.word_bitsize, int) and self.word_bitsize > 0):
                    n = max(1, (len(table) - 1).bit_length())    # S-box input width in bits
                    if n % self.word_bitsize == 0:
                        need = n // self.word_bitsize
                        bad = sorted({len(g) for g in index if isinstance(g, list) and len(g) != need})
                        if bad:
                            errors.append(
                                f"Round layer {i} ('sbox' {sbox_name!r}) has index groups of size "
                                f"{bad}, but each must have {need} word(s): the S-box takes {n} input "
                                f"bit(s) and each word is {self.word_bitsize} bit(s), so "
                                f"{n}//{self.word_bitsize} = {need} word(s) per group. (A per-cell "
                                f"S-box at cell granularity is 1 word/group [[0],[1],...]; do NOT reuse "
                                f"the MixColumn per-column grouping for the S-box.)")

        # Every S-box output must fit the S-box's output width: an n-bit S-box has 2^n entries
        # and its values must be in [0, 2^n). An out-of-range value is a copy error that yields a
        # wrong cipher (or an index error downstream).
        for name, table in (self.sbox_tables or {}).items():
            if isinstance(table, list) and table:
                hi = len(table)                          # 2^n for an n-bit S-box
                bad = sorted({v for v in table if isinstance(v, int) and not 0 <= v < hi})
                if bad:
                    errors.append(f"S-box {name!r} has value(s) {bad} outside the output range "
                                  f"[0, {hi}); an n-bit S-box's outputs must be < its length.")

        # State size must factor as word_bitsize * nbr_words (a layout/cell/versioned cipher
        # derives it and returned earlier, so here the three are concrete and must agree).
        if (isinstance(self.block_size, int) and self.block_size > 0
                and isinstance(self.word_bitsize, int) and self.word_bitsize > 0
                and isinstance(self.nbr_words, int) and self.nbr_words > 0
                and self.block_size != self.word_bitsize * self.nbr_words):
            errors.append(
                f"block_size ({self.block_size}) must equal word_bitsize * nbr_words "
                f"({self.word_bitsize} * {self.nbr_words} = {self.word_bitsize * self.nbr_words}).")

        # Block cipher validation
        if self.cipher_type == "blockcipher":
            if self.key_size is None or self.key_size <= 0:
                errors.append("Block cipher requires a positive key_size.")
            if self.key_nbr_words is None or self.key_nbr_words <= 0:
                errors.append("Block cipher requires key_nbr_words.")
            # Key size must factor as key_word_bitsize * key_nbr_words (symmetric with the
            # state check above), so a mis-declared key shape is caught before build.
            if (isinstance(self.key_size, int) and self.key_size > 0
                    and isinstance(self.key_word_bitsize, int) and self.key_word_bitsize > 0
                    and isinstance(self.key_nbr_words, int) and self.key_nbr_words > 0
                    and self.key_size != self.key_word_bitsize * self.key_nbr_words):
                errors.append(
                    f"key_size ({self.key_size}) must equal key_word_bitsize * key_nbr_words "
                    f"({self.key_word_bitsize} * {self.key_nbr_words} = "
                    f"{self.key_word_bitsize * self.key_nbr_words}).")
            # AddRoundKey XORs the subkey into the state, so a subkey word and a state word
            # must have the SAME bit width (all built-ins have key_word_bitsize == word_bitsize).
            # A mismatch (e.g. modeling a 128-bit key as 2x64-bit words over a 4-bit state, the
            # way an LLM does to make a cross-cell key rotation "legal") is a granularity
            # conflict: the cipher must be modeled bit-sliced (cell_layout / word_bitsize=1).
            if (self.key_word_bitsize is not None
                    and self.word_bitsize
                    and self.key_word_bitsize != self.word_bitsize):
                errors.append(
                    f"key_word_bitsize ({self.key_word_bitsize}) must equal word_bitsize "
                    f"({self.word_bitsize}) - the subkey is XORed into the state word for word. "
                    f"A larger key word usually means the key is being reshaped to make a "
                    f"cross-cell rotation legal. If the data path is a CELL S-box plus a GF(2^n) "
                    f"MixColumn (FUTURE/LED class), use \"cell_layout\": {{\"cell_bits\": n, "
                    f"\"nbr_cells\": m}} with the high-level cell layers (subcell_sbox / mixcolumn "
                    f"/ cell_shiftrow) - it bit-expands them for you. Plain word_bitsize=1 works "
                    f"ONLY if you also hand-expand every S-box/matrix/permutation table to bits."
                )
            if self.key_extract_indices is None:
                errors.append("Block cipher requires key_extract_indices (which key words form the subkey).")
            else:
                # key_extract_indices is a flat list (fixed), a list of lists (round-
                # dependent: round i uses phase (i-1) % period, e.g. Midori/LED K0/K1
                # alternation), entries {"xor": [share0, share1, ...]} for a combined subkey
                # (Midori WK = K0 (+) K1), or entries {"from": ks_round, "words": [...]} that
                # read a HISTORICAL key-schedule state (Simon's subkey reaches back to
                # vars[i-m+1]). Every entry must yield the same number of subkey words.
                extract = self.key_extract_indices

                def _entry_words(e):
                    if isinstance(e, dict):
                        return len(e["words"]) if "from" in e else len(e["xor"][0])
                    return len(e)

                periodic = bool(extract) and isinstance(extract[0], (list, dict))
                if periodic:
                    for p in extract:
                        if isinstance(p, dict) and "from" in p:
                            if not (isinstance(p.get("from"), int) and p["from"] >= 1
                                    and isinstance(p.get("words"), list) and p["words"]):
                                errors.append(
                                    'key_extract_indices "from" entry must be '
                                    '{"from": <ks_round >= 1>, "words": [indices]}.')
                        elif isinstance(p, dict):
                            shares = p.get("xor")
                            if not (isinstance(shares, list) and len(shares) >= 2
                                    and all(isinstance(s, list) for s in shares)
                                    and len({len(s) for s in shares}) == 1):
                                errors.append(
                                    "key_extract_indices xor entry must be "
                                    '{"xor": [share0, share1, ...]} with two or more '
                                    "equal-length index lists (the subkey is their XOR).")
                    share_counts = {len(p["xor"]) for p in extract
                                    if isinstance(p, dict) and "xor" in p}
                    if len(share_counts) > 1:
                        errors.append(
                            f"key_extract_indices xor entries have differing share counts "
                            f"{sorted(share_counts)}; every combined subkey must XOR the same "
                            f"number of shares.")
                    phase_lengths = sorted({_entry_words(p) for p in extract})
                    if len(phase_lengths) > 1:
                        errors.append(
                            f"key_extract_indices phases have differing lengths {phase_lengths}; "
                            f"every round must extract the same number of subkey words."
                        )
                    subkey_words = phase_lengths[0] if phase_lengths else 0
                else:
                    subkey_words = len(extract)

                # Every key-word index the extraction names must be a real key-state word
                # (0 .. key_state-1). A "from" entry's round number is NOT a word index and is
                # excluded here (it selects a key-schedule ROUND, bounded separately).
                key_state = (self.key_nbr_words or 0) + (self.key_nbr_temp_words or 0)
                if key_state:
                    kidx = []
                    for e in (extract if periodic else [extract]):
                        if isinstance(e, dict) and "from" in e:
                            kidx += e.get("words") or []
                        elif isinstance(e, dict):
                            for share in e.get("xor") or []:
                                kidx += share
                        elif isinstance(e, list):
                            kidx += e
                        else:
                            kidx.append(e)
                    kbad = sorted({v for v in kidx if isinstance(v, int) and not 0 <= v < key_state})
                    if kbad:
                        errors.append(
                            f"key_extract_indices references key-word index/indices {kbad} outside "
                            f"the key state (0 .. {key_state - 1}).")
                # OCP's AddRoundKey requires the number of active (=1) positions in an
                # add_round_key mask to equal the subkey size. Flag a mismatch here instead
                # of only at build ("subkey size does not match the mask").
                for idx, layer in enumerate(self.round_structure):
                    if layer.layer_type != "add_round_key":
                        continue
                    mask = (layer.params or {}).get("mask")
                    if mask is None:
                        continue
                    active = sum(1 for m in mask if m)
                    if active != subkey_words:
                        errors.append(
                            f"round_structure layer {idx} (add_round_key) mask has {active} "
                            f"active position(s) but the subkey has {subkey_words} word(s) "
                            f"(len of key_extract_indices). They must be equal - the mask "
                            f"selects which state words receive the subkey, one per subkey word."
                        )

        # Test-vector shape + value range. A vector whose word counts don't match the cipher
        # (e.g. a 31-word output for a 16-word Midori - a hallucinated vector) makes the KAT
        # unmatchable, and the auto-repair loop then chases an impossible target forever. Reject
        # it here with a readable message instead. Handles the {plaintext,key,output} dict form
        # and the [[inputs...], output] list form.
        def _tv_parts(tv):
            if isinstance(tv, dict):
                if "plaintext" in tv or "key" in tv:
                    return [tv.get("plaintext"), tv.get("key")], tv.get("output")
                return [tv.get("input")], tv.get("output")
            if isinstance(tv, (list, tuple)) and len(tv) == 2:
                ins = tv[0]
                return (list(ins) if isinstance(ins, (list, tuple)) else [ins]), tv[1]
            return None, None

        nw, wb = self.nbr_words, self.word_bitsize
        kw = self.key_nbr_words
        kwb = self.key_word_bitsize or self.word_bitsize
        for vi, tv in enumerate(self.test_vectors or []):
            ins, out = _tv_parts(tv)
            if out is None:
                continue
            if isinstance(nw, int) and nw > 0 and isinstance(out, list) and len(out) != nw:
                hexhint = ""
                if isinstance(wb, int) and wb in (4, 8):
                    per = wb // 4
                    hexhint = (f" Split the hex answer into ONE word per {per} hex char(s): a "
                               f"{nw * per}-hex-char value is {nw} words, not {len(out)}. Do not "
                               f"double it or append another variant's vector.")
                errors.append(f"Test vector {vi + 1} output has {len(out)} word(s); this cipher "
                              f"outputs {nw}. Fix the vector (or the state size) - a wrong length "
                              f"makes the known-answer test impossible to match.{hexhint}")
            if isinstance(wb, int) and wb > 0 and isinstance(out, list):
                obad = sorted({v for v in out if isinstance(v, int) and not 0 <= v < (1 << wb)})
                if obad:
                    errors.append(f"Test vector {vi + 1} output word(s) {obad} are outside "
                                  f"[0, 2^word_bitsize) = [0, {1 << wb}).")
            # plaintext (first input) for both permutations and block ciphers
            if ins and isinstance(ins[0], list) and isinstance(nw, int) and nw > 0 and len(ins[0]) != nw:
                errors.append(f"Test vector {vi + 1} plaintext/input has {len(ins[0])} word(s); "
                              f"this cipher takes {nw}.")
            # key (second input) for block ciphers
            if (self.cipher_type == "blockcipher" and len(ins or []) > 1
                    and isinstance(ins[1], list) and isinstance(kw, int) and kw > 0
                    and len(ins[1]) != kw):
                errors.append(f"Test vector {vi + 1} key has {len(ins[1])} word(s); this cipher's "
                              f"key is {kw} word(s).")

        return errors

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dict."""
        d = {
            "name": self.name,
            "cipher_type": self.cipher_type,
            "block_size": self.block_size,
            "word_bitsize": self.word_bitsize,
            "nbr_words": self.nbr_words,
            "nbr_rounds": self.nbr_rounds,
            "nbr_temp_words": self.nbr_temp_words,
            "round_structure": [l.to_dict() for l in self.round_structure],
            "sbox_tables": self.sbox_tables,
        }
        if self.arx:
            d["arx"] = self.arx
        if self.cipher_type == "blockcipher":
            d.update({
                "key_size": self.key_size,
                "key_word_bitsize": self.key_word_bitsize,
                "key_nbr_words": self.key_nbr_words,
                "key_nbr_temp_words": self.key_nbr_temp_words,
                "key_schedule": [l.to_dict() for l in (self.key_schedule or [])],
                "key_extract_indices": self.key_extract_indices,
            })
            if self.key_nbr_rounds is not None:
                d["key_nbr_rounds"] = self.key_nbr_rounds
            if self.pre_whitening:
                d["pre_whitening"] = True
            if self.post_whitening:
                d["post_whitening"] = True
            if self.key_archetype:
                d["key_archetype"] = self.key_archetype
        if self.test_vectors:
            d["test_vectors"] = self.test_vectors
        if self.versions:
            d["versions"] = self.versions
            d["default_version"] = self.default_version
        if self.layout:
            d["layout"] = self.layout
        if self.cell_layout:
            d["cell_layout"] = self.cell_layout
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "CipherSpec":
        """Construct from a dict (e.g., parsed from JSON)."""
        spec = cls(
            name=d.get("name", "CustomCipher"),
            cipher_type=d.get("cipher_type", "permutation"),
            block_size=d.get("block_size", 64),
            word_bitsize=d.get("word_bitsize", 32),
            nbr_words=d.get("nbr_words", 2),
            nbr_rounds=d.get("nbr_rounds", 16),
            nbr_temp_words=d.get("nbr_temp_words", 0),
            round_structure=[LayerSpec.from_dict(l) for l in d.get("round_structure", [])],
            sbox_tables=d.get("sbox_tables", {}),
            test_vectors=d.get("test_vectors"),
        )
        spec.versions = d.get("versions")
        spec.default_version = d.get("default_version")
        spec.layout = d.get("layout")
        spec.cell_layout = d.get("cell_layout")
        spec.arx = d.get("arx")
        if spec.cipher_type == "blockcipher":
            spec.key_size = d.get("key_size")
            spec.key_word_bitsize = d.get("key_word_bitsize")
            spec.key_nbr_words = d.get("key_nbr_words")
            spec.key_nbr_temp_words = d.get("key_nbr_temp_words", 0)
            spec.key_nbr_rounds = d.get("key_nbr_rounds")
            spec.key_schedule = [LayerSpec.from_dict(l) for l in d.get("key_schedule", [])]
            spec.key_extract_indices = d.get("key_extract_indices")
            spec.pre_whitening = d.get("pre_whitening", False)
            spec.post_whitening = d.get("post_whitening", False)
            spec.key_archetype = d.get("key_archetype")
        return spec

    def to_permutation(self) -> "CipherSpec":
        """Return the keyless permutation for this cipher.

        The permutation is the round function with the key removed: the same
        round_structure minus any add_round_key layers, and no key schedule. It
        equals this cipher run with all round keys (subkeys) set to zero, and is
        what differential/linear analysis usually targets. Test vectors are not
        carried over (a block cipher's use a real key); derive fresh ones by
        evaluating the built permutation.
        """
        return CipherSpec(
            # keep the base name; build_permutation_from_spec appends "_PERM"
            name=self.name,
            cipher_type="permutation",
            block_size=self.block_size,
            word_bitsize=self.word_bitsize,
            nbr_words=self.nbr_words,
            nbr_rounds=self.nbr_rounds,
            nbr_temp_words=self.nbr_temp_words,
            round_structure=[
                LayerSpec(layer.layer_type, dict(layer.params),
                          only_rounds=layer.only_rounds, except_rounds=layer.except_rounds)
                for layer in self.round_structure
                if layer.layer_type != "add_round_key"
            ],
            sbox_tables=dict(self.sbox_tables),
        )

    def to_word_permutation(self) -> Optional["CipherSpec"]:
        """Best-effort WORD-level (cell-granularity) keyless permutation for a cell_layout
        cipher: word_bitsize = cell_bits, nbr_words = nbr_cells, and the CELL data-path layers
        re-expressed at cell granularity (subcell_sbox -> sbox, mixcolumn -> matrix, cell_shiftrow
        -> permutation, add_constant bit-rows repacked to cells). Returns None when the data path
        can't be cleanly coarsened (an archetype that injects bit-level constants, a partial
        constant mask, an unknown layer) - the caller then falls back to the bit-level
        permutation. EITHER WAY the result is cross-checked against the block cipher, so a wrong
        coarsening is caught, never trusted.
        """
        if not self.cell_layout or self.key_archetype:   # archetype constants are injected bit-level
            return None
        import copy
        cb, nc = self.cell_layout["cell_bits"], self.cell_layout["nbr_cells"]
        nbits = cb * nc

        def repack(params):
            mask, table = params.get("constant_mask"), params.get("constant_table")
            if not (isinstance(mask, list) and len(mask) == nbits and all(m for m in mask)):
                return None                              # only a full (all-cells) mask is handled
            # A keyless permutation has NO whitening round, but pre/post_whitening tables carry a
            # leading/trailing whitening-round row - drop those so the constants line up with the
            # perm's rounds (the block-cipher cross-check catches it if this guess is wrong).
            rows_in = list(table)
            if self.pre_whitening and rows_in:
                rows_in = rows_in[1:]
            if self.post_whitening and rows_in:
                rows_in = rows_in[:-1]
            rows = []
            for row in rows_in:
                if not (isinstance(row, list) and len(row) == nbits):
                    return None
                rows.append([sum(row[cb * c + j] << (cb - 1 - j) for j in range(cb)) for c in range(nc)])
            return {"add_type": params.get("add_type", "xor"),
                    "constant_mask": [1] * nc, "constant_table": rows}

        layers = []
        for lyr in self.round_structure:
            p, lt = lyr.params or {}, lyr.layer_type
            orr, er = lyr.only_rounds, lyr.except_rounds
            if lt == "add_round_key":
                continue
            elif lt == "subcell_sbox":
                layers.append(LayerSpec("sbox", {"sbox_name": p["sbox_name"],
                                                 "index": [[c] for c in range(nc)]}, orr, er))
            elif lt == "mixcolumn":
                layers.append(LayerSpec("matrix", {"matrix": p["matrix"],
                                                   "polynomial": p.get("polynomial", "0x0"),
                                                   "indices": p["columns"]}, orr, er))
            elif lt == "cell_shiftrow":
                layers.append(LayerSpec("permutation", {"table": p["table"]}, orr, er))
            elif lt in ("sbox", "matrix", "permutation"):
                layers.append(copy.deepcopy(lyr))
            elif lt == "add_constant":
                new = repack(p)
                if new is None:
                    return None
                layers.append(LayerSpec("add_constant", new, orr, er))
            else:
                return None                              # unknown layer -> fall back
        return CipherSpec(name=self.name, cipher_type="permutation",
                          block_size=nbits, word_bitsize=cb, nbr_words=nc,
                          nbr_rounds=self.nbr_rounds, round_structure=layers,
                          sbox_tables=dict(self.sbox_tables))

    def instantiate(self, version=None) -> "CipherSpec":
        """Resolve a version-parameterized family into one concrete CipherSpec.

        Applies the chosen version's scalar overrides (block_size, word_bitsize,
        nbr_rounds, key params, ...) and fills "$name" placeholders in the
        round_structure/key_schedule from the version's "params". Returns self
        unchanged when there are no versions.
        """
        if not self.versions:
            return self
        key = str(
            version if version is not None
            else self.default_version if self.default_version is not None
            else next(iter(self.versions))
        )
        if key not in self.versions:
            raise ValueError(f"Unknown version {key!r}. Available: {sorted(self.versions)}")
        overrides = dict(self.versions[key])
        params = overrides.get("params", {}) or {}
        # Name the concrete member from the version key (avoid doubling the base
        # name when the key already carries it), sanitized to a valid identifier.
        raw_name = key if key.lower().startswith(self.name.lower()) else f"{self.name}_{key}"

        # Deep-copy the WHOLE spec, then apply the version's scalar overrides and resolve
        # "$name" placeholders. Copying (instead of hand-rebuilding the CipherSpec) preserves
        # EVERY field automatically - cell_layout / arx / key_archetype / pre/post_whitening /
        # key_nbr_rounds and each layer's only_rounds / except_rounds / phase_params - so a newly
        # added field is never silently dropped here the way the old hand-built copy dropped them.
        import copy
        concrete = copy.deepcopy(self)
        concrete.versions = None
        concrete.default_version = None
        concrete.name = _sanitize_identifier(raw_name)

        # A version's scalar overrides may themselves reference params ("nbr_rounds": "$nr0");
        # take the override if present else the top-level value, resolving either against params.
        scalar_fields = ["block_size", "word_bitsize", "nbr_words", "nbr_rounds", "nbr_temp_words"]
        if self.cipher_type == "blockcipher":
            scalar_fields += ["key_size", "key_word_bitsize", "key_nbr_words",
                              "key_nbr_temp_words", "key_nbr_rounds", "key_extract_indices"]
        for field in scalar_fields:
            # a scalar may sit at the version's top level OR inside "params" (LLMs do both);
            # accept either so a value placed in params isn't ignored in favour of a stale top level.
            val = overrides.get(field, params.get(field, getattr(self, field)))
            setattr(concrete, field, _resolve_placeholders(val, params))
        if "test_vectors" in overrides:
            concrete.test_vectors = overrides["test_vectors"]

        # STRUCTURAL per-version overrides. When versions differ in STRUCTURE, not just scalars
        # (Midori64 has 1 S-box layer + xor_shares whitening; Midori128 has 4 position S-box
        # layers + whole_key whitening), a version may carry its OWN round_structure / key_schedule
        # / key_archetype / representation / whitening instead of sharing the base with only
        # $placeholders. Use the version's when present; sbox_tables MERGE (base + version) so a
        # version can add its own S-boxes without dropping shared ones.
        def _as_layers(val):
            return [l if isinstance(l, LayerSpec) else LayerSpec.from_dict(l) for l in (val or [])]
        if "round_structure" in overrides:
            concrete.round_structure = _as_layers(overrides["round_structure"])
        if "key_schedule" in overrides:
            concrete.key_schedule = _as_layers(overrides["key_schedule"])
        if isinstance(overrides.get("sbox_tables"), dict):
            merged = dict(self.sbox_tables or {})
            merged.update(overrides["sbox_tables"])
            concrete.sbox_tables = merged
        for field in ("key_archetype", "cell_layout", "arx", "layout",
                      "pre_whitening", "post_whitening"):
            if field in overrides:
                setattr(concrete, field, overrides[field])

        # resolve "$name" placeholders in the deep-copied layer params / phase params / layouts
        def _resolve_layers(layers):
            for lyr in (layers or []):
                lyr.params = _resolve_placeholders(lyr.params, params)
                if lyr.phase_params is not None:
                    lyr.phase_params = _resolve_placeholders(lyr.phase_params, params)
        _resolve_layers(concrete.round_structure)
        _resolve_layers(concrete.key_schedule)
        if concrete.layout is not None:
            concrete.layout = _resolve_placeholders(concrete.layout, params)
        if concrete.cell_layout is not None:
            concrete.cell_layout = _resolve_placeholders(concrete.cell_layout, params)
        return concrete

    def expand_bitsliced(self) -> "CipherSpec":
        """Expand a bit-sliced (rows x cols) layout into a concrete word_bitsize=1
        CipherSpec: subcolumn_sbox -> S-box on column bit-groups; shift_rows -> a
        bit-permutation; add_round_constant{{d, lfsr}} -> an add_constant with the
        LFSR-generated round-constant table. Returns self unchanged without a layout.
        """
        if not self.layout:
            return self
        rows = self.layout.get("rows")
        cols = self.layout.get("cols")
        for dim_name, dim in (("rows", rows), ("cols", cols)):
            if not isinstance(dim, int) or isinstance(dim, bool) or dim <= 0:
                raise ValueError(
                    f"layout {dim_name} must be a positive integer, got {dim!r}"
                    + ("" if not isinstance(dim, float)
                       else " (a placeholder like \"$b/4\" must divide evenly)")
                )
        total = rows * cols

        def widx(r, c):
            return r * cols + c

        new_round = []
        for layer in self.round_structure:
            lt = layer.layer_type
            p = layer.params or {}
            if lt == "subcolumn_sbox":
                table = self.sbox_tables.get(p["sbox_name"])
                if not isinstance(table, list) or len(table) != (1 << rows):
                    raise ValueError(
                        f"subcolumn_sbox '{p['sbox_name']}' needs a lookup table of length "
                        f"2**rows = {1 << rows} (one entry per column value over {rows} rows), "
                        f"got length {len(table) if isinstance(table, list) else table!r}"
                    )
                # S-box input for column c is a_{rows-1}||...||a_1||a_0 with row 0 the
                # LSB (KNOT convention). OCP reads index[0] as the MSB, so list the
                # rows most-significant first.
                index = [[widx(r, c) for r in reversed(range(rows))] for c in range(cols)]
                new_round.append(LayerSpec("sbox", {"sbox_name": p["sbox_name"], "index": index}))
            elif lt == "shift_rows":
                offsets = p["offsets"]
                if not isinstance(offsets, list) or len(offsets) != rows:
                    raise ValueError(
                        f"shift_rows needs one offset per row (offsets length must equal "
                        f"rows = {rows}), got {offsets!r}"
                    )
                direction = p.get("direction", "l")
                table = [0] * total
                for r in range(rows):
                    off = offsets[r] % cols
                    for c in range(cols):
                        # Left rotation moves the bit at column c to column c+off, i.e.
                        # output column c comes from input column c-off. OCP's table is
                        # output[i] = input[table[i]], so table[c] = c-off for "l".
                        src = (c - off) % cols if direction == "l" else (c + off) % cols
                        table[widx(r, c)] = widx(r, src)
                new_round.append(LayerSpec("permutation", {"table": table}))
            elif lt == "add_round_constant" and (p.get("lfsr") or p.get("constants") or p.get("code")):
                # d-bit round constant per round from an lfsr / explicit list / LLM code program
                # (safe_eval_program); bit-expanded to the first d bits. The KAT verifies it.
                d = p["d"]
                sequence = _round_constant_values(p, self.nbr_rounds)
                constant_table = [[(sequence[i] >> k) & 1 for k in range(d)] for i in range(self.nbr_rounds)]
                mask = [1] * d + [None] * (total - d)
                new_round.append(LayerSpec("add_constant", {
                    "add_type": "xor", "constant_mask": mask, "constant_table": constant_table,
                }))
            else:
                new_round.append(LayerSpec(lt, dict(p)))

        concrete = CipherSpec(
            name=self.name,
            cipher_type=self.cipher_type,
            block_size=total,
            word_bitsize=1,
            nbr_words=total,
            nbr_rounds=self.nbr_rounds,
            nbr_temp_words=self.nbr_temp_words,
            round_structure=new_round,
            sbox_tables=dict(self.sbox_tables),
            test_vectors=self.test_vectors,
        )
        if self.cipher_type == "blockcipher":
            concrete.key_size = self.key_size
            concrete.key_word_bitsize = self.key_word_bitsize
            concrete.key_nbr_words = self.key_nbr_words
            concrete.key_nbr_temp_words = self.key_nbr_temp_words
            concrete.key_schedule = self.key_schedule
            concrete.key_extract_indices = self.key_extract_indices
        return concrete

    def expand_cell_sliced(self) -> "CipherSpec":
        """Expand a cell-sliced layout into a concrete word_bitsize=1 CipherSpec.

        High-level CELL layers in round_structure are lowered to bit-level layers, deriving
        the error-prone tables so neither the user nor an LLM writes them by hand:
          - subcell_sbox {sbox_name}: the cell S-box on each cell's bit-group (MSB first).
          - mixcolumn {matrix (integer GF(2^cell_bits) coeffs), polynomial, columns}: a
            GF(2) binary MatrixLayer, the bit expansion of the GF(2^n) matrix over each
            column's cells. "polynomial" omits the top term (GF(2^4) x^4+x+1 -> "0x3").
          - cell_shiftrow {table}: a cell permutation lowered to a bit permutation.
        Any other layer (add_constant, add_round_key, permutation, ...) is already bit-level
        and passes through unchanged. Round-dependent scope (only_rounds/except_rounds) is
        preserved. The key schedule is left as given (supply it at bit level).
        Returns self unchanged without a cell_layout.
        """
        if not self.cell_layout:
            return self
        from agent.skills.cell_sliced import (
            gf_matrix_to_bit_matrix, cell_perm_to_bit_perm,
        )
        cell_bits = self.cell_layout.get("cell_bits")
        nbr_cells = self.cell_layout.get("nbr_cells")
        for nm, v in (("cell_bits", cell_bits), ("nbr_cells", nbr_cells)):
            if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                raise ValueError(f"cell_layout {nm} must be a positive integer, got {v!r}")
        total = cell_bits * nbr_cells

        def cell_bit_group(cell):  # bits of a cell, MSB first
            return [cell * cell_bits + k for k in range(cell_bits)]

        new_round = []
        for layer in self.round_structure:
            lt = layer.layer_type
            p = layer.params or {}
            keep = {"only_rounds": layer.only_rounds, "except_rounds": layer.except_rounds}
            if lt == "subcell_sbox":
                name = p["sbox_name"]
                table = self.sbox_tables.get(name)
                if not isinstance(table, list) or len(table) != (1 << cell_bits):
                    raise ValueError(
                        f"subcell_sbox '{name}' needs a lookup table of length "
                        f"2**cell_bits = {1 << cell_bits}, got "
                        f"{len(table) if isinstance(table, list) else table!r}")
                index = [cell_bit_group(i) for i in range(nbr_cells)]
                new_round.append(LayerSpec("sbox", {"sbox_name": name, "index": index}, **keep))
            elif lt == "mixcolumn":
                int_matrix = p["matrix"]
                columns = p["columns"]
                poly = p.get("polynomial", 0)
                poly_int = int(poly, 16) if isinstance(poly, str) else int(poly)
                full_poly = (1 << cell_bits) | poly_int
                bit_matrix = gf_matrix_to_bit_matrix(int_matrix, full_poly, cell_bits)
                indices = [[b for cell in col for b in cell_bit_group(cell)] for col in columns]
                new_round.append(LayerSpec("matrix", {"matrix": bit_matrix, "indices": indices}, **keep))
            elif lt == "cell_shiftrow":
                table = cell_perm_to_bit_perm(p["table"], cell_bits)
                new_round.append(LayerSpec("permutation", {"table": table}, **keep))
            else:
                new_round.append(LayerSpec(lt, dict(p), **keep))

        concrete = CipherSpec(
            name=self.name, cipher_type=self.cipher_type,
            block_size=total, word_bitsize=1, nbr_words=total,
            nbr_rounds=self.nbr_rounds, nbr_temp_words=self.nbr_temp_words,
            round_structure=new_round, sbox_tables=dict(self.sbox_tables),
            test_vectors=self.test_vectors,
        )
        if self.cipher_type == "blockcipher":
            concrete.key_size = self.key_size
            concrete.key_word_bitsize = self.key_word_bitsize
            concrete.key_nbr_words = self.key_nbr_words
            concrete.key_nbr_temp_words = self.key_nbr_temp_words
            concrete.key_schedule = self.key_schedule
            concrete.key_extract_indices = self.key_extract_indices
            concrete.pre_whitening = self.pre_whitening
            concrete.post_whitening = self.post_whitening
        return concrete
