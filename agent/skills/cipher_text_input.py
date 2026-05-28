"""Text-first data models for cipher extraction workflows."""

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
SUPPORTED_OPERATIONS = {
    "add_constant",
    "add_round_key",
    "and",
    "matrix",
    "modadd",
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

    @property
    def is_valid(self) -> bool:
        """Whether the draft has no blocking validation errors."""

        return not self.validation_errors

    def validate_spec(self) -> List[str]:
        """Validate the proposed CipherSpec payload and refresh blocking errors."""

        errors = validate_cipher_spec_payload(self.spec)
        self.validation_errors = errors
        return errors


def normalize_cipher_text(text: str) -> str:
    """Normalize plain/Markdown/LaTeX cipher text for downstream parsing."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    for latex_token, replacement in _LATEX_TOKEN_REPLACEMENTS.items():
        normalized = normalized.replace(latex_token, replacement)

    lines = []
    previous_blank = False
    for line in normalized.split("\n"):
        clean_line = line.rstrip()
        is_blank = clean_line.strip() == ""
        if is_blank and previous_blank:
            continue
        lines.append(clean_line)
        previous_blank = is_blank

    return "\n".join(lines).strip()


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


def _operation_type(operation):
    return operation.get("layer_type") or operation.get("type") or operation.get("operation")


def _operation_params(operation):
    return operation.get("params", operation.get("parameters", {}))


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

    if not facts.operations:
        errors.append("At least one round operation is required.")
    for index, operation in enumerate(facts.operations):
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

    if facts.primitive_type == "blockcipher":
        key_size = facts.key_schedule.get("key_size")
        key_nbr_words = facts.key_schedule.get("key_nbr_words")
        if not _positive_int(key_size):
            errors.append("Block cipher key_size must be a positive integer.")
        if not _positive_int(key_nbr_words):
            errors.append("Block cipher key_nbr_words must be a positive integer.")
        if "key_extract_indices" not in facts.key_schedule:
            errors.append("Block cipher key_extract_indices is required.")

    if facts.ambiguities:
        warnings.extend(f"Ambiguity: {ambiguity}" for ambiguity in facts.ambiguities)

    return errors, warnings


def cipher_spec_payload_from_facts(facts: CipherFacts) -> Dict[str, Any]:
    """Convert validated facts into a CipherSpec-compatible dictionary."""

    state = facts.state
    rounds = facts.rounds
    key_schedule = facts.key_schedule
    payload = {
        "name": facts.name or "CustomCipher",
        "cipher_type": facts.primitive_type or "permutation",
        "block_size": state.get("block_size") or state.get("state_size_bits") or 0,
        "word_bitsize": state.get("word_bitsize") or state.get("unit_size_bits") or 0,
        "nbr_words": state.get("nbr_words") or state.get("num_units") or 0,
        "nbr_rounds": rounds.get("nbr_rounds") or rounds.get("num_rounds") or 0,
        "nbr_temp_words": state.get("nbr_temp_words", 0),
        "round_structure": [
            {
                "layer_type": _operation_type(operation),
                "params": _operation_params(operation),
            }
            for operation in facts.operations
        ],
        "sbox_tables": facts.tables.get("sbox_tables") or facts.tables.get("sboxes") or {},
    }

    if facts.primitive_type == "blockcipher":
        payload.update(
            {
                "key_size": key_schedule.get("key_size"),
                "key_word_bitsize": key_schedule.get("key_word_bitsize"),
                "key_nbr_words": key_schedule.get("key_nbr_words"),
                "key_nbr_temp_words": key_schedule.get("key_nbr_temp_words", 0),
                "key_schedule": key_schedule.get("round_structure", []),
                "key_extract_indices": key_schedule.get("key_extract_indices"),
            }
        )
    if facts.test_vectors:
        payload["test_vectors"] = facts.test_vectors
    return payload


def validate_cipher_spec_payload(spec_payload: Dict[str, Any]) -> List[str]:
    """Validate a CipherSpec-compatible dictionary without constructing a primitive."""

    try:
        spec = CipherSpec.from_dict(spec_payload)
        return spec.validate()
    except (KeyError, TypeError, ValueError) as exc:
        return [f"Invalid CipherSpec payload: {exc}"]


def build_cipher_spec_draft(facts: CipherFacts) -> CipherSpecDraft:
    """Build a user-reviewable CipherSpec draft from extracted facts."""

    fact_errors, fact_warnings = validate_cipher_facts(facts)
    spec_payload = cipher_spec_payload_from_facts(facts)
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

    return CipherSpecDraft(
        spec=spec_payload,
        validation_errors=fact_errors + [err for err in spec_errors if err not in fact_errors],
        warnings=fact_warnings,
        assumptions=assumptions,
        clarification_questions=clarification_questions,
        requires_user_confirmation=True,
    )
