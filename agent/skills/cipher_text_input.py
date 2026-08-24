"""Text-first data models for cipher extraction workflows."""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from agent.llm.response_parser import parse_llm_json_object
from agent.skills.cipher_spec import CipherSpec


_LATEX_TOKEN_REPLACEMENTS = {
    r"\oplus": " XOR ",
    r"\xor": " XOR ",
    r"\boxplus": " MODADD ",
    r"\lll": " ROTL ",
    r"\ggg": " ROTR ",
    r"\leftarrow": " <- ",
    r"\gets": " <- ",
    r"\rightarrow": " -> ",
    r"\to": " -> ",
    r"\land": " AND ",
    r"\lor": " OR ",
    r"\neg": " NOT ",
}

SUPPORTED_SOURCE_TYPES = {
    "direct_text",
    "uploaded_text",
    "markdown",
    "latex",
    "pseudocode",
}
SUPPORTED_FORMAT_HINTS = {"auto", "mixed", "plain_text", "markdown", "latex", "pseudocode"}
SUPPORTED_LANGUAGE_HINTS = {"en", "zh", "mixed", "unknown"}
SUPPORTED_PRIMITIVE_TYPES = {"permutation", "blockcipher"}
# High-level layer types valid only inside a bit-sliced `layout` cipher; expanded
# to concrete layers by CipherSpec.expand_bitsliced. Kept separate from the
# concrete SUPPORTED_OPERATIONS so add_round_constant is NOT rewritten to
# add_constant (which would discard the LFSR the expander needs).
LAYOUT_OPERATIONS = {"subcolumn_sbox", "shift_rows", "add_round_constant"}
SUPPORTED_OPERATIONS = {
    "add_constant",
    "add_round_key",
    "and",
    "andxor",
    "matrix",
    "modadd",
    "n_xor",
    "not",
    "or",
    "permutation",
    "rotation",
    "sbox",
    "shift",
    "xor",
}


@dataclass(frozen=True)
class CipherInput:
    """Raw user-provided cipher description before LLM parsing."""

    raw_text: str
    source_type: str = "direct_text"
    format_hint: str = "mixed"
    source_name: Optional[str] = None
    language_hint: str = "unknown"

    @property
    def normalized_text(self) -> str:
        """Return normalized text while preserving the user's cryptographic content."""

        return normalize_cipher_text(self.raw_text)

    @property
    def source_line_spans(self) -> List[Dict[str, Any]]:
        """Return line/column spans for normalized non-empty input lines."""

        _, spans = normalize_cipher_text_with_spans(self.raw_text)
        return spans

    def validate(self) -> List[str]:
        """Return validation errors for user-provided text metadata."""

        errors = []
        if not self.raw_text or not self.raw_text.strip():
            errors.append("Cipher input text is required.")
        if self.source_type not in SUPPORTED_SOURCE_TYPES:
            errors.append(f"Unsupported source_type: {self.source_type!r}.")
        if self.format_hint not in SUPPORTED_FORMAT_HINTS:
            errors.append(f"Unsupported format_hint: {self.format_hint!r}.")
        if self.language_hint not in SUPPORTED_LANGUAGE_HINTS:
            errors.append(f"Unsupported language_hint: {self.language_hint!r}.")
        return errors


@dataclass
class CipherFacts:
    """Intermediate facts extracted from cipher text before formalization."""

    name: Optional[str] = None
    primitive_type: Optional[str] = None
    state: Dict[str, Any] = field(default_factory=dict)
    rounds: Dict[str, Any] = field(default_factory=dict)
    operations: List[Dict[str, Any]] = field(default_factory=list)
    tables: Dict[str, Any] = field(default_factory=dict)
    key_schedule: Dict[str, Any] = field(default_factory=dict)
    test_vectors: List[Dict[str, Any]] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)
    source_spans: List[Dict[str, Any]] = field(default_factory=list)
    # Parameterized family: version -> scalar overrides + "params" for placeholders.
    versions: Optional[Dict[str, Any]] = None
    default_version: Optional[str] = None
    # Bit-sliced layout {rows, cols}: when present the operations are high-level
    # (subcolumn_sbox / shift_rows / add_round_constant) and CipherSpec.expand_bitsliced
    # derives the concrete word_bitsize=1 layers and state scalars.
    layout: Optional[Dict[str, Any]] = None
    # Cell-sliced layout {cell_bits, nbr_cells} (FUTURE class): high-level cell operations
    # (subcell_sbox / mixcolumn / cell_shiftrow) that CipherSpec.expand_cell_sliced lowers to
    # bit-level. Whitening keys added outside the round function (FUTURE pre, PRESENT post).
    cell_layout: Optional[Dict[str, Any]] = None
    pre_whitening: bool = False
    post_whitening: bool = False
    # Declarative static-key schedule (Midori/LED family): CipherSpec.expand_key_archetype
    # turns it into the per-round extraction + key-add / round-constant layers. Shape:
    # {"type": "static_alternating", "shares": 2, "whitening": "xor_shares",
    #  "round_constants": {"source": "pi_hex", "count": 15}}. With this set, `operations`
    # carries ONLY the data path (SubCell/Shuffle/Mix), not the key addition.
    key_archetype: Optional[Dict[str, Any]] = None
    # ARX permutation (ChaCha/Salsa/Forro): CipherSpec.expand_arx turns a declared (sub)round
    # into concrete modadd/xor/rotation layers. With this set, `operations` is left empty.
    arx: Optional[Dict[str, Any]] = None

    def validate(self) -> Tuple[List[str], List[str]]:
        """Validate extracted facts before they are converted into a draft spec."""

        return validate_cipher_facts(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CipherFacts":
        """Build extracted facts from a JSON-compatible dictionary."""

        return cls(
            name=data.get("name"),
            primitive_type=data.get("primitive_type") or data.get("cipher_type"),
            state=data.get("state", {}),
            rounds=data.get("rounds", {}),
            operations=data.get("operations", []),
            tables=data.get("tables", {}),
            key_schedule=data.get("key_schedule", {}),
            test_vectors=data.get("test_vectors", []),
            ambiguities=data.get("ambiguities", []),
            source_spans=data.get("source_spans", []),
            versions=data.get("versions"),
            default_version=data.get("default_version"),
            layout=data.get("layout"),
            cell_layout=data.get("cell_layout"),
            arx=data.get("arx"),
            pre_whitening=bool(data.get("pre_whitening", False)),
            post_whitening=bool(data.get("post_whitening", False)),
            # accept key_archetype at the top level OR nested under key_schedule (the LLM
            # often puts key-related fields there); top level wins if both are present.
            key_archetype=(data.get("key_archetype")
                           or (data.get("key_schedule") or {}).get("key_archetype")),
        )


@dataclass
class CipherSpecDraft:
    """A candidate CipherSpec with validation notes before user confirmation."""

    spec: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)
    requires_user_confirmation: bool = True
    # Trace of automatic LLM self-repair rounds (each: attempt, problems_before,
    # problems_after / error, resolved). Shown to the user so the fixes are visible.
    repair_log: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Whether the draft has no blocking validation errors."""

        return not self.validation_errors

    def validate_spec(self) -> List[str]:
        """Validate the proposed CipherSpec payload and refresh blocking errors."""

        errors = validate_cipher_spec_payload(self.spec)
        self.validation_errors = errors
        return errors


def _replace_latex_tokens(text: str) -> str:
    for latex_token, replacement in _LATEX_TOKEN_REPLACEMENTS.items():
        text = text.replace(latex_token, replacement)
    return text


def normalize_cipher_text_with_spans(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Normalize cipher text and return source spans for normalized non-empty lines."""

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = []
    spans = []
    previous_blank = False
    for line_number, line in enumerate(text.split("\n"), start=1):
        clean_line = _replace_latex_tokens(line).rstrip()
        is_blank = clean_line.strip() == ""
        if is_blank and previous_blank:
            continue
        lines.append(clean_line)
        if not is_blank:
            column_start = len(line) - len(line.lstrip()) + 1
            column_end = len(line.rstrip())
            spans.append(
                {
                    "line_start": line_number,
                    "line_end": line_number,
                    "column_start": column_start,
                    "column_end": column_end,
                    "text": clean_line,
                }
            )
        previous_blank = is_blank

    return "\n".join(lines).strip(), spans


