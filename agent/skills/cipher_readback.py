"""Deterministic human-readable read-back of a CipherSpec.

Turns the structured spec that will *actually* be built back into plain English so
a user can confirm the extraction matches their intent, independent of any LLM.
Because it renders the machine's real interpretation (not a second LLM paraphrase),
it surfaces extraction mistakes. Shared by the dialogue REVIEW step and the
text-first draft.
"""

from agent.skills.cipher_spec import CipherSpec, LayerSpec, _resolve_placeholders


def _state_bits(spec, overrides, params):
    """Best-effort state size in bits for a (possibly parameterized/bit-sliced)
    spec, resolving "$name" placeholders from a version's params. Returns None when
    it cannot be pinned down (e.g. an unresolved placeholder)."""
    if spec.layout:
        rows = _resolve_placeholders(spec.layout.get("rows"), params)
        cols = _resolve_placeholders(spec.layout.get("cols"), params)
        if isinstance(rows, int) and isinstance(cols, int):
            return rows * cols
        return None
    block_size = overrides.get("block_size", spec.block_size) if overrides else spec.block_size
    return _resolve_placeholders(block_size, params)


def _flat(groups):
    return ", ".join(
        str(i) for g in (groups or []) for i in (g if isinstance(g, list) else [g])
    )


def _round_scope(layer):
    """Human note for a layer that runs in only some rounds, else ''."""
    def _fmt(rounds):
        return ", ".join(("last" if r == -1 else str(r)) for r in rounds)
    if getattr(layer, "only_rounds", None):
        return f" (only in round(s) {_fmt(layer.only_rounds)}; identity otherwise)"
    if getattr(layer, "except_rounds", None):
        return f" (skipped in round(s) {_fmt(layer.except_rounds)}; identity there)"
    return ""


def describe_layer(layer):
    """One-line English description of a single LayerSpec (dict or object)."""
    if isinstance(layer, dict):
        layer = LayerSpec.from_dict(layer)
    return _describe_layer_core(layer) + _round_scope(layer)


def _describe_layer_core(layer):
    lt = layer.layer_type
    p = layer.params or {}
    outs = ", ".join(str(o) for o in p.get("output_indices", []))

    if lt == "add_identity":
        return "Identity (no-op layer)"

    if lt in ("rotation", "shift"):
        verb = "Rotate" if lt == "rotation" else "Shift"
        direction = "left" if p.get("direction") == "l" else "right"
        out = f" -> word {p['out_index']}" if p.get("out_index") is not None else ""
        return f"{verb} word {p.get('word_index')} {direction} by {p.get('amount')}{out}"
    if lt == "xor" or lt == "n_xor":
        return f"XOR words {_flat(p.get('input_indices'))} -> word {outs}"
    if lt == "and":
        return f"AND words {_flat(p.get('input_indices'))} -> word {outs}"
    if lt == "or":
        return f"OR words {_flat(p.get('input_indices'))} -> word {outs}"
    if lt == "not":
        return f"NOT word {_flat(p.get('input_indices'))} -> word {outs}"
    if lt == "andxor":
        group = (p.get("input_indices") or [[]])[0]
        if len(group) == 3:
            return f"(word {group[0]} AND word {group[1]}) XOR word {group[2]} -> word {outs}"
        return f"AND-XOR words {_flat(p.get('input_indices'))} -> word {outs}"
    if lt == "modadd":
        return f"Modular-add words {_flat(p.get('input_indices'))} -> word {outs}"
    if lt == "sbox":
        return f"S-box '{p.get('sbox_name')}' on word groups {p.get('index', 'all')}"
    if lt == "subcolumn_sbox":
        return f"S-box '{p.get('sbox_name')}' down each column (bit-sliced)"
    if lt == "shift_rows":
        direction = "left" if p.get("direction", "l") == "l" else "right"
        return f"Rotate each row {direction} by offsets {p.get('offsets')}"
    if lt == "add_round_constant":
        return f"Add {p.get('d')}-bit LFSR round constant to row 0"
    if lt == "permutation":
        return f"Permutation (table {p.get('table')})"
    if lt == "matrix":
        m = p.get("matrix", [])
        return f"Matrix multiply ({len(m)}x{len(m)})"
    if lt == "gf2_linear":
        m = p.get("matrix", [])
        return f"GF(2) bit-linear transform ({len(m)}x{len(m)}) on words {p.get('index_in')}"
    if lt == "add_round_key":
        return f"Add round key ({p.get('operator', 'xor')})"
    if lt == "add_constant":
        return f"Add constant ({p.get('add_type', 'xor')})"
    return f"{lt}: {p}"


