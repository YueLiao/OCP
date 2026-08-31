"""Export a user-defined CipherSpec as an OCP-style primitive source file.

OCP ships each cipher as a hand-written module under ``primitives/`` (e.g.
``primitives/present.py``): a ``Permutation``/``Block_cipher`` subclass whose
``__init__`` builds the round function with the layer DSL (``SboxLayer``,
``PermutationLayer``, ``AddConstantLayer``, ...), plus a small factory function.
S-boxes live centrally in ``operators/Sbox.py`` (``KNOT_Sbox``, ``PRESENT_Sbox``,
...) and are imported by the primitive module.

This module turns a bit-sliced (rows x cols) family CipherSpec - the KNOT / RECTANGLE
class - into exactly that shape: the S-box goes to ``operators/Sbox.py`` (reused when
an identical table is already there, appended otherwise) and the permutation module
imports it. The generated module inlines only the per-version parameters and the
deterministic bit-sliced expansion (S-box column indices, row-shift permutation, LFSR
round constants).

`generate_primitive_source(spec)` returns ``(filename, source, sbox_appends)`` where
``sbox_appends`` is a list of ``(class_name, source)`` S-box class definitions the
caller should append to ``operators/Sbox.py`` (already filtered to ones not present).
"""

import ast

from agent.skills.cipher_spec import CipherSpec, _sanitize_identifier


def _read_operators_sbox_source():
    import operators.Sbox as _sbox_mod
    from pathlib import Path
    return Path(_sbox_mod.__file__).read_text(encoding="utf-8")


def _existing_sboxes(source):
    """Parse operators/Sbox.py -> {class_name: table_list} for every class that sets
    ``self.table = [literal]`` (all OCP S-boxes do)."""
    tables = {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return tables
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Assign):
                for target in sub.targets:
                    if (isinstance(target, ast.Attribute) and target.attr == "table"
                            and isinstance(target.value, ast.Name) and target.value.id == "self"):
                        try:
                            tables[node.name] = ast.literal_eval(sub.value)
                        except (ValueError, SyntaxError):
                            pass
    return tables


def _plan_sboxes(spec, cipher_base, existing):
    """Decide the S-box class name for each of the spec's S-boxes, reusing an existing
    class with an identical table or picking a free name to append.

    Returns a list aligned with ``spec.sbox_tables`` order of
    ``(sbox_key, class_name, append_source_or_None)``.
    """
    single = len(spec.sbox_tables) == 1
    known = dict(existing)  # class_name -> table
    plan = []
    for key, table in spec.sbox_tables.items():
        table = list(table)
        stem = cipher_base if single else f"{cipher_base}_{_sanitize_identifier(key)}"
        base_name = f"{stem}_Sbox"
        class_name, i = base_name, 1
        # advance past any same-named class that holds a DIFFERENT table
        while class_name in known and known[class_name] != table:
            i += 1
            class_name = f"{stem}{i}_Sbox"
        if class_name in known:  # identical table already defined -> reuse
            plan.append((key, class_name, None))
            continue
        n = max(1, (len(table) - 1).bit_length())
        source = (
            f"\n\nclass {class_name}(Sbox):  # auto-added by OCP-agent\n"
            f"    def __init__(self, input_vars, output_vars, ID=None):\n"
            f"        super().__init__(input_vars, output_vars, {n}, {n}, ID=ID)\n"
            f"        self.table = {table!r}\n"
        )
        known[class_name] = table
        plan.append((key, class_name, source))
    return plan


# Fixed bit-sliced expansion + LFSR helpers, emitted verbatim so the generated module
# stands alone. Mirrors CipherSpec.expand_bitsliced / _lfsr_constants (row 0 = S-box
# LSB, so index lists rows most-significant first; "l" is a left rotation, so output
# column c reads input column c-off).
_HELPERS_SRC = '''
    @staticmethod
    def _lfsr_constants(lfsr, count):
        """Fibonacci LFSR {width, taps, init}: each step left-shifts and feeds back
        the XOR of the tap bits. Returns `count` successive states."""
        width, taps, state = lfsr["width"], lfsr["taps"], lfsr.get("init", 1)
        mask, seq = (1 << width) - 1, []
        for _ in range(count):
            seq.append(state)
            feedback = 0
            for tap in taps:
                feedback ^= (state >> tap) & 1
            state = ((state << 1) | feedback) & mask
        return seq

    @staticmethod
    def _bitsliced_layers(rows, cols, offsets, direction, d, lfsr, nbr_rounds):
        total = rows * cols
        def widx(r, c):
            return r * cols + c
        sbox_index = [[widx(r, c) for r in reversed(range(rows))] for c in range(cols)]
        shift_table = [0] * total
        for r in range(rows):
            off = offsets[r] % cols
            for c in range(cols):
                src = (c - off) % cols if direction == "l" else (c + off) % cols
                shift_table[widx(r, c)] = widx(r, src)
        seq = KNOT_PLACEHOLDER._lfsr_constants(lfsr, nbr_rounds)
        rc_table = [[(seq[i] >> k) & 1 for k in range(d)] for i in range(nbr_rounds)]
        rc_mask = [1] * d + [None] * (total - d)
        return sbox_index, shift_table, rc_mask, rc_table
'''


