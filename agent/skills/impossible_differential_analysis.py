from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.analysis_common import build_solver_config, run_analysis_attack
from agent.skills.base import BaseSkill


class ImpossibleDifferentialAnalysisSkill(BaseSkill):
    """Enumerate impossible-differential distinguishers (truncated, miss-in-the-middle).

    Wraps attacks.impossible_differential_attacks. Returns the impossible
    ``(input_positions, output_positions)`` truncated-difference pairs.
    """

    @property
    def name(self) -> SkillName:
        return SkillName.IMPOSSIBLE_DIFFERENTIAL_ANALYSIS

    @property
    def description(self) -> str:
        return (
            "Search for impossible-differential distinguishers of the current cipher "
            "(truncated, miss-in-the-middle). Supports MILP and SAT. Returns the impossible "
            "(input, output) active-word position pairs."
        )

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "model_type": {
                "type": "string",
                "required": False,
                "default": "milp",
                "description": "Solver backend: 'milp' or 'sat'.",
                "enum": ["milp", "sat"],
            },
            "show_mode": {
                "type": "int",
                "required": False,
                "default": 0,
                "description": "Display mode for results.",
            },
            "solver": {
                "type": "string",
                "required": False,
                "description": "Solver name (e.g., 'DEFAULT', 'GUROBI', 'SCIP').",
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
        model_type = params.get("model_type", "milp")
        if model_type not in ("milp", "sat"):
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Invalid model_type: '{model_type}'. Use 'milp' or 'sat'.",
            )

        distinguishers, failure = run_analysis_attack(
            skill_name=self.name,
            expected_error_prefix="Impossible-differential analysis failed",
            unexpected_error_prefix="Unexpected impossible-differential analysis failure",
            attack_fn=attacks.impossible_differential_attacks,
            cipher=cipher,
            goal="IMPOSSIBLETRUNCATEDDIFF",
            config_model={"model_type": model_type},
            config_solver=build_solver_config(params),
            show_mode=params.get("show_mode", 0),
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
                "goal": "IMPOSSIBLETRUNCATEDDIFF",
                "model_type": model_type,
            },
            summary=f"Impossible-differential analysis ({model_type.upper()}): found {count} distinguisher(s).",
        )