def spec_readback(spec):
    """Multi-line English read-back of a full CipherSpec (dict or object)."""
    if isinstance(spec, dict):
        spec = CipherSpec.from_dict(spec)
    lines = [f"{spec.name}", f"  Type: {spec.cipher_type}"]
    if spec.versions:
        # Parameterized family: show each version's real state size and round count
        # (resolved from its params) instead of the unfilled 0/placeholder template.
        default = spec.default_version or next(iter(spec.versions), None)
        lines.append(f"  Family: {len(spec.versions)} versions (default: {default})")
        for vname, ov in spec.versions.items():
            params = ov.get("params", {}) if isinstance(ov, dict) else {}
            rounds = _resolve_placeholders(
                ov.get("nbr_rounds", spec.nbr_rounds) if isinstance(ov, dict) else spec.nbr_rounds,
                params,
            )
            bits = _state_bits(spec, ov if isinstance(ov, dict) else {}, params)
            size = f"{bits}-bit" if isinstance(bits, int) and bits > 0 else "size ?"
            rnd = f"{rounds} rounds" if isinstance(rounds, int) and rounds > 0 else "rounds ?"
            lines.append(f"    {vname}: {size} state, {rnd}")
        if spec.layout:
            lines.append(f"  Bit-sliced: {spec.layout.get('rows')} rows x {spec.layout.get('cols')} cols")
    elif spec.layout:
        bits = _state_bits(spec, {}, {})
        lines.append(
            f"  State size: {bits if isinstance(bits, int) and bits > 0 else '?'} bits "
            f"(bit-sliced: {spec.layout.get('rows')} rows x {spec.layout.get('cols')} cols)"
        )
        lines.append(f"  Rounds: {spec.nbr_rounds}")
    else:
        lines.append(
            f"  Block size: {spec.block_size} bits "
            f"({spec.nbr_words} x {spec.word_bitsize}-bit words)"
        )
        lines.append(f"  Rounds: {spec.nbr_rounds}")
    if spec.sbox_tables:
        lines.append(f"  S-boxes: {', '.join(spec.sbox_tables.keys())}")
    lines.append("  Each round:")
    for i, layer in enumerate(spec.round_structure, 1):
        lines.append(f"    {i}. {describe_layer(layer)}")
    if spec.cipher_type == "blockcipher":
        lines.append(
            f"  Key: {spec.key_size} bits "
            f"({spec.key_nbr_words} x {spec.key_word_bitsize}-bit words)"
        )
        lines.append(f"  Subkey extraction: words {spec.key_extract_indices}")
        if getattr(spec, "pre_whitening", False):
            lines.append("  Pre-whitening: round key added before round 1 (modeled as an extra round)")
        if getattr(spec, "post_whitening", False):
            lines.append("  Post-whitening: round key added after the last round (modeled as an extra round)")
        if spec.key_schedule:
            lines.append("  Key schedule:")
            for i, layer in enumerate(spec.key_schedule, 1):
                lines.append(f"    {i}. {describe_layer(layer)}")
    if spec.test_vectors:
        lines.append(f"  Test vectors: {len(spec.test_vectors)} provided")
    return "\n".join(lines)