def _layout_family_params(spec):
    """Resolve each version into concrete bit-sliced parameters, keyed by STATE SIZE
    (rows*cols bits) so the generated factory takes version=256 (not 'KNOT-256'), matching
    the other ciphers. Returns (versions_by_size, default_size)."""
    versions, default_size = {}, None
    for vname in spec.versions:
        member = spec.instantiate(vname)  # resolves $placeholders for this version
        size = member.layout["rows"] * member.layout["cols"]
        entry = {"rows": member.layout["rows"], "cols": member.layout["cols"],
                 "nbr_rounds": member.nbr_rounds}
        for layer in member.round_structure:
            p = layer.params or {}
            if layer.layer_type == "shift_rows":
                entry["offsets"] = p["offsets"]
                entry["direction"] = p.get("direction", "l")
            elif layer.layer_type == "add_round_constant" and p.get("lfsr"):
                entry["d"] = p["d"]
                entry["lfsr"] = p["lfsr"]
        versions[size] = entry
        if vname == spec.default_version:
            default_size = size
    if default_size is None:
        default_size = next(iter(versions))
    return versions, default_size


# layer_type -> the boolean/modular operator class emitted in the generated source
_SINGLE_OP_CLASS = {
    "xor": "XOR", "and": "AND", "or": "OR", "not": "NOT",
    "n_xor": "N_XOR", "andxor": "ANDXOR", "modadd": "ModAdd", "equal": "Equal",
}


def _layer_to_source(func, i, idx, layer, sbox_names, param_expr=None):
    """One OCP layer call as source, matching cipher_definition._apply_layer exactly. When
    `param_expr` is given (a source expression evaluating to the layer's params dict, used for
    round-dependent phase params), fields are read from it instead of inlined."""
    lt = layer.layer_type
    p = layer.params or {}

    def f(key):  # a param value: from the phase dict at runtime, or inlined literally
        return f'{param_expr}[{key!r}]' if param_expr is not None else repr(p.get(key))

    if lt == "rotation" or lt == "shift":
        call = "RotationLayer" if lt == "rotation" else "ShiftLayer"
        tag = "ROT" if lt == "rotation" else "SH"
        _nd = lambda d: {"left": "l", "right": "r"}.get(d, d)  # OCP wants 'l'/'r'
        if p.get("rotations") is not None or (param_expr is not None and "rotations" in p):
            if param_expr is None:
                rots = [[_nd(r[0])] + list(r[1:]) for r in p["rotations"]]
                return f'{func}.{call}("{tag}_{idx}", {i}, {idx}, {rots!r})'
            return f'{func}.{call}("{tag}_{idx}", {i}, {idx}, {f("rotations")})'
        vec = [_nd(p["direction"]), p["amount"], p["word_index"]]
        if p.get("out_index") is not None:
            vec.append(p["out_index"])
        return f'{func}.{call}("{tag}_{idx}", {i}, {idx}, {vec!r})'
    if lt in _SINGLE_OP_CLASS:
        return (f'{func}.SingleOperatorLayer("{lt.upper()}_{idx}", {i}, {idx}, '
                f'{_SINGLE_OP_CLASS[lt]}, {f("input_indices")}, {f("output_indices")})')
    if lt == "sbox":
        return (f'{func}.SboxLayer("SB_{idx}", {i}, {idx}, {sbox_names[p["sbox_name"]]}, '
                f'mask={p.get("mask")!r}, index={p.get("index")!r})')
    if lt == "permutation":
        return f'{func}.PermutationLayer("P_{idx}", {i}, {idx}, {p["table"]!r})'
    if lt == "matrix":
        return (f'{func}.MatrixLayer("MAT_{idx}", {i}, {idx}, {p["matrix"]!r}, '
                f'{p["indices"]!r}, polynomial={p.get("polynomial")!r})')
    if lt == "gf2_linear":
        return (f'{func}.GF2Linear_TransLayer("GF2_{idx}", {i}, {idx}, {p["index_in"]!r}, '
                f'{p.get("index_out", p["index_in"])!r}, {p["matrix"]!r}, '
                f'constants={p.get("constants")!r})')
    if lt == "add_round_key":
        op = "XOR" if p.get("operator", "xor") == "xor" else "ModAdd"
        return f'{func}.AddRoundKeyLayer("ARK_{idx}", {i}, {idx}, {op}, SK, mask={p.get("mask")!r})'
    if lt == "add_constant":
        return (f'{func}.AddConstantLayer("C_{idx}", {i}, {idx}, {p.get("add_type", "xor")!r}, '
                f'{p["constant_mask"]!r}, {p["constant_table"]!r})')
    if lt == "add_identity":
        return f'{func}.AddIdentityLayer("ID_{idx}", {i}, {idx})'
    raise ValueError(f"primitive export does not support layer '{lt}' yet.")


def _wrap_list_literal(lst, indent, per_line=16):
    """A Python list literal split over multiple lines (per_line items each) so long
    test-vector rows never become one giant line."""
    inner = indent + "    "
    rows = [", ".join(str(x) for x in lst[i:i + per_line])
            for i in range(0, len(lst), per_line)]
    return "[\n" + ",\n".join(inner + r for r in rows) + "\n" + indent + "]"


def _emit_test_vector_appends(test_vectors, is_block, ind, word_bitsize=None, key_word_bitsize=None):
    """The plaintext/key/ciphertext + self.test_vectors.append(...) lines at indent `ind`.

    In the generic path vectors are already integer word lists (word_bitsize omitted). The layout
    exporter passes word_bitsize=1 so a bit-sliced family's RAW hex vectors split into their bits.
    """
    from agent.skills.cipher_definition import _normalize_test_vectors
    tvs = _normalize_test_vectors(test_vectors, "blockcipher" if is_block else "permutation",
                                  word_bitsize, key_word_bitsize)
    lines = []
    for tv in tvs:
        inputs, output = tv[0], tv[1]
        lines.append(f"{ind}plaintext = " + _wrap_list_literal(inputs[0], ind))
        if is_block and len(inputs) == 2:
            lines.append(f"{ind}key = " + _wrap_list_literal(inputs[1], ind))
            lines.append(f"{ind}ciphertext = " + _wrap_list_literal(output, ind))
            lines.append(f"{ind}self.test_vectors.append([[plaintext, key], ciphertext])")
        else:
            lines.append(f"{ind}ciphertext = " + _wrap_list_literal(output, ind))
            lines.append(f"{ind}self.test_vectors.append([[plaintext], ciphertext])")
    return lines