def normalize_cipher_text(text: str) -> str:
    """Normalize plain/Markdown/LaTeX cipher text for downstream parsing."""

    normalized, _ = normalize_cipher_text_with_spans(text)
    return normalized


def lint_cipher_text(text):
    """Deterministic pre-flight check of a cipher description before extraction.

    Returns ``(blocking, warnings)``. ``blocking`` is True only when the text is
    too short to be a cipher spec (skip the LLM call entirely). ``warnings`` are
    non-blocking nudges about missing pieces that hurt extraction accuracy or
    prevent verification (no rounds, no operations, no state size, no test
    vectors). Costs no LLM tokens.
    """
    import re

    raw = text or ""
    lowered = raw.lower()
    if len(raw.strip()) < 40:
        return True, [
            "The description looks too short. Paste the round function and cipher "
            "structure (state size, number of rounds, and each per-round operation)."
        ]

    warnings = []
    if "round" not in lowered:
        warnings.append("No round count found - state the number of rounds (e.g. 'Rounds: 22').")

    op_keywords = ("rotate", "rotation", "rotl", "rotr", "shift", "xor", "modadd",
                   "modular", "sbox", "s-box", "substitut", "permut", "matrix", "\\oplus", "\\boxplus")
    if not any(kw in lowered for kw in op_keywords):
        warnings.append(
            "No round operations detected - describe each step of the round function "
            "(rotate / xor / modular-add / S-box / permutation / ...)."
        )

    if not re.search(r"\b(bit|bits|block|word|words|state|nibble)\b", lowered):
        warnings.append(
            "No state size found - give the block size and word layout "
            "(e.g. '32 bits = 2 words x 16 bits')."
        )

    has_test_vector = ("0x" in lowered) or ("test vector" in lowered) or bool(re.search(r"->|→", raw))
    if not has_test_vector:
        warnings.append(
            "No test vectors found - add a known input -> output pair (with the key "
            "for a block cipher) so the built cipher can be verified."
        )
    return False, warnings


def parse_cipher_facts_response(raw: str) -> Optional[CipherFacts]:
    """Parse an LLM JSON response into ``CipherFacts``."""

    data = parse_llm_json_object(raw)
    if data is None:
        return None
    facts_data = data.get("cipher_facts", data)
    if not isinstance(facts_data, dict):
        return None
    return CipherFacts.from_dict(facts_data)


def _positive_int(value):
    return isinstance(value, int) and value > 0


# Map common LLM synonyms to OCP's canonical layer_type names, so an extraction
# that says e.g. "add_round_constant" or "substitution" still validates and builds.
_OPERATION_ALIASES = {
    "add_round_constant": "add_constant",
    "addroundconstant": "add_constant",
    "round_constant": "add_constant",
    "constant_addition": "add_constant",
    "add_constant_layer": "add_constant",
    "addroundkey": "add_round_key",
    "add_key": "add_round_key",
    "key_addition": "add_round_key",
    "rotate": "rotation",
    "circular_shift": "rotation",
    "rotl": "rotation",
    "rotr": "rotation",
    "mod_add": "modadd",
    "modular_add": "modadd",
    "modular_addition": "modadd",
    "substitution": "sbox",
    "s_box": "sbox",
    "sbox_layer": "sbox",
    "bit_permutation": "permutation",
    "bitpermutation": "permutation",
    "permute": "permutation",
    "mixcolumns": "matrix",
    "mix_columns": "matrix",
    "linear_layer": "matrix",
    "nxor": "n_xor",
    "and_xor": "andxor",
}


