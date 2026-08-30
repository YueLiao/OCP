from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class SkillName(Enum):
    CIPHER_INSTANTIATION = "cipher_instantiation"
    CODE_GENERATION = "code_generation"
    VISUALIZATION = "visualization"
    DIFFERENTIAL_ANALYSIS = "differential_analysis"
    LINEAR_ANALYSIS = "linear_analysis"
    INTEGRAL_ANALYSIS = "integral_analysis"
    IMPOSSIBLE_DIFFERENTIAL_ANALYSIS = "impossible_differential_analysis"
    ZERO_CORRELATION_ANALYSIS = "zero_correlation_analysis"
    TWO_STAGE_TRAIL_SEARCH = "two_stage_trail_search"
    CIPHER_DEFINITION = "cipher_definition"
    CIPHER_DIALOGUE = "cipher_dialogue"
    CIPHER_EXTRACTION = "cipher_extraction"
    OPERATOR_CAPABILITIES = "operator_capabilities"


@dataclass
class SkillRequest:
    skill: SkillName
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    success: bool
    skill: SkillName
    data: Any = None
    summary: str = ""
    error: Optional[str] = None


@dataclass
class UserIntent:
    requests: List[SkillRequest] = field(default_factory=list)
    raw_text: str = ""
    needs_clarification: bool = False
    clarification_prompt: str = ""


@dataclass
class ClarificationRequest:
    """A piece the agent could not auto-resolve while building a cipher, surfaced so the user
    can resolve it conversationally (the human-in-the-loop clarification loop).

    e.g. a version's S-box has no table and is not a built-in - the user can point to a built-in
    ("use Midori128_SSb0-3"), paste the table, or skip the version.
    """
    kind: str                                       # "missing_sbox" (extensible)
    item: str                                       # the missing name, e.g. "SSb"
    context: str                                    # human-readable description of the gap
    options: List[str] = field(default_factory=list)      # resolution options offered
    suggestions: List[str] = field(default_factory=list)  # e.g. built-in names that may match
    version: Optional[str] = None                   # the family version this blocks, if any

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "item": self.item, "context": self.context,
                "options": list(self.options), "suggestions": list(self.suggestions),
                "version": self.version}

    def prompt_line(self) -> str:
        """A one-block chat message asking the user to resolve this gap."""
        lines = [f"⚠️ Need your help: {self.context}"]
        if self.suggestions:
            lines.append(f"   Likely built-in match(es): {', '.join(self.suggestions)}")
        if self.options:
            lines.append("   You can: " + "; ".join(self.options))
        return "\n".join(lines)