def _emit_test_vectors(test_vectors, is_block):
    """Source lines for a gen_test_vectors(self) method, like the built-in primitives."""
    appends = _emit_test_vector_appends(test_vectors, is_block, "        ")
    return ["", "    def gen_test_vectors(self):"] + (appends or ["        pass"])


def _xor_share_count(extract, periodic):
    """Number of shares a combined-subkey ({"xor": [...]}) entry XORs (Midori WK n=2,
    SKINNY-384 subtweakey n=3). 1 when there is no xor entry."""
    if not periodic:
        return 1
    return max((len(e["xor"]) for e in extract if isinstance(e, dict) and "xor" in e), default=1)


def _emit_xor_reduce(sk_words, xor_n, indent):
    """Source for the SUBKEYS reduce layer: XOR the xor_n extracted shares down to sk_words."""
    if xor_n == 2:
        return (f"{indent}SK.SingleOperatorLayer('SK_XOR', i, 1, XOR, "
                f"[[j, {sk_words} + j] for j in range({sk_words})], list(range({sk_words})))")
    return (f"{indent}SK.SingleOperatorLayer('SK_XOR', i, 1, N_XOR, "
            f"[[k * {sk_words} + j for k in range({xor_n})] for j in range({sk_words})], "
            f"list(range({sk_words})))")