def _operation_type(operation):
    raw = operation.get("layer_type") or operation.get("type") or operation.get("operation")
    if not raw:
        return raw
    canonical = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
    return _OPERATION_ALIASES.get(canonical, canonical)


def _layout_operation_type(operation):
    """Normalize a high-level layout op type WITHOUT the concrete-layer aliases:
    inside a `layout` cipher, add_round_constant must stay add_round_constant (its
    LFSR is consumed by expand_bitsliced) rather than collapsing to add_constant."""
    raw = operation.get("layer_type") or operation.get("type") or operation.get("operation")
    if not raw:
        return raw
    return str(raw).strip().lower().replace(" ", "_").replace("-", "_")


# Param-key synonyms an LLM commonly emits, normalized to the names the builder expects. Only
# UNAMBIGUOUS global renames go here: "inputs"/"outputs" are never a native param name. NOT
# included on purpose: "columns" (mixcolumn uses it natively, only matrix means "indices" - a
# layer-specific rename) and "row" (a whole-row rotation across cells is a BIT permutation, not
# a word rotation, so mapping row->word_index would hide a granularity error).
_PARAM_KEY_ALIASES = {"inputs": "input_indices", "outputs": "output_indices"}


def _operation_params(operation):
    params = operation.get("params", operation.get("parameters", {}))
    if isinstance(params, dict) and any(k in params for k in _PARAM_KEY_ALIASES):
        params = {_PARAM_KEY_ALIASES.get(k, k): v for k, v in params.items()}
    return params


def _operation_to_layer(operation, type_fn):
    """A round/key layer dict from a fact operation, carrying round-dependent scope
    (only_rounds/except_rounds) through so e.g. a last-round-skipped MixColumn survives."""
    layer = {"layer_type": type_fn(operation), "params": _operation_params(operation)}
    for key in ("only_rounds", "except_rounds"):
        if operation.get(key) is not None:
            layer[key] = operation[key]
    return layer


def _is_power_of_two(value):
    return isinstance(value, int) and value > 0 and value & (value - 1) == 0


def _validate_sbox_table(name, table):
    errors = []
    if not isinstance(table, list) or not table:
        return [f"S-box table {name!r} must be a non-empty list."]
    if not _is_power_of_two(len(table)):
        errors.append(f"S-box table {name!r} length must be a power of two.")
    if not all(isinstance(entry, int) and entry >= 0 for entry in table):
        errors.append(f"S-box table {name!r} must contain non-negative integers.")
    return errors


