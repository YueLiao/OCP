from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.analysis_common import (
    analysis_success_result,
    build_solver_config,
    run_analysis_attack,
    validate_analysis_params,
)
from agent.skills.artifacts import trail_artifact_links
from agent.skills.base import BaseSkill

VALID_GOALS = [
    "LINEAR_SBOXCOUNT",
    "LINEARPATH_CORR",
    "LINEARHULL_CORR",
    "TRUNCATEDLINEAR_SBOXCOUNT",
]


class LinearAnalysisSkill(BaseSkill):

    @property
    def name(self) -> SkillName:
        return SkillName.LINEAR_ANALYSIS

    @property
    def description(self) -> str:
        return (
            "Run linear cryptanalysis on the current cipher. "
            "Supports MILP and SAT solvers. "
            "Goals: " + ", ".join(VALID_GOALS)
        )

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "goal": {
                "type": "string",
                "required": False,
                "default": "LINEARPATH_CORR",
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
            default_goal="LINEARPATH_CORR",
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

        config_solver = build_solver_config(params)

        trails, failure = run_analysis_attack(
            skill_name=self.name,
            expected_error_prefix="Linear analysis failed",
            unexpected_error_prefix="Unexpected linear analysis failure",
            attack_fn=attacks.linear_attacks,
            cipher=cipher,
            goal=goal,
            constraints=normalized["constraints"],
            objective_target=normalized["objective_target"],
            show_mode=normalized["show_mode"],
            config_model=config_model,
            config_solver=config_solver,
        )
        if failure:
            return failure

        return analysis_success_result(
            skill_name=self.name,
            analysis_label="Linear",
            goal=goal,
            model_type=model_type,
            trails=trails,
            artifact_links=trail_artifact_links(trails),
        )
