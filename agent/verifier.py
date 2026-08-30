from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from solving.solving import is_solver_available


@dataclass
class VerificationResult:
    ok: bool
    blocking_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "blocking_errors": list(self.blocking_errors),
            "warnings": list(self.warnings),
        }


def verify_action(action: str, session, params: Optional[Dict[str, Any]] = None) -> VerificationResult:
    """Run lightweight preflight checks before risky Agent actions."""
    params = params or {}
    errors: List[str] = []
    warnings: List[str] = []

    if action in {"analyze", "code", "visualize"} and session.get_cipher() is None:
        errors.append("No cipher is loaded. Build or instantiate a cipher first.")

    if action == "analyze":
        model_type = params.get("model_type", "milp")
        if model_type not in {"milp", "sat"}:
            errors.append("model_type must be 'milp' or 'sat'.")
        else:
            solver = params.get("solver", "DEFAULT") or "DEFAULT"
            if not is_solver_available(model_type, solver):
                errors.append(f"Solver backend is not available or implemented: {model_type}/{solver}.")

    if action == "code":
        language = params.get("language", "python")
        if language not in {"python", "c", "verilog"}:
            errors.append("language must be 'python', 'c', or 'verilog'.")
        if params.get("test", True):
            warnings.append("Code generation tests may execute generated code for available test vectors.")

    if action == "visualize":
        warnings.append("Visualization writes a PDF artifact to the configured output directory.")

    return VerificationResult(ok=not errors, blocking_errors=errors, warnings=warnings)