def validate_cipher_facts(facts: CipherFacts) -> Tuple[List[str], List[str]]:
    """Validate extracted facts and return ``(errors, warnings)``."""

    errors = []
    warnings = []

    if not facts.name:
        errors.append("Cipher name is missing.")
    if facts.primitive_type not in SUPPORTED_PRIMITIVE_TYPES:
        errors.append("primitive_type must be 'permutation' or 'blockcipher'.")

    # For a parameterized family the per-member scalars (state size, rounds, key
    # sizes) live under "versions"; skip the top-level scalar checks and let the
    # concrete member be validated at instantiation time.
    # A bit-sliced layout derives its state scalars (block_size/word_bitsize/
    # nbr_words) from rows x cols at expansion time, so skip the scalar checks too.
    if not facts.versions and not facts.layout and not facts.cell_layout and not facts.arx:
        block_size = facts.state.get("block_size") or facts.state.get("state_size_bits")
        word_bitsize = facts.state.get("word_bitsize") or facts.state.get("unit_size_bits")
        nbr_words = facts.state.get("nbr_words") or facts.state.get("num_units")
        nbr_rounds = facts.rounds.get("nbr_rounds") or facts.rounds.get("num_rounds")

        if not _positive_int(block_size):
            errors.append("State block_size/state_size_bits must be a positive integer.")
        if not _positive_int(word_bitsize):
            errors.append("State word_bitsize/unit_size_bits must be a positive integer.")
        if not _positive_int(nbr_words):
            errors.append("State nbr_words/num_units must be a positive integer.")
        if _positive_int(block_size) and _positive_int(word_bitsize) and _positive_int(nbr_words):
            if block_size != word_bitsize * nbr_words:
                errors.append("State size must equal word_bitsize * nbr_words.")
        if not _positive_int(nbr_rounds):
            errors.append("Round count nbr_rounds/num_rounds must be a positive integer.")

    # Each family member needs a DEFAULT round count - the design's full number of
    # rounds, used whenever the user leaves the round count blank (the user can
    # still override it at build time). Papers often list several phase counts (e.g.
    # KNOT's nr/nr0/nrf), so the family must say which one is the full/default: set
    # "nbr_rounds" on every version, or a single top-level nbr_rounds.
    if facts.versions:
        top_rounds = facts.rounds.get("nbr_rounds") or facts.rounds.get("num_rounds")
        version_map = facts.versions if isinstance(facts.versions, dict) else {}
        missing = [name for name, ov in version_map.items()
                   if not (isinstance(ov, dict) and "nbr_rounds" in ov)]
        if not top_rounds and missing:
            shown = ", ".join(missing[:4]) + ("..." if len(missing) > 4 else "")
            errors.append(
                "Each version must set 'nbr_rounds' - the default (full) round count used "
                "when the round count is left blank. For a permutation family like KNOT "
                "that is the permutation's own full round count, e.g. \"nbr_rounds\": "
                f"\"$nr0\" (not the AEAD/hash phase counts). Missing in: {shown}."
            )

    if not facts.operations and not facts.arx:
        # The recurring "ingredients without a recipe" failure: the LLM captured the round
        # TABLES (S-box / matrix / permutation) and even per-version params, but left the
        # ordered `operations` recipe empty (nothing says HOW the tables are applied per round).
        # Turn the generic error into a table-aware, actionable one so the repair loop and the
        # user see exactly which tables exist and the canonical order to sequence them into.
        # We do NOT invent the order here (it varies by cipher and the KAT is the gate) - this
        # only nudges the LLM to emit the list it forgot.
        tbls = facts.tables if isinstance(facts.tables, dict) else {}
        def _names(*keys):
            out = []
            for k in keys:
                v = tbls.get(k)
                if isinstance(v, dict):
                    out.extend(v.keys())
            return out
        sboxes = _names("sbox_tables", "sboxes")
        matrices = _names("matrix_tables", "matrices")
        perms = _names("permutation_tables", "permutations")
        if sboxes or matrices or perms:
            have = []
            if sboxes:
                have.append("S-box(es) " + ", ".join(sboxes))
            if perms:
                have.append("permutation(s) " + ", ".join(perms))
            if matrices:
                have.append("matrix/matrices " + ", ".join(matrices))
            errors.append(
                "`operations` (the ordered round recipe) is EMPTY, but you extracted the round "
                "tables: " + "; ".join(have) + ". Tables alone are NOT a cipher - add the ordered "
                "`operations` list saying HOW each round applies them. For an SPN the canonical "
                "order is sbox/subcell_sbox -> permutation/cell_shiftrow (ShuffleCell) -> "
                "matrix/mixcolumn (MixColumn) -> add_round_key (+ add_constant if the round has "
                "constants); confirm the exact order and per-round layers against the paper. For a "
                "versioned family, emit this shared `operations` skeleton (use $placeholders for "
                "values that differ per version) - do NOT leave it empty and put only table names "
                "under each version's params."
            )
        else:
            errors.append("At least one round operation is required.")
    # For a parameterized family the layout dimensions may be placeholders (e.g.
    # cols "$b/4") resolved per version at instantiation, so only check concrete
    # rows/cols here when there is no versions map.
    if facts.layout and not facts.versions and (
        not isinstance(facts.layout, dict)
        or not _positive_int(facts.layout.get("rows"))
        or not _positive_int(facts.layout.get("cols"))
    ):
        errors.append("layout must provide positive integer 'rows' and 'cols'.")
    if facts.cell_layout and not facts.versions and (
        not isinstance(facts.cell_layout, dict)
        or not _positive_int(facts.cell_layout.get("cell_bits"))
        or not _positive_int(facts.cell_layout.get("nbr_cells"))
    ):
        errors.append("cell_layout must provide positive integer 'cell_bits' and 'nbr_cells'.")
    for index, operation in enumerate(facts.operations):
        if facts.layout:
            operation_type = _layout_operation_type(operation)
            if operation_type not in LAYOUT_OPERATIONS:
                errors.append(
                    f"Operation {index} has unsupported layout type {operation_type!r} "
                    f"(expected one of {sorted(LAYOUT_OPERATIONS)})."
                )
        elif facts.cell_layout:
            # cell-sliced mixes high-level cell ops (subcell_sbox / mixcolumn / cell_shiftrow)
            # with plain bit-level ops (add_round_key / add_constant / permutation); concrete
            # validity is checked after expand_cell_sliced, so don't restrict the type here.
            pass
        else:
            operation_type = _operation_type(operation)
            if operation_type not in SUPPORTED_OPERATIONS:
                errors.append(f"Operation {index} has unsupported type {operation_type!r}.")
        if "confidence" in operation and not 0 <= operation["confidence"] <= 1:
            warnings.append(f"Operation {index} confidence should be between 0 and 1.")
        if operation.get("assumption"):
            warnings.append(f"Operation {index} depends on assumption: {operation['assumption']}.")

    sbox_tables = facts.tables.get("sbox_tables") or facts.tables.get("sboxes") or {}
    if isinstance(sbox_tables, dict):
        for name, table in sbox_tables.items():
            errors.extend(_validate_sbox_table(name, table))
    elif sbox_tables:
        errors.append("S-box tables must be provided as a dictionary.")

    if facts.primitive_type == "blockcipher" and not facts.versions:
        key_size = facts.key_schedule.get("key_size")
        key_nbr_words = facts.key_schedule.get("key_nbr_words")
        if not _positive_int(key_size):
            errors.append("Block cipher key_size must be a positive integer.")
        if not _positive_int(key_nbr_words):
            errors.append("Block cipher key_nbr_words must be a positive integer.")
        # key_extract_indices is generated by the archetype expander when key_archetype is set.
        if "key_extract_indices" not in facts.key_schedule and not facts.key_archetype:
            errors.append(
                "Block cipher key_extract_indices is required (or declare a key_archetype).")

    if facts.ambiguities:
        warnings.extend(f"Ambiguity: {ambiguity}" for ambiguity in facts.ambiguities)

    return errors, warnings


