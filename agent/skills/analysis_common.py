"""Shared helpers for agent analysis skills."""

from agent.types import SkillResult

EXPECTED_ANALYSIS_ERRORS = (ValueError, RuntimeError)


def validate_analysis_params(params, *, valid_goals, default_goal):
    """Validate common differential/linear analysis request parameters."""

    goal = params.get("goal", default_goal)
    model_type = params.get("model_type", "milp")
    constraints = params.get("constraints", ["INPUT_NOT_ZERO"])
    objective_target = params.get("objective_target", "OPTIMAL")
    show_mode = params.get("show_mode", 0)

    if goal not in valid_goals:
        return None, f"Invalid goal: '{goal}'. Valid: {valid_goals}"
    if model_type not in ("milp", "sat"):
        return None, f"Invalid model_type: '{model_type}'. Use 'milp' or 'sat'."
    if not isinstance(constraints, list) or any(not isinstance(item, str) for item in constraints):
        return None, "Invalid constraints: expected a list of strings."
    if "solution_number" in params:
        solution_number = params["solution_number"]
        if not isinstance(solution_number, int) or solution_number <= 0:
            return None, "Invalid solution_number: use a positive integer."

    return {
        "goal": goal,
        "model_type": model_type,
        "constraints": constraints,
        "objective_target": objective_target,
        "show_mode": show_mode,
    }, None


def build_solver_config(params):
    """Build a solver config dictionary only when solver params are supplied."""

    if "solver" not in params and "solution_number" not in params:
        return None
    config_solver = {}
    if "solver" in params:
        config_solver["solver"] = params["solver"]
    if "solution_number" in params:
        config_solver["solution_number"] = params["solution_number"]
    return config_solver


def analysis_success_result(
    *,
    skill_name,
    analysis_label,
    goal,
    model_type,
    trails,
    artifact_links,
):
    """Build the common successful SkillResult payload for analysis skills."""

    trail_count = len(trails) if trails else 0
    return SkillResult(
        success=True,
        skill=skill_name,
        data={
            "trails": trails,
            "trail_count": trail_count,
            "goal": goal,
            "model_type": model_type,
            "artifact_links": artifact_links,
        },
        summary=f"{analysis_label} cryptanalysis ({model_type.upper()}, {goal}): found {trail_count} trail(s).",
    )


def run_analysis_attack(
    *,
    skill_name,
    expected_error_prefix,
    unexpected_error_prefix,
    attack_fn,
    **attack_kwargs,
):
    """Run an attack function and classify expected solver/model failures."""

    try:
        return attack_fn(**attack_kwargs), None
    except EXPECTED_ANALYSIS_ERRORS as exc:
        return None, SkillResult(
            success=False,
            skill=skill_name,
            error=f"{expected_error_prefix}: {exc}",
        )
    except Exception as exc:
        return None, SkillResult(
            success=False,
            skill=skill_name,
            error=f"{unexpected_error_prefix}: {exc}",
        )
