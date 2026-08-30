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