def _block_key_config(inst):
    """(ks_layers, kwb, knw, knt, extract, periodic, has_xor, sk_words, sk_layers, sk_temp, xor_n)."""
    kwb = inst.key_word_bitsize or inst.word_bitsize
    knw = inst.key_nbr_words or (inst.key_size // kwb)
    ks_layers = len(inst.key_schedule) if inst.key_schedule else 1
    extract = inst.key_extract_indices

    def _entry_words(e):
        return len(e["xor"][0]) if isinstance(e, dict) else len(e)

    periodic = bool(extract) and isinstance(extract[0], (list, dict))
    xor_n = _xor_share_count(extract, periodic)
    has_xor = xor_n >= 2
    sk_words = _entry_words(extract[0]) if periodic else len(extract)
    return (ks_layers, kwb, knw, inst.key_nbr_temp_words, extract, periodic,
            has_xor, sk_words, 2 if has_xor else 1,
            (xor_n - 1) * sk_words if has_xor else 0, xor_n)


def _emit_block_body(inst, sbox_names, ind):
    """Block-cipher __init__ body (config + super + extraction + key schedule + round
    function) at indent `ind`. Shared by the single-version and per-version emitters."""
    wb, nw, nt, nr = inst.word_bitsize, inst.nbr_words, inst.nbr_temp_words, inst.nbr_rounds
    s_nbr_layers = len(inst.round_structure)
    (ks_layers, kwb, knw, knt, extract, periodic,
     has_xor, sk_words, sk_layers, sk_temp, xor_n) = _block_key_config(inst)
    ii = ind + "    "
    B = [
        f"{ind}if nbr_rounds is None: nbr_rounds = {nr}",
        f"{ind}s_config = [{s_nbr_layers}, {nw}, {nt}, {wb}]",
        f"{ind}k_config = [{ks_layers}, {knw}, {knt}, {kwb}]",
        f"{ind}sk_config = [{sk_layers}, {sk_words}, {sk_temp}, {wb}]",
        f"{ind}super().__init__(name, p_input, k_input, c_output, nbr_rounds, "
        f"nbr_rounds, s_config, k_config, sk_config)",
        f'{ind}S = self.functions["PERMUTATION"]',
        f'{ind}KS = self.functions["KEY_SCHEDULE"]',
        f'{ind}SK = self.functions["SUBKEYS"]',
        f"{ind}for i in range(1, nbr_rounds + 1):",
    ]
    if has_xor:
        B += [
            f"{ii}_phases = {extract!r}",
            f"{ii}e = _phases[(i - 1) % {len(extract)}]",
            f"{ii}if isinstance(e, dict):",
            f"{ii}    flat = [idx for sh in e['xor'] for idx in sh]",
            f"{ii}    SK.ExtractionLayer('SK_EX', i, 0, flat, KS.vars[i][0])",
            _emit_xor_reduce(sk_words, xor_n, ii + "    "),
            f"{ii}else:",
            f"{ii}    SK.ExtractionLayer('SK_EX', i, 0, list(e) * {xor_n}, KS.vars[i][0])",
            f"{ii}    SK.AddIdentityLayer('SK_ID', i, 1)",
        ]
    elif periodic:
        B += [
            f"{ii}_phases = {extract!r}",
            f"{ii}SK.ExtractionLayer('SK_EX', i, 0, _phases[(i - 1) % {len(extract)}], KS.vars[i][0])",
        ]
    else:
        B.append(f"{ii}SK.ExtractionLayer('SK_EX', i, 0, {extract!r}, KS.vars[i][0])")
    B.append(f"{ind}for i in range(1, nbr_rounds):")
    if inst.key_schedule:
        B += _emit_layers("KS", inst.key_schedule, sbox_names, ii)
    else:
        B.append(f'{ii}KS.AddIdentityLayer("K_ID", i, 0)')
    B.append(f"{ind}for i in range(1, nbr_rounds + 1):")
    B += _emit_layers("S", inst.round_structure, sbox_names, ii)
    return B


def _emit_versioned_block(spec):
    """Self-contained block-cipher file with a `version` parameter (like present.py/led.py):
    ONE class whose __init__ dispatches on the block size to each version's config + layers,
    a VERSIONS map for the factory, and a factory that sizes plaintext/key/state per version.
    `version` may be an int block size or a [block, key] pair (the block size selects it)."""
    cls_base = _sanitize_identifier(spec.name)
    cls = f"{cls_base}_block_cipher"
    factory = f"{cls_base.upper()}_BLOCKCIPHER"
    filename = f"{cls_base.lower()}.py"
    VER = cls_base.upper()

    # instantiate every version and lower it, so each branch is fully concrete
    insts = {}
    for vname in spec.versions:
        insts[vname] = spec.instantiate(vname).compile()   # same canonical lowering chain

    # plan S-boxes across all versions (union), so the file imports/appends each once
    existing = _existing_sboxes(_read_operators_sbox_source())
    sbox_names, sbox_appends, seen = {}, [], set()
    for inst in insts.values():
        for key, name, src in _plan_sboxes(inst, cls_base, existing):
            sbox_names[key] = name
            if src and name not in seen:
                sbox_appends.append((name, src)); seen.add(name)
    imported_sboxes = sorted(set(sbox_names.values()))

    # operators used across versions (incl. XOR for a combined-subkey extraction)
    used = set()
    for inst in insts.values():
        for lyr in list(inst.round_structure) + list(inst.key_schedule or []):
            if lyr.layer_type in _SINGLE_OP_CLASS:
                used.add(_SINGLE_OP_CLASS[lyr.layer_type])
            if lyr.layer_type == "add_round_key":
                used.add("XOR" if (lyr.params or {}).get("operator", "xor") == "xor" else "ModAdd")
        if inst.key_extract_indices and any(isinstance(e, dict) and "xor" in e
                                            for e in inst.key_extract_indices):
            periodic = isinstance(inst.key_extract_indices[0], (list, dict))
            used.add("XOR" if _xor_share_count(inst.key_extract_indices, periodic) == 2 else "N_XOR")
    bool_ops = sorted(o for o in used if o != "ModAdd")
    need_modadd = "ModAdd" in used

    def _bs(inst):
        return inst.block_size or inst.word_bitsize * inst.nbr_words

    def _bk(inst):                       # (block, key) - the version identity, like present.py
        return (_bs(inst), inst.key_size)

    dims = {}
    for inst in insts.values():
        kwb = inst.key_word_bitsize or inst.word_bitsize
        dims[_bk(inst)] = {"wb": inst.word_bitsize, "nw": inst.nbr_words,
                           "kwb": kwb, "knw": inst.key_nbr_words or (inst.key_size // kwb)}
    default_bk = _bk(insts[spec.default_version]) if spec.default_version in insts else next(iter(dims))
    has_tv = any(inst.test_vectors for inst in insts.values())

    L = [
        f'"""{spec.name} - OCP primitive auto-generated by OCP-agent. Self-contained,',
        'version-parameterized (version = [block_bitsize, key_bitsize], like present.py/led.py).',
        f'Versions: {", ".join(f"{n} {_bk(i)}" for n, i in insts.items())}."""',
        "from primitives.primitives import Block_cipher",
    ]
    if imported_sboxes:
        L.append("from operators.Sbox import " + ", ".join(imported_sboxes))
    if bool_ops:
        L.append("from operators.boolean_operators import " + ", ".join(bool_ops))
    if need_modadd:
        L.append("from operators.modular_operators import ModAdd")
    # A block cipher's version is a [block, key] pair (never a bare block size - that is the
    # permutation convention). Match the built-in block ciphers: normalize to a tuple and
    # validate against the known versions.
    L += ["import variables.variables as var", "", f"{VER}_VERSIONS = {dims!r}",
          f"{VER}_DEFAULT = {default_bk!r}", "", "",
          f"def _{VER.lower()}_sel(version):",
          f"    sel = tuple(version) if isinstance(version, (list, tuple)) else None",
          f"    if sel not in {VER}_VERSIONS:",
          f"        raise ValueError(f\"unsupported {cls_base} version {{version!r}}; expected \"",
          f"                         f\"one of {{[list(v) for v in {VER}_VERSIONS]}}\")",
          f"    return sel",
          "", ""]

    L.append(f"class {cls}(Block_cipher):")
    L.append("    def __init__(self, name, version, p_input, k_input, c_output, nbr_rounds=None):")
    L.append(f"        sel = _{VER.lower()}_sel(version)")
    for k, inst in enumerate(insts.values()):
        L.append(f"        {'if' if k == 0 else 'elif'} sel == {_bk(inst)!r}:")
        L += _emit_block_body(inst, sbox_names, "            ")
    L.append("        else:")
    L.append('            raise ValueError(f"unsupported version {version}")')
    if has_tv:
        L.append("        self.gen_test_vectors(version)")

    L += ["", "    def gen_test_vectors(self, version):", "        self.test_vectors = []",
          f"        sel = _{VER.lower()}_sel(version)"]
    from agent.skills.cipher_definition import (
        _normalize_test_vectors, _drop_cross_variant_vectors, _effective_word_sizes,
        _effective_state_counts,
    )
    emitted_tv = False
    for inst in insts.values():
        if not inst.test_vectors:
            continue
        # inst.test_vectors may be RAW hex and carry the WHOLE family's KATs (instantiate copies
        # the top-level vectors onto every member); split by this version's word size and keep
        # only this version's (matching state size) vectors.
        wb, kwb = _effective_word_sizes(inst)
        ns, nk = _effective_state_counts(inst)
        norm = _normalize_test_vectors(inst.test_vectors, "blockcipher", wb, kwb)
        kept, _ = _drop_cross_variant_vectors(norm, ns, nk, "blockcipher")
        if not kept:
            continue
        L.append(f"        {'if' if not emitted_tv else 'elif'} sel == {_bk(inst)!r}:")
        L += _emit_test_vector_appends(kept, True, "            ")
        emitted_tv = True
    if not emitted_tv:
        L.append("        pass")

    L += ["", "",
          f"def {factory}(r=None, version=None, copy_operator=False):",
          f"    if version is None: version = {VER}_DEFAULT",
          f"    v = {VER}_VERSIONS[_{VER.lower()}_sel(version)]",
          '    p = [var.Variable(v["wb"], ID="p" + str(i)) for i in range(v["nw"])]',
          '    k = [var.Variable(v["kwb"], ID="k" + str(i)) for i in range(v["knw"])]',
          '    c = [var.Variable(v["wb"], ID="c" + str(i)) for i in range(v["nw"])]',
          f'    cipher = {cls}("{cls_base}", version, p, k, c, nbr_rounds=r)',
          "    cipher.post_initialization(copy_operator=copy_operator)",
          "    return cipher", ""]

    catalog_entry = {cls_base.lower(): {
        "module": f"primitives.{cls_base.lower()}",
        "factories": {"blockcipher": factory},
        # default_version must use the SAME [block,key] convention as valid_versions and the
        # generated factory (version=[block,key]) - NOT the spec's version NAME (e.g. "Midori64"),
        # which the factory rejects. default_bk is that pair for the default version.
        "default_version": {"blockcipher": default_bk},
        "valid_versions": {"blockcipher": list(dims.keys())}}}
    return filename, "\n".join(L), sbox_appends, catalog_entry


def _active_condition(layer):
    """Source-level condition for a round-dependent layer, or None if always active."""
    def resolve(rounds):
        # Round numbers are known at generation time: a positive literal is itself; a negative one
        # counts from the end (-1 = last round = nbr_rounds). Resolve now instead of emitting the
        # runtime `(r if r > 0 else nbr_rounds+1+r)` conditional for every entry.
        def one(r):
            if isinstance(r, int):
                if r > 0:
                    return str(r)
                off = 1 + r                       # -1 -> 0 (nbr_rounds), -2 -> -1, ...
                return "nbr_rounds" if off == 0 else f"nbr_rounds + ({off})"
            return f"({r} if {r} > 0 else nbr_rounds + 1 + ({r}))"   # symbolic (rare)
        return "{" + ", ".join(one(r) for r in rounds) + "}"
    if layer.only_rounds:
        return "i in " + resolve(layer.only_rounds)
    if layer.except_rounds:
        return "i not in " + resolve(layer.except_rounds)
    return None


def _emit_layers(func, layers, sbox_names, indent):
    """Source lines applying each layer inside a `for i in ...` loop, filling inactive
    rounds of a round-dependent layer with an identity so every round keeps its layer count."""
    lines = []
    for idx, layer in enumerate(layers):
        cond = _active_condition(layer)
        if layer.phase_params:
            # Round-dependent params (ARX columns/diagonals, Forro's 8 selections): pick the
            # phase at runtime, then emit the call reading fields from that phase dict.
            period = len(layer.phase_params)
            var = f"_ph{idx}"
            pre = [f"{indent}{var} = {layer.phase_params!r}[(i - 1) % {period}]"]
            base = _layer_to_source(func, "i", idx, layer, sbox_names, param_expr=var)
        else:
            pre = []
            base = _layer_to_source(func, "i", idx, layer, sbox_names)
        if cond:
            lines += pre
            lines.append(f"{indent}if {cond}:")
            lines.append(f"{indent}    {base}")
            lines.append(f"{indent}else:")
            lines.append(f'{indent}    {func}.AddIdentityLayer("ID_{idx}", i, {idx})')
        else:
            lines += pre
            lines.append(f"{indent}{base}")
    return lines


def _generate_generic_primitive_source(spec):
    """Self-contained OCP primitive source for any non-layout CipherSpec (word-level or bit,
    permutation or block cipher). Emits an OCP Primitive subclass that builds itself layer by
    layer - like the hand-written built-ins (skinny.py etc.) - with no dependency on the agent
    package. A versioned family is exported at its default version (concrete)."""
    if spec.versions:
        # A versioned block cipher becomes ONE file with a `version` parameter (like
        # present.py/led.py) instead of flattening to the default version's own file.
        if spec.cipher_type == "blockcipher":
            return _emit_versioned_block(spec)
        spec = spec.instantiate(spec.default_version or next(iter(spec.versions)))
    spec = spec.compile()   # the SAME canonical lowering chain the builders use

    cls_base = _sanitize_identifier(spec.name)
    is_block = spec.cipher_type == "blockcipher"
    kind = "blockcipher" if is_block else "permutation"
    cls = f"{cls_base}_{'block_cipher' if is_block else 'permutation'}"
    factory = f"{cls_base.upper()}_{'BLOCKCIPHER' if is_block else 'PERMUTATION'}"
    filename = f"{cls_base.lower()}.py"

    existing = _existing_sboxes(_read_operators_sbox_source())
    plan = _plan_sboxes(spec, cls_base, existing)
    sbox_names = {key: name for key, name, _ in plan}
    sbox_appends = [(name, src) for _, name, src in plan if src]
    imported_sboxes = sorted({name for _, name, _ in plan})

    # boolean/modular operator classes actually used, for imports
    all_layers = list(spec.round_structure) + list(spec.key_schedule or [])
    used = set()
    for lyr in all_layers:
        if lyr.layer_type in _SINGLE_OP_CLASS:
            used.add(_SINGLE_OP_CLASS[lyr.layer_type])
        if lyr.layer_type == "add_round_key":
            used.add("XOR" if (lyr.params or {}).get("operator", "xor") == "xor" else "ModAdd")
    # A combined subkey (Midori WK = K0 (+) K1; SKINNY-384 TK1^TK2^TK3) is built with an
    # XOR / N_XOR reduce inside SUBKEYS.
    if is_block and spec.key_extract_indices and any(
            isinstance(e, dict) and "xor" in e for e in spec.key_extract_indices):
        periodic = isinstance(spec.key_extract_indices[0], (list, dict))
        used.add("XOR" if _xor_share_count(spec.key_extract_indices, periodic) == 2 else "N_XOR")
    bool_ops = sorted(o for o in used if o not in ("ModAdd", "Equal"))
    need_modadd = "ModAdd" in used
    need_equal = "Equal" in used                     # ARX feed-forward copy (operators.operators)

    round_desc = "; ".join(l.layer_type for l in spec.round_structure)
    L = []
    L.append(f'"""{spec.name} - OCP primitive auto-generated by OCP-agent from a user cipher')
    L.append(f'definition. Self-contained (no agent deps). Round: {round_desc}."""')
    L.append("from primitives.primitives import " + ("Block_cipher" if is_block else "Permutation"))
    if imported_sboxes:
        L.append("from operators.Sbox import " + ", ".join(imported_sboxes))
    if bool_ops:
        L.append("from operators.boolean_operators import " + ", ".join(bool_ops))
    if need_modadd:
        L.append("from operators.modular_operators import ModAdd")
    if need_equal:
        L.append("from operators.operators import Equal")
    L.append("import variables.variables as var")
    L.append("")
    L.append("")

    wb, nw, nt, nr = spec.word_bitsize, spec.nbr_words, spec.nbr_temp_words, spec.nbr_rounds
    s_nbr_layers = len(spec.round_structure)

    if is_block:
        kwb = spec.key_word_bitsize or spec.word_bitsize
        knw = spec.key_nbr_words or (spec.key_size // kwb)
        knt = spec.key_nbr_temp_words
        ks_layers = len(spec.key_schedule) if spec.key_schedule else 1
        extract = spec.key_extract_indices

        def _entry_words(e):
            if isinstance(e, dict):
                return len(e["words"]) if "from" in e else len(e["xor"][0])
            return len(e)

        periodic = bool(extract) and isinstance(extract[0], (list, dict))
        xor_n = _xor_share_count(extract, periodic)
        has_xor = xor_n >= 2
        has_from = periodic and any(isinstance(e, dict) and "from" in e for e in extract)
        sk_words = _entry_words(extract[0]) if periodic else len(extract)
        sk_layers = 2 if has_xor else 1
        sk_temp = (xor_n - 1) * sk_words if has_xor else 0
        # Simon's key schedule runs fewer rounds than the cipher; k_rounds tracks nbr_rounds
        # so a caller can still vary the round count.
        k_off = (nr - spec.key_nbr_rounds) if spec.key_nbr_rounds is not None else 0

        L.append(f"class {cls}(Block_cipher):")
        L.append("    def __init__(self, name, p_input, k_input, c_output, nbr_rounds=None):")
        L.append(f"        if nbr_rounds is None: nbr_rounds = {nr}")
        L.append(f"        k_rounds = nbr_rounds - {k_off}")
        L.append(f"        s_config = [{s_nbr_layers}, {nw}, {nt}, {wb}]")
        L.append(f"        k_config = [{ks_layers}, {knw}, {knt}, {kwb}]")
        L.append(f"        sk_config = [{sk_layers}, {sk_words}, {sk_temp}, {wb}]")
        L.append("        super().__init__(name, p_input, k_input, c_output, nbr_rounds, "
                 "k_rounds, s_config, k_config, sk_config)")
        L.append('        S = self.functions["PERMUTATION"]')
        L.append('        KS = self.functions["KEY_SCHEDULE"]')
        L.append('        SK = self.functions["SUBKEYS"]')
        # subkey extraction (round-dependent when periodic; an entry may be {"xor": [s0, s1]}
        # for a combined subkey like Midori's WK = K0 (+) K1, built inside SUBKEYS)
        L.append("        for i in range(1, nbr_rounds + 1):")
        if has_xor:
            L.append(f"            _phases = {extract!r}")
            L.append(f"            e = _phases[(i - 1) % {len(extract)}]")
            L.append("            if isinstance(e, dict):")
            L.append("                flat = [idx for sh in e['xor'] for idx in sh]")
            L.append("                SK.ExtractionLayer('SK_EX', i, 0, flat, KS.vars[i][0])")
            L.append(_emit_xor_reduce(sk_words, xor_n, "                "))
            L.append("            else:")
            L.append(f"                SK.ExtractionLayer('SK_EX', i, 0, list(e) * {xor_n}, KS.vars[i][0])")
            L.append("                SK.AddIdentityLayer('SK_ID', i, 1)")
        elif has_from:
            L.append(f"            _phases = {extract!r}")
            L.append(f"            e = _phases[(i - 1) % {len(extract)}]")
            L.append("            if isinstance(e, dict):")   # read a historical KS state
            L.append("                SK.ExtractionLayer('SK_EX', i, 0, e['words'], KS.vars[e['from']][0])")
            L.append("            else:")
            L.append("                SK.ExtractionLayer('SK_EX', i, 0, e, KS.vars[i][0])")
        elif periodic:
            L.append(f"            _phases = {extract!r}")
            L.append(f"            SK.ExtractionLayer('SK_EX', i, 0, "
                     f"_phases[(i - 1) % {len(extract)}], KS.vars[i][0])")
        else:
            L.append(f"            SK.ExtractionLayer('SK_EX', i, 0, {extract!r}, KS.vars[i][0])")
        # key schedule
        L.append("        for i in range(1, k_rounds):")
        if spec.key_schedule:
            L.extend(_emit_layers("KS", spec.key_schedule, sbox_names, "            "))
        else:
            L.append('            KS.AddIdentityLayer("K_ID", i, 0)')
        # round function
        L.append("        for i in range(1, nbr_rounds + 1):")
        L.extend(_emit_layers("S", spec.round_structure, sbox_names, "            "))
        if spec.test_vectors:
            L.append("        self.gen_test_vectors()")   # populate in the class, not the factory
            L.extend(_emit_test_vectors(spec.test_vectors, is_block))
        L.append("")
        L.append("")
        L.append(f"def {factory}(r=None, version=None, copy_operator=False):")
        L.append(f'    p = [var.Variable({wb}, ID="p" + str(i)) for i in range({nw})]')
        L.append(f'    k = [var.Variable({kwb}, ID="k" + str(i)) for i in range({knw})]')
        L.append(f'    c = [var.Variable({wb}, ID="c" + str(i)) for i in range({nw})]')
        L.append(f'    cipher = {cls}("{cls_base}", p, k, c, nbr_rounds=r)')
    else:
        L.append(f"class {cls}(Permutation):")
        L.append("    def __init__(self, name, s_input, s_output, nbr_rounds=None):")
        L.append(f"        if nbr_rounds is None: nbr_rounds = {nr}")
        L.append(f"        super().__init__(name, s_input, s_output, nbr_rounds, "
                 f"[{s_nbr_layers}, {nw}, {nt}, {wb}])")
        L.append('        S = self.functions["PERMUTATION"]')
        L.append("        for i in range(1, nbr_rounds + 1):")
        L.extend(_emit_layers("S", spec.round_structure, sbox_names, "            "))
        if spec.test_vectors:
            L.append("        self.gen_test_vectors()")   # populate in the class, not the factory
            L.extend(_emit_test_vectors(spec.test_vectors, is_block))
        L.append("")
        L.append("")
        L.append(f"def {factory}(r=None, version=None, copy_operator=False):")
        L.append(f'    inp = [var.Variable({wb}, ID="in" + str(i)) for i in range({nw})]')
        L.append(f'    out = [var.Variable({wb}, ID="out" + str(i)) for i in range({nw})]')
        L.append(f'    cipher = {cls}("{cls_base}", inp, out, nbr_rounds=r)')
    L.append("    cipher.post_initialization(copy_operator=copy_operator)")
    L.append("    return cipher")
    L.append("")

    src = "\n".join(L)
    catalog_entry = {
        cls_base.lower(): {
            "module": f"primitives.{cls_base.lower()}",
            "factories": {kind: factory},
            "default_version": {kind: spec.default_version},
            "valid_versions": {kind: []},
        }
    }
    return filename, src, sbox_appends, catalog_entry


def generate_primitive_source(spec):
    """Return (filename, source, sbox_appends, catalog_entry) for a CipherSpec. Layout
    families get a self-contained source; everything else goes through the generic exporter."""
    if isinstance(spec, dict):
        spec = CipherSpec.from_dict(spec)
    # Materialize {"code": ...} structure params to concrete lists so the exported primitive
    # stands alone (a non-versioned spec; a versioned family resolves per member on instantiate).
    if not spec.versions and spec._has_code_params():
        spec = spec.resolve_code_params()
    # Bit-sliced layout permutation families get a self-contained, hand-written-style
    # primitive (below). Everything else - word-level permutations, block ciphers, plain
    # or versioned - gets a generic primitive that inlines the spec and rebuilds through
    # the agent's builders, reusing all the layer / round-dependent / whitening / key-
    # schedule handling instead of re-implementing per-layer source emission.
    if not (spec.layout and spec.versions and spec.cipher_type == "permutation"):
        return _generate_generic_primitive_source(spec)

    cls_base = _sanitize_identifier(spec.name)          # e.g. "KNOT"
    perm_cls = f"{cls_base}_permutation"
    factory = f"{cls_base.upper()}_PERMUTATION"
    filename = f"{cls_base.lower()}.py"                   # e.g. "knot.py"

    existing = _existing_sboxes(_read_operators_sbox_source())
    plan = _plan_sboxes(spec, cls_base, existing)        # aligned with sbox_tables order
    key_to_class = {key: name for key, name, _ in plan}
    sbox_appends = [(name, src) for _, name, src in plan if src]
    imported = sorted({name for _, name, _ in plan})

    versions, default_version = _layout_family_params(spec)   # keyed by state size (e.g. 256)

    layer_calls = []
    for idx, layer in enumerate(spec.round_structure):
        lt = layer.layer_type
        if lt == "add_round_constant":
            layer_calls.append(f'            S.AddConstantLayer("C", i, {idx}, "xor", rc_mask, rc_table)')
        elif lt == "subcolumn_sbox":
            cls = key_to_class[(layer.params or {})["sbox_name"]]
            layer_calls.append(f'            S.SboxLayer("SB", i, {idx}, {cls}, index=sbox_index)')
        elif lt == "shift_rows":
            layer_calls.append(f'            S.PermutationLayer("P", i, {idx}, shift_table)')
        else:
            raise ValueError(f"primitive export does not support layout layer '{lt}' yet.")
    nbr_layers = len(spec.round_structure)

    # Per-version designer KATs, inlined into gen_test_vectors and keyed by STATE SIZE
    # (the version identity the factory takes). Only appended when the built object runs
    # the design's full round count, so a partial-round instantiation gets no bogus KAT.
    from agent.skills.cipher_definition import _normalize_test_vectors, _drop_cross_variant_vectors
    tv_by_size = {}
    if spec.versions:
        for vname in spec.versions:
            member = spec.instantiate(vname)
            size = member.layout["rows"] * member.layout["cols"]
            if not member.test_vectors:
                continue
            # instantiate() carries ALL of the family's top-level KATs (256/384/512-bit) onto
            # every member; keep only THIS version's (bit length == its state size). Vectors are
            # bit-sliced (word_bitsize=1); normalize the hex to bits, then drop the other sizes.
            norm = _normalize_test_vectors(member.test_vectors, "permutation", 1, 1)
            kept, _ = _drop_cross_variant_vectors(norm, size, 0, "permutation")
            if kept:
                tv_by_size.setdefault(size, kept)
    elif spec.test_vectors:
        tv_by_size[spec.layout["rows"] * spec.layout["cols"]] = spec.test_vectors

    if tv_by_size:
        _tvl = ["    def gen_test_vectors(self):", "        self.test_vectors = []"]
        for k, size in enumerate(tv_by_size):
            full = versions[size]["nbr_rounds"]
            _tvl.append(f"        {'if' if k == 0 else 'elif'} self._tv_version == {size}"
                        f" and self.nbr_rounds == {full}:")
            # A bit-sliced layout family's word is 1 bit, so its hex KATs split into bits here.
            _tvl += _emit_test_vector_appends(tv_by_size[size], False, "            ", word_bitsize=1)
        gen_tv_body = chr(10).join(_tvl)
        tv_version_line = f"\n        self._tv_version = version or {perm_cls.upper()}_DEFAULT_VERSION"
    else:
        gen_tv_body = "    def gen_test_vectors(self):\n        pass"
        tv_version_line = ""

    helpers = _HELPERS_SRC.replace("KNOT_PLACEHOLDER", perm_cls)
    round_desc = chr(10).join(
        "  " + str(i + 1) + ". " + layer.layer_type
        for i, layer in enumerate(spec.round_structure)
    )
    VER = perm_cls.upper()

    src = f'''"""{spec.name} - OCP primitive auto-generated by OCP-agent from a user cipher definition.

Bit-sliced permutation family (rows x cols state, S-box down each column, per-row
rotation, LFSR round constants). Each round applies, in order:
{round_desc}
"""

from primitives.primitives import Permutation
from operators.Sbox import {", ".join(imported)}
import variables.variables as var


# Per-version parameters keyed by STATE SIZE in bits (rows x cols): call the factory with
# version=256 / 384 / 512, like the other ciphers. nbr_rounds is the design's full rounds.
{VER}_VERSIONS = {versions!r}
{VER}_DEFAULT_VERSION = {default_version!r}


class {perm_cls}(Permutation):
    def __init__(self, name, s_input, s_output, version=None, nbr_rounds=None):
        params = {VER}_VERSIONS[version or {VER}_DEFAULT_VERSION]
        rows, cols = params["rows"], params["cols"]
        total = rows * cols
        if nbr_rounds is None:
            nbr_rounds = params["nbr_rounds"]
        super().__init__(name, s_input, s_output, nbr_rounds, [{nbr_layers}, total, 0, 1])
        S = self.functions["PERMUTATION"]
        sbox_index, shift_table, rc_mask, rc_table = self._bitsliced_layers(
            rows, cols, params["offsets"], params.get("direction", "l"),
            params["d"], params["lfsr"], nbr_rounds,
        )
        for i in range(1, nbr_rounds + 1):
{chr(10).join(layer_calls)}{tv_version_line}

{gen_tv_body}
{helpers}

def {factory}(r=None, version=None, copy_operator=False):
    version = version or {VER}_DEFAULT_VERSION
    params = {VER}_VERSIONS[version]
    n = params["rows"] * params["cols"]
    my_input = [var.Variable(1, ID="in" + str(i)) for i in range(n)]
    my_output = [var.Variable(1, ID="out" + str(i)) for i in range(n)]
    my_permutation = {perm_cls}("{cls_base}_PERM", my_input, my_output, version=version, nbr_rounds=r)
    my_permutation.gen_test_vectors()
    my_permutation.post_initialization(copy_operator=copy_operator)
    return my_permutation
'''
    # Catalog entry so the built cipher is usable by name like a built-in
    # (cipher_instantiation merges this into CIPHER_CATALOG).
    catalog_entry = {
        cls_base.lower(): {
            "module": f"primitives.{cls_base.lower()}",
            "factories": {"permutation": factory},
            "default_version": {"permutation": default_version},
            "valid_versions": {"permutation": list(versions.keys())},
        }
    }
    return filename, src, sbox_appends, catalog_entry