def cipher_spec_payload_from_facts(facts: CipherFacts) -> Dict[str, Any]:
    """Convert validated facts into a CipherSpec-compatible dictionary."""

    state = facts.state
    rounds = facts.rounds
    key_schedule = facts.key_schedule
    # Inside a layout cipher the operations are high-level and must keep their raw
    # type (see _layout_operation_type); otherwise apply the concrete-layer aliases.
    # Inside a layout OR cell_layout cipher the operations are high-level (subcolumn_sbox /
    # subcell_sbox / mixcolumn / cell_shiftrow / ...) and must keep their raw type for the
    # expander; otherwise apply the concrete-layer aliases.
    op_type = _layout_operation_type if (facts.layout or facts.cell_layout) else _operation_type
    payload = {
        "name": facts.name or "CustomCipher",
        "cipher_type": facts.primitive_type or "permutation",
        "block_size": state.get("block_size") or state.get("state_size_bits") or 0,
        "word_bitsize": state.get("word_bitsize") or state.get("unit_size_bits") or 0,
        "nbr_words": state.get("nbr_words") or state.get("num_units") or 0,
        "nbr_rounds": rounds.get("nbr_rounds") or rounds.get("num_rounds") or 0,
        "nbr_temp_words": state.get("nbr_temp_words", 0),
        "round_structure": [
            _operation_to_layer(operation, op_type) for operation in facts.operations
        ],
        "sbox_tables": facts.tables.get("sbox_tables") or facts.tables.get("sboxes") or {},
    }
    if facts.layout:
        payload["layout"] = facts.layout
    if facts.cell_layout:
        payload["cell_layout"] = facts.cell_layout
    if facts.arx:
        payload["arx"] = facts.arx

    if facts.primitive_type == "blockcipher":
        payload.update(
            {
                "key_size": key_schedule.get("key_size"),
                "key_word_bitsize": key_schedule.get("key_word_bitsize"),
                "key_nbr_words": key_schedule.get("key_nbr_words"),
                "key_nbr_temp_words": key_schedule.get("key_nbr_temp_words", 0),
                "key_schedule": [
                    _operation_to_layer(operation, _operation_type)
                    for operation in key_schedule.get("round_structure", [])
                ],
                "key_extract_indices": key_schedule.get("key_extract_indices"),
            }
        )
        if key_schedule.get("key_nbr_rounds") is not None:  # Simon: KS runs fewer rounds
            payload["key_nbr_rounds"] = key_schedule.get("key_nbr_rounds")
        if facts.pre_whitening:
            payload["pre_whitening"] = True
        if facts.post_whitening:
            payload["post_whitening"] = True
        if facts.key_archetype:
            payload["key_archetype"] = facts.key_archetype
    if facts.test_vectors:
        payload["test_vectors"] = facts.test_vectors
    if facts.versions:
        versions = facts.versions
        # For a bit-sliced (layout) family the state scalars are derived from
        # rows x cols at expansion, so any per-version block_size/word_bitsize/
        # nbr_words overrides are redundant (and misleading). Drop them, keeping
        # nbr_rounds and params.
        if facts.layout and isinstance(versions, dict):
            derived = ("block_size", "word_bitsize", "nbr_words")
            versions = {
                name: ({k: v for k, v in ov.items() if k not in derived}
                       if isinstance(ov, dict) else ov)
                for name, ov in versions.items()
            }
        payload["versions"] = versions
        payload["default_version"] = facts.default_version
    return payload


def merge_test_vectors_into_spec(spec: Dict[str, Any], tv_data: Any) -> Dict[str, Any]:
    """Inject parsed test vectors into a CipherSpec dict, returning a new dict.

    Accepts three shapes so users can paste or load a variety of files:
      - {"versions": {name: {"test_vectors": [...]}}} - the per-version layout of
        files/knot_test_vectors.json; injected into each matching version.
      - {"test_vectors": [...]} or a bare list [[[inputs], output], ...] - injected
        into the family's default version, or the top level for a single cipher.
    Unknown version names are ignored. Vector shapes are normalized later by
    _normalize_test_vectors at build time.
    """
    import copy
    spec = copy.deepcopy(spec)

    def _vectors(obj):
        if isinstance(obj, dict):
            return obj.get("test_vectors")
        return obj if isinstance(obj, list) else None

    if isinstance(tv_data, dict) and isinstance(tv_data.get("versions"), dict):
        versions = spec.get("versions") or {}
        for name, member in tv_data["versions"].items():
            vectors = _vectors(member)
            if name in versions and vectors:
                versions[name] = {**versions[name], "test_vectors": vectors}
        spec["versions"] = versions
    else:
        vectors = _vectors(tv_data)
        if vectors:
            if spec.get("versions"):
                default = spec.get("default_version") or next(iter(spec["versions"]))
                if default in spec["versions"]:
                    spec["versions"][default] = {**spec["versions"][default], "test_vectors": vectors}
            else:
                spec["test_vectors"] = vectors
    return spec


def validate_cipher_spec_payload(spec_payload: Dict[str, Any]) -> List[str]:
    """Validate a CipherSpec-compatible dictionary without constructing a primitive."""

    try:
        spec = CipherSpec.from_dict(spec_payload)
        return spec.validate()
    except (KeyError, TypeError, ValueError) as exc:
        return [f"Invalid CipherSpec payload: {exc}"]


