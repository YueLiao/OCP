from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.analysis_common import (
    analysis_success_result,
    build_solver_config,
    validate_analysis_params,
)
from agent.skills.artifacts import trail_artifact_links
from agent.skills.base import BaseSkill

VALID_GOALS = [
    "DIFFERENTIAL_SBOXCOUNT",
    "DIFFERENTIALPATH_PROB",
    "DIFFERENTIAL_PROB",
    "TRUNCATEDDIFF_SBOXCOUNT",
]


class DifferentialAnalysisSkill(BaseSkill):

    @property
    def name(self) -> SkillName:
        return SkillName.DIFFERENTIAL_ANALYSIS

    @property
    def description(self) -> str:
        return (
            "Run differential cryptanalysis on the current cipher. "
            "Supports MILP and SAT solvers. "
            "Goals: " + ", ".join(VALID_GOALS)
        )

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "goal": {
                "type": "string",
                "required": False,
                "default": "DIFFERENTIALPATH_PROB",
                "description": "Analysis goal",
                "enum": VALID_GOALS,
            },
            "model_type": {
                "type": "string",
                "required": False,
                "default": "milp",
                "description": "Solver type: 'milp' or 'sat'",
                "enum": ["milp", "sat"],
            },
            "constraints": {
                "type": "list",
                "required": False,
                "default": ["INPUT_NOT_ZERO"],
                "description": "List of constraints (e.g., ['INPUT_NOT_ZERO'])",
            },
            "objective_target": {
                "type": "string",
                "required": False,
                "default": "OPTIMAL",
                "description": "Objective target: 'OPTIMAL', 'EXISTENCE', or 'AT MOST N'",
            },
            "show_mode": {
                "type": "int",
                "required": False,
                "default": 0,
                "description": "Display mode for results",
            },
            "input_diff": {
                "type": "string",
                "required": False,
                "description": "Fixed input difference (hex string)",
            },
            "output_diff": {
                "type": "string",
                "required": False,
                "description": "Fixed output difference (hex string)",
            },
            "solver": {
                "type": "string",
                "required": False,
                "description": "Solver name (e.g., 'DEFAULT', 'GUROBI', 'SCIP')",
            },
            "solution_number": {
                "type": "int",
                "required": False,
                "description": "Number of solutions to find",
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
        normalized, error = validate_analysis_params(
            params,
            valid_goals=VALID_GOALS,
            default_goal="DIFFERENTIALPATH_PROB",
        )
        if error:
            return SkillResult(
                success=False,
                skill=self.name,
                error=error,
            )
        goal = normalized["goal"]
        model_type = normalized["model_type"]

        # Build config_model
        config_model = {"model_type": model_type}
        if "input_diff" in params:
            config_model["input_diff"] = params["input_diff"]
        if "output_diff" in params:
            config_model["output_diff"] = params["output_diff"]

        config_solver = build_solver_config(params)

        try:
            trails = attacks.diff_attacks(
                cipher,
                goal=goal,
                constraints=normalized["constraints"],
                objective_target=normalized["objective_target"],
                show_mode=normalized["show_mode"],
                config_model=config_model,
                config_solver=config_solver,
            )
            return analysis_success_result(
                skill_name=self.name,
                analysis_label="Differential",
                goal=goal,
                model_type=model_type,
                trails=trails,
                artifact_links=trail_artifact_links(trails),
            )
        except (ValueError, RuntimeError) as e:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Differential analysis failed: {e}",
            )
        except Exception as e:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Unexpected differential analysis failure: {e}",
            )
