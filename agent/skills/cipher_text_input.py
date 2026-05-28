"""Text-first data models for cipher extraction workflows."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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


@dataclass
class CipherSpecDraft:
    """A candidate CipherSpec with validation notes before user confirmation."""

    spec: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    requires_user_confirmation: bool = True

    @property
    def is_valid(self) -> bool:
        """Whether the draft has no blocking validation errors."""

        return not self.validation_errors


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
