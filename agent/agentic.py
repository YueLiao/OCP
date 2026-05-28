from dataclasses import dataclass
from typing import Any, Dict


RISKY_ACTIONS = {"analyze", "code", "visualize", "confirm_cipher_spec"}


@dataclass(frozen=True)
class ExecutionTraceEntry:
    step: int
    event: str
    payload: Dict[str, Any]


def requires_confirmation(action: str) -> bool:
    return action in RISKY_ACTIONS
