from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.analysis_common import build_solver_config, run_analysis_attack
from agent.skills.artifacts import trail_artifact_links
from agent.skills.base import BaseSkill


class IntegralAnalysisSkill(BaseSkill):
    """Bit-based two-subset integral (division-property) distinguisher search.

    Unlike differential/linear analysis, integral analysis is MILP-only, targets the
    EXISTENCE of a provably balanced output bit, and needs the set of CONSTANT input
    bits (every other input bit is active/summed). Wraps attacks.integral_attacks.
    """

    @property
    def name(self) -> SkillName:
        return SkillName.INTEGRAL_ANALYSIS

    @property
    def description(self) -> str:
        return (
            "Run bit-based two-subset integral cryptanalysis on the current cipher to find a "
            "division-property distinguisher (a provably balanced output bit). MILP only. "
            "Requires constant_bits: the input bit positions held constant; all other input "
            "bits are active (summed over)."
        )

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "constant_bits": {
                "type": "list",
                "required": True,
                "description": "Input bit positions held constant (0-indexed); the rest are active/summed.",
            },
            "active_bits": {
                "type": "list",
                "required": False,
                "description": "Optional explicit active input bit positions (defaults to the complement of constant_bits).",
            },
            "show_mode": {
                "type": "int",
                "required": False,
                "default": 0,
                "description": "Display mode for results (0-3).",
            },
            "solver": {
                "type": "string",
                "required": False,
                "description": "MILP solver name (e.g., 'DEFAULT', 'GUROBI', 'SCIP').",
            },
            "solution_number": {
                "type": "int",
                "required": False,
                "description": "Number of solutions to find.",
            },
        }

    def execute(self, request: SkillRequest, session: Session) -> SkillResult:
        import attacks.attacks as attacks

        cipher = session.get_cipher()
        if cipher is None:
            return SkillResult(
                success=False,
                skill=self.name,
                error="No cipher loaded. Use cipher_instantiation first.",
            )

        params = request.params
        constant_bits = params.get("constant_bits")
        if (
            not isinstance(constant_bits, list)
            or not constant_bits
            or any(not isinstance(bit, int) for bit in constant_bits)
        ):
            return SkillResult(
                success=False,
                skill=self.name,
                error="Invalid constant_bits: provide a non-empty list of integer bit positions.",
            )

        # goal / objective_target / model_type are fixed: the core supports only this combination.
        config_model = {"model_type": "milp", "constant_bits": constant_bits}
        if "active_bits" in params:
            config_model["active_bits"] = params["active_bits"]

        config_solver = build_solver_config(params)

        distinguishers, failure = run_analysis_attack(
            skill_name=self.name,
            expected_error_prefix="Integral analysis failed",
            unexpected_error_prefix="Unexpected integral analysis failure",
            attack_fn=attacks.integral_attacks,
            cipher=cipher,
            goal="INTEGRAL_TWOSUBSET",
            constraints=["TWO_SUBSET_INIT"],
            objective_target="EXISTENCE",
            show_mode=params.get("show_mode", 0),
            config_model=config_model,
            config_solver=config_solver,
        )
        if failure:
            return failure

        count = len(distinguishers) if distinguishers else 0
        return SkillResult(
            success=True,
            skill=self.name,
            data={
                "distinguishers": distinguishers,
                "distinguisher_count": count,
                "goal": "INTEGRAL_TWOSUBSET",
                "model_type": "milp",
                "constant_bits": constant_bits,
                "artifact_links": trail_artifact_links(distinguishers),
            },
            summary=f"Integral cryptanalysis (MILP, INTEGRAL_TWOSUBSET): found {count} distinguisher(s).",
        )
