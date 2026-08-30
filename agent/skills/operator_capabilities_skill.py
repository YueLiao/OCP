"""Skill that answers what operators OCP supports and what each one can model / implement.

It reads the declared capability surface via ``tools.operator_capabilities`` (the single
source of truth), so answers are accurate rather than guessed by the LLM.
"""

from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.base import BaseSkill


def _format_one(name: str, info: Dict[str, Any]) -> str:
    lines = [f"{name} ({info['module']})", "  model versions (generate_model):"]
    for model_type, versions in info["model_versions"].items():
        lines.append(f"    {model_type}: {', '.join(versions) or '(none)'}")
    impls = ", ".join(info["implementations"]) or "(none)"
    lines.append(f"  implementations (generate_implementation): {impls}")
    return "\n".join(lines)


def _format_all(caps: Dict[str, Dict[str, Any]]) -> str:
    lines = [f"OCP supports {len(caps)} operators:", ""]
    for name in caps:
        lines.append(_format_one(name, caps[name]))
        lines.append("")
    return "\n".join(lines).rstrip()


class OperatorCapabilitiesSkill(BaseSkill):
    """List supported operators, or describe one operator's modeling / implementation support."""

    @property
    def name(self) -> SkillName:
        return SkillName.OPERATOR_CAPABILITIES

    @property
    def description(self) -> str:
        return (
            "List the OPERATORS OCP supports (XOR, Sbox, ModAdd, Matrix, ...), or describe what a "
            "specific operator supports: which analysis MODEL versions its generate_model accepts "
            "(e.g. XORDIFF, LINEAR, TRUNCATEDDIFF, INTEGRAL_TWOSUBSET) and which implementation "
            "languages (python/c/verilog) it produces. Use ONLY for questions about OPERATORS/"
            "primitives-modeling, e.g. 'what operators are supported?' or 'what modeling does XOR "
            "support?'. NOT for a CIPHER's family versions (e.g. 'how many versions does KNOT "
            "have?', 'what versions of SKINNY') - those are cipher-catalog questions, not operator "
            "model versions."
        )

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "operator": {
                "type": "string",
                "required": False,
                "description": "Operator class name to describe (e.g. 'XOR', 'Sbox'). "
                               "Omit to list all supported operators.",
            }
        }

    def execute(self, request: SkillRequest, session: Session) -> SkillResult:
        # Imported lazily so the skill registry does not pull in the operator modules at startup.
        from tools.operator_capabilities import describe_operators

        try:
            caps = describe_operators()
        except Exception as exc:  # introspection failure should not crash the agent
            return SkillResult(success=False, skill=self.name,
                               error=f"Failed to read operator capabilities: {exc}")

        operator = (request.params or {}).get("operator")
        if operator:
            match = next((k for k in caps if k.lower() == operator.lower()), None)
            if match is None:
                available = ", ".join(caps)
                return SkillResult(
                    success=False, skill=self.name,
                    error=f"Unknown operator '{operator}'. Supported operators: {available}",
                )
            return SkillResult(success=True, skill=self.name, data={match: caps[match]},
                               summary=_format_one(match, caps[match]))

        return SkillResult(success=True, skill=self.name, data=caps, summary=_format_all(caps))
