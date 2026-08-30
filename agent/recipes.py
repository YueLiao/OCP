"""Named recipes: canned SkillRequest pipelines for the agentic harness.

A recipe is a function returning a list of SkillRequests that OCPAgent.run_pipeline runs as a
verified multi-step plan (each step gated + repaired by the controller's skill registry). They
package the common end-to-end flows - "build this spec, then run differential and linear trail
search on it" - so a caller (or the LLM) names the flow instead of assembling the requests.

Use via OCPAgent.run_recipe(name, **kwargs), or build_recipe(name, **kwargs) for the raw list.
"""

from agent.types import SkillName, SkillRequest


def build_and_analyze(spec, *, model_type="milp"):
    """Build a cipher from `spec`, then run differential + linear trail search on it.

    The built cipher flows to the analysis steps via the session; each analysis step is gated
    on reaching a verdict and repaired by solver-backend fallback (milp<->sat).
    """
    return [
        SkillRequest(SkillName.CIPHER_DEFINITION, {"spec": spec}),
        SkillRequest(SkillName.DIFFERENTIAL_ANALYSIS, {"model_type": model_type}),
        SkillRequest(SkillName.LINEAR_ANALYSIS, {"model_type": model_type}),
    ]


def differential_then_linear(*, model_type="milp"):
    """Differential then linear trail search on the ALREADY-loaded cipher (no build step)."""
    return [
        SkillRequest(SkillName.DIFFERENTIAL_ANALYSIS, {"model_type": model_type}),
        SkillRequest(SkillName.LINEAR_ANALYSIS, {"model_type": model_type}),
    ]


def secret_key_distinguishers(*, model_type="milp"):
    """The two secret-key distinguisher searches on the loaded cipher: impossible-differential
    and zero-correlation (both backend-swappable)."""
    return [
        SkillRequest(SkillName.IMPOSSIBLE_DIFFERENTIAL_ANALYSIS, {"model_type": model_type}),
        SkillRequest(SkillName.ZERO_CORRELATION_ANALYSIS, {"model_type": model_type}),
    ]


RECIPES = {
    "build_and_analyze": build_and_analyze,
    "differential_then_linear": differential_then_linear,
    "secret_key_distinguishers": secret_key_distinguishers,
}


def build_recipe(name, **kwargs):
    """Return the SkillRequest list for the named recipe (raises on an unknown name)."""
    if name not in RECIPES:
        raise ValueError(f"Unknown recipe '{name}'. Available: {sorted(RECIPES)}")
    return RECIPES[name](**kwargs)