def apply_deterministic_fixes(spec: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Fix mechanical spec errors that have a single, unambiguous correct value, so that
    neither the LLM nor the user has to. Only fixes with ONE clearly-right answer are done
    here; anything requiring judgement is left for validation/repair. Mutates and returns
    the spec plus a list of human-readable notes for the ones applied.
    """
    notes: List[str] = []

    # 1. block_size must equal word_bitsize * nbr_words. If the two factors are given and
    # concrete (not a versioned/layout family, where they are derived), the product is the
    # only correct block_size - set it.
    wb, nw, bs = spec.get("word_bitsize"), spec.get("nbr_words"), spec.get("block_size")
    if (isinstance(wb, int) and isinstance(nw, int) and wb > 0 and nw > 0
            and not spec.get("versions") and not spec.get("layout") and not spec.get("cell_layout")
            and bs != wb * nw):
        spec["block_size"] = wb * nw
        notes.append(f"Set block_size to {wb * nw} (word_bitsize {wb} x nbr_words {nw}).")

    # 2. add_round_key mask: when the subkey covers the WHOLE state (subkey word count ==
    # state word count), the mask must be all-1s. That is the single correct value, so a
    # mismatched mask can be reset. (A partial subkey has no unique mask - leave it.)
    if spec.get("cipher_type") == "blockcipher":
        subkey_words = len(spec.get("key_extract_indices") or [])
        state_words = spec.get("nbr_words")
        if isinstance(state_words, int) and subkey_words == state_words and state_words > 0:
            for i, layer in enumerate(spec.get("round_structure", [])):
                if layer.get("layer_type") != "add_round_key":
                    continue
                params = layer.get("params") or {}
                mask = params.get("mask")
                if mask is not None and sum(1 for m in mask if m) != subkey_words:
                    params["mask"] = [1] * state_words
                    layer["params"] = params
                    notes.append(
                        f"round layer {i}: reset add_round_key mask to all-1 "
                        f"({state_words} words, matching the subkey)."
                    )

    # 2b. Cross-variant test vectors. A family's paper lists KATs for several variants
    # (LEA-128/192/256, Midori64/128); a vector whose plaintext or key word-count matches a
    # DIFFERENT variant than the one being built can NEVER pass this cipher's KAT, and neither
    # the repair (it must not edit vectors) nor a size change (that would be the wrong cipher)
    # can fix it. Drop such vectors - but ONLY when a same-variant vector still remains, so a
    # merely-wrong declared size surfaces as a validation error instead of silently discarding
    # every vector. Decided purely by declared sizes, so it is deterministic.
    def _expected_words(word_bits, total_bits, count):
        if isinstance(count, int) and count > 0:
            return count
        if isinstance(total_bits, int) and total_bits > 0 and isinstance(word_bits, int) and word_bits > 0:
            return total_bits // word_bits
        return None

    def _field_words(val, word_bits):
        if isinstance(val, (list, tuple)):
            return len(val)
        if isinstance(val, str) and isinstance(word_bits, int) and word_bits > 0:
            s = re.sub(r"[\s_,]", "", val.strip().lower())
            if s.startswith("0x"):
                s = s[2:]
            if s and re.fullmatch(r"[0-9a-f]+", s) and (len(s) * 4) % word_bits == 0:
                return (len(s) * 4) // word_bits
        return None

    tvs = spec.get("test_vectors")
    if isinstance(tvs, list) and tvs and spec.get("cipher_type") == "blockcipher":
        wbits = spec.get("word_bitsize")
        kbits = spec.get("key_word_bitsize") or wbits
        exp_state = _expected_words(wbits, spec.get("block_size"), spec.get("nbr_words"))
        exp_key = _expected_words(kbits, spec.get("key_size"), spec.get("key_nbr_words"))
        matched, mismatched = [], []
        for tv in tvs:
            ok = True
            if isinstance(tv, dict):
                pw = _field_words(tv.get("plaintext") or tv.get("input") or tv.get("pt"), wbits)
                kw = _field_words(tv.get("key"), kbits)
                if ((exp_state and pw is not None and pw != exp_state)
                        or (exp_key and kw is not None and kw != exp_key)):
                    ok = False
            (matched if ok else mismatched).append(tv)
        if mismatched and matched:
            spec["test_vectors"] = matched
            notes.append(
                f"Dropped {len(mismatched)} test vector(s) whose plaintext/key size does not "
                f"match this cipher (expects {exp_state}-word blocks, {exp_key}-word keys) - they "
                f"belong to a different variant or were mis-copied. Kept {len(matched)}."
            )

    cell_ops = {"subcell_sbox", "mixcolumn", "cell_shiftrow"}

    # 3a. layout vs cell_layout confusion. `layout` is the BIT-SLICED SPN representation
    # (needs rows/cols); `cell_layout` is the CELL-level one (cell_bits/nbr_cells, consumed by
    # subcell_sbox/mixcolumn/cell_shiftrow). LLMs nest cell_layout INSIDE layout, or put
    # cell_bits/nbr_cells under layout. The two vocabularies are disjoint, so a `layout` shaped
    # like a cell_layout (or a layout carrying cell operations) can be hoisted deterministically.
    def _cell_dim_ok(v):
        # A cell dimension is a positive int OR a "$name" version placeholder (resolved at
        # instantiate time for a family like Midori64/128).
        return (isinstance(v, int) and v > 0) or (isinstance(v, str) and v.startswith("$"))

    lay = spec.get("layout")
    if isinstance(lay, dict) and not spec.get("cell_layout"):
        inner = lay.get("cell_layout") if isinstance(lay.get("cell_layout"), dict) else None
        uses_cell_ops = any(l.get("layer_type") in cell_ops for l in spec.get("round_structure", []))
        # A NESTED cell_layout is unambiguous evidence - hoist it verbatim even when its values are
        # $placeholders (a versioned family). Otherwise only hoist cell_bits/nbr_cells that sit
        # directly under layout when the round actually uses cell operations. A real bit-sliced
        # layout (rows/cols, no cell keys) is left untouched.
        source = inner if inner is not None else (lay if uses_cell_ops else None)
        if source is not None:
            cb, nc = source.get("cell_bits"), source.get("nbr_cells")
            if _cell_dim_ok(cb) and _cell_dim_ok(nc):
                spec["cell_layout"] = {"cell_bits": cb, "nbr_cells": nc}
                spec.pop("layout", None)
                notes.append(
                    f"Moved a cell-shaped 'layout' to cell_layout {{cell_bits: {cb}, nbr_cells: {nc}}} "
                    f"and removed 'layout' - cell operations (SubCell/MixColumn/ShiftRow) expand via "
                    f"cell_layout, not the bit-sliced layout."
                )

    # 3. cell operations without a cell_layout: the LLM used subcell_sbox/mixcolumn/
    # cell_shiftrow (recognizing a cell-level SPN) but forgot the cell_layout field, so those
    # types are rejected. The layout is fully determined by the cell size and count, so derive
    # it from word_bitsize x nbr_words and drop the now-derived state scalars.
    if not spec.get("cell_layout") and not spec.get("layout") and any(
            l.get("layer_type") in cell_ops for l in spec.get("round_structure", [])):
        wb, nw = spec.get("word_bitsize"), spec.get("nbr_words")
        if isinstance(wb, int) and wb > 0 and isinstance(nw, int) and nw > 0:
            spec["cell_layout"] = {"cell_bits": wb, "nbr_cells": nw}
            for k in ("block_size", "word_bitsize", "nbr_words"):
                spec.pop(k, None)
            notes.append(
                f"Derived cell_layout {{cell_bits: {wb}, nbr_cells: {nw}}} from the cell "
                f"operations (they need a cell_layout to expand to bit-level)."
            )

    # 3c. cell_layout present but the round uses GENERIC word layers (sbox / matrix /
    # permutation) instead of the cell-native ones. A cell_layout lowers the data path to
    # word_bitsize=1 via expand_cell_sliced, which ONLY rewrites subcell_sbox / mixcolumn /
    # cell_shiftrow; a generic `sbox` with per-cell singleton groups then becomes "1-bit words,
    # 4 needed" and the build dies. This is the FUTURE/LED class: the LLM correctly saw a cell
    # SPN (chose cell_layout) but emitted the operations at word granularity. The two vocabularies
    # are 1:1 at cell granularity, so convert generic -> cell-native deterministically. Guards keep
    # this from firing on a genuine bit-sliced layer: a real bit matrix/permutation is nc*cb wide,
    # never nc wide. KAT stays the safety net for anything the conversion mis-reads.
    clay = spec.get("cell_layout")
    if isinstance(clay, dict):
        cb, nc = clay.get("cell_bits"), clay.get("nbr_cells")
        if isinstance(cb, int) and cb > 1 and isinstance(nc, int) and nc > 0:
            def _is_percell_groups(index):
                # nc singleton groups covering 0..nc-1 exactly (the per-cell S-box grouping).
                if not isinstance(index, list) or len(index) != nc:
                    return False
                flat = []
                for g in index:
                    if not isinstance(g, list) or len(g) != 1:
                        return False
                    flat.append(g[0])
                return sorted(flat) == list(range(nc))
            new_round = []
            changed = []
            for layer in (spec.get("round_structure") or []):
                lt = layer.get("layer_type")
                p = layer.get("params") or {}
                if lt == "sbox":
                    name = p.get("sbox_name")
                    tbl = (spec.get("sbox_tables") or {}).get(name)
                    idx = p.get("index")
                    # A per-cell S-box: the table spans one cell (2**cell_bits) and the groups are
                    # singletons (or absent -> implicitly every cell).
                    if (isinstance(tbl, list) and len(tbl) == (1 << cb)
                            and (idx is None or _is_percell_groups(idx))):
                        layer = {"layer_type": "subcell_sbox", "params": {"sbox_name": name}}
                        changed.append("sbox->subcell_sbox")
                elif lt == "matrix":
                    mat = p.get("matrix")
                    cols = p.get("indices")
                    # A cell MDS matrix: small square of GF(2^cb) integer coeffs (all < 2**cell_bits),
                    # with column groups sized to the matrix dimension. A lowered bit matrix would be
                    # (m*cb) wide with 0/1 entries and cb*m-sized groups instead.
                    if (isinstance(mat, list) and mat and all(isinstance(r, list) for r in mat)
                            and len({len(r) for r in mat}) == 1 and len(mat) == len(mat[0])
                            and all(isinstance(v, int) and 0 <= v < (1 << cb) for r in mat for v in r)
                            and isinstance(cols, list) and cols
                            and all(isinstance(c, list) and len(c) == len(mat) for c in cols)):
                        params = {"matrix": mat, "columns": cols}
                        if p.get("polynomial") is not None:
                            params["polynomial"] = p["polynomial"]
                        layer = {"layer_type": "mixcolumn", "params": params}
                        changed.append("matrix->mixcolumn")
                elif lt == "permutation":
                    tbl = p.get("table")
                    # A CELL permutation is nc wide; a bit permutation is nc*cb wide.
                    if (isinstance(tbl, list) and len(tbl) == nc
                            and sorted(tbl) == list(range(nc))):
                        layer = {"layer_type": "cell_shiftrow", "params": {"table": tbl}}
                        changed.append("permutation->cell_shiftrow")
                new_round.append(layer)
            if changed:
                spec["round_structure"] = new_round
                notes.append(
                    "Converted generic word layers to cell-native ones under cell_layout ("
                    + ", ".join(changed)
                    + ") - cell_layout only expands subcell_sbox / mixcolumn / cell_shiftrow, so a "
                    "per-cell S-box, a GF(2^cell_bits) MDS matrix and a cell permutation must use "
                    "those types (a generic word 'sbox' becomes 1-bit words after bit-slicing and "
                    "the build fails)."
                )


    # 3b. Midori/LED-family AUTO-ARCHETYPE. The LLM repeatedly builds this family the fragile
    # MANUAL way: a static-alternating key_extract_indices (equal shares partitioning the key) +
    # pre/post_whitening + an add_round_key layer, but WITHOUT the round constants. That drops the
    # pi constants (wrong cipher, all-zero output), and the whitening+key extraction of this exact
    # shape is broken in the builder - so it can NEVER be right. Convert it to the reliable
    # key_archetype (which injects the alternating keys, whitening AND pi constants). The KAT stays
    # the safety net: a mis-detected cipher just fails to verify (no worse than the broken manual
    # shape), while a real Midori/LED now builds.
    if spec.get("cipher_type") == "blockcipher" and not spec.get("key_archetype"):
        kei = spec.get("key_extract_indices")
        rtypes = [l.get("layer_type") for l in (spec.get("round_structure") or [])]
        has_spn = (any(t in ("sbox", "subcell_sbox") for t in rtypes)
                   and any(t in ("matrix", "mixcolumn") for t in rtypes))
        has_whitening = bool(spec.get("pre_whitening") or spec.get("post_whitening"))
        no_constants = "add_constant" not in rtypes
        # key_extract_indices is a list of >= 2 EQUAL shares that partition [0, total) exactly.
        is_shares = (isinstance(kei, list) and len(kei) >= 2
                     and all(isinstance(s, list) and s for s in kei)
                     and len({len(s) for s in kei}) == 1
                     and sorted(x for s in kei for x in s) == list(range(sum(len(s) for s in kei))))
        if is_shares and has_spn and has_whitening and no_constants:
            shares = len(kei)
            spec["key_archetype"] = {
                "type": "static_alternating", "shares": shares,
                "whitening": "xor_shares" if shares == 2 else "whole_key",
                "round_constants": {"source": "pi_hex"},
            }
            notes.append(
                f"Converted a hand-wired static-alternating key (shares={shares}, whitening, no "
                f"round constants) to a key_archetype - the manual path drops the pi round "
                f"constants and mis-handles whitening (the Midori/LED family). The archetype "
                f"injects the alternating keys, whitening and pi constants."
            )

    # 4. key_archetype supersedes hand-written key handling. When a key_archetype is declared it
    # GENERATES the per-round key add, the subkey extraction, the whitening and (if given) the
    # round constants - so a hand-written key_extract_indices / key_schedule / add_round_key /
    # add_constant DOUBLES them, which validate rejects. The LLM often emits both (it reached for
    # the archetype AND kept the old fields). Strip exactly what the archetype provides - a purely
    # mechanical de-duplication with one correct answer, so the repair loop never has to.
    arch = spec.get("key_archetype")
    # An EVOLVING key_schedule (it UPDATES the key each round via rotation/permutation/LFSR/...)
    # CONTRADICTS a static_alternating archetype (which models a FIXED key). The evolving schedule
    # is concrete evidence the key evolves (FUTURE class), so REMOVE the archetype and keep the
    # schedule (mechanism 3) - the opposite of stripping the schedule.
    _KEY_UPDATE = {"rotation", "shift", "bit_rotation", "gf2_linear"}
    if isinstance(arch, dict) and arch.get("type") == "static_alternating" and any(
            l.get("layer_type") in _KEY_UPDATE for l in (spec.get("key_schedule") or [])):
        spec.pop("key_archetype", None)
        arch = None
        notes.append(
            "Removed the static_alternating key_archetype: the key_schedule UPDATES the key each "
            "round (rotation/permutation), so the key EVOLVES (FUTURE class) - a static archetype "
            "cannot model that. Kept the evolving key_schedule (mechanism 3)."
        )
    if isinstance(arch, dict):
        if spec.get("key_extract_indices") is not None:
            spec.pop("key_extract_indices", None)
            notes.append("Removed hand-written key_extract_indices: the key_archetype generates it.")
        if spec.get("key_schedule"):
            spec["key_schedule"] = []
            notes.append("Cleared key_schedule: the key_archetype models a static key.")
        # The archetype's own whitening ("xor_shares"/"whole_key") already emits the pre/post
        # whitening rounds; ALSO setting pre_whitening/post_whitening applies whitening TWICE
        # (compile runs expand_key_archetype AND expand_whitening), inflating nbr_rounds and
        # overrunning the round-constant table at codegen ("list index out of range"). Clear them.
        if arch.get("whitening") not in (None, "none"):
            cleared = [f for f in ("pre_whitening", "post_whitening") if spec.get(f)]
            for f in cleared:
                spec[f] = False
            if cleared:
                notes.append(f"Cleared {', '.join(cleared)}: the key_archetype's "
                             f"whitening='{arch.get('whitening')}' already adds the whitening "
                             f"round(s); setting both applies whitening twice.")
        rs = spec.get("round_structure") or []
        strip = {"add_round_key"}
        if arch.get("round_constants"):
            strip.add("add_constant")  # archetype supplies the constants; a hand-written one doubles them
        kept_layers = [l for l in rs if l.get("layer_type") not in strip]
        if len(kept_layers) != len(rs):
            spec["round_structure"] = kept_layers
            notes.append(
                f"Removed {len(rs) - len(kept_layers)} key-add/constant layer(s) from the data "
                f"path: the key_archetype injects them (round_structure is the data path only)."
            )

    return spec, notes


def build_cipher_spec_draft(facts: CipherFacts) -> CipherSpecDraft:
    """Build a user-reviewable CipherSpec draft from extracted facts."""

    fact_errors, fact_warnings = validate_cipher_facts(facts)
    spec_payload = cipher_spec_payload_from_facts(facts)
    # Deterministic self-repair first: fix mechanical errors with a single correct value so
    # they never reach the LLM repair loop or the user.
    spec_payload, deterministic_fixes = apply_deterministic_fixes(spec_payload)
    spec_errors = validate_cipher_spec_payload(spec_payload)

    assumptions = [
        operation["assumption"]
        for operation in facts.operations
        if operation.get("assumption")
    ]
    clarification_questions = []
    if fact_errors:
        clarification_questions.append("Please provide the missing or inconsistent cipher fields.")
    if facts.ambiguities:
        clarification_questions.append("Please resolve the listed ambiguities before building the cipher.")

    repair_log = []
    if deterministic_fixes:
        repair_log.append({"source": "deterministic", "fixes": deterministic_fixes})

    return CipherSpecDraft(
        spec=spec_payload,
        validation_errors=fact_errors + [err for err in spec_errors if err not in fact_errors],
        warnings=fact_warnings,
        assumptions=assumptions,
        clarification_questions=clarification_questions,
        requires_user_confirmation=True,
        repair_log=repair_log,
    )
