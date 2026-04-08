from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
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
        goal = params.get("goal", "LINEARPATH_CORR")
        model_type = params.get("model_type", "milp")
        constraints = params.get("constraints", ["INPUT_NOT_ZERO"])
        objective_target = params.get("objective_target", "OPTIMAL")
        show_mode = params.get("show_mode", 0)

        if goal not in VALID_GOALS:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Invalid goal: '{goal}'. Valid: {VALID_GOALS}",
            )

        # Build config_model
        config_model = {"model_type": model_type}

        # Build config_solver
        config_solver = None
        if "solver" in params or "solution_number" in params:
            config_solver = {}
            if "solver" in params:
                config_solver["solver"] = params["solver"]
            if "solution_number" in params:
                config_solver["solution_number"] = params["solution_number"]

        try:
            trails = attacks.linear_attacks(
                cipher,
                goal=goal,
                constraints=constraints,
                objective_target=objective_target,
                show_mode=show_mode,
                config_model=config_model,
                config_solver=config_solver,
            )
            trail_count = len(trails) if trails else 0
            summary = (
                f"Linear analysis ({model_type.upper()}, {goal}): "
                f"found {trail_count} trail(s)."
            )
            return SkillResult(
                success=True,
                skill=self.name,
                data={"trails": trails, "trail_count": trail_count, "goal": goal, "model_type": model_type},
                summary=summary,
            )
        except Exception as e:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Linear analysis failed: {e}",
            )
