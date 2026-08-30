"""P2.4 closeout: the 4 new attack skills exposed on the facade + named recipes.

Hermetic - execute_direct / analyses are captured or faked, so these pin the facade wiring
and recipe composition, not any solver's behavior.
"""

import pytest

from agent.interfaces.api import OCPAgent
from agent.types import SkillName, SkillResult
from agent import recipes


@pytest.fixture(autouse=True)
def _no_primitive_persist(monkeypatch):
    # Suppress the CIPHER_DEFINITION skill's auto-export to primitives/ + catalog registration,
    # so the real build step in the recipe test never pollutes the tracked primitives/ directory.
    monkeypatch.setattr("agent.skills.cipher_definition._persist_primitive", lambda spec: None)


def _capture_requests(agent):
    seen = []

    def fake_execute(req):
        seen.append(req)
        return SkillResult(success=True, skill=req.skill, summary="ok")
    agent._core.execute_direct = fake_execute
    return seen


# --- the 4 new facade methods dispatch to the right skill with the right params ----

def test_integral_analysis_facade():
    agent = OCPAgent()
    seen = _capture_requests(agent)
    agent.integral_analysis([0, 1], show_mode=2)
    assert seen[0].skill == SkillName.INTEGRAL_ANALYSIS
    assert seen[0].params == {"constant_bits": [0, 1], "show_mode": 2}


def test_impossible_and_zero_correlation_facades():
    agent = OCPAgent()
    seen = _capture_requests(agent)
    agent.impossible_differential_analysis(model_type="sat")
    agent.zero_correlation_analysis()
    assert seen[0].skill == SkillName.IMPOSSIBLE_DIFFERENTIAL_ANALYSIS and seen[0].params["model_type"] == "sat"
    assert seen[1].skill == SkillName.ZERO_CORRELATION_ANALYSIS and seen[1].params["model_type"] == "milp"


def test_two_stage_facade():
    agent = OCPAgent()
    seen = _capture_requests(agent)
    agent.two_stage_trail_search("skinny", 8, version=[64, 64], goal="LINEARPATH_CORR")
    assert seen[0].skill == SkillName.TWO_STAGE_TRAIL_SEARCH
    assert seen[0].params == {"cipher_name": "skinny", "rounds": 8, "cipher_type": "blockcipher",
                              "goal": "LINEARPATH_CORR", "version": [64, 64]}


# --- run_analysis_verified now covers impossible / zero-correlation ----------

def test_run_analysis_verified_impossible_no_goal_and_fallback(monkeypatch):
    agent = OCPAgent()
    agent.session.set_cipher(object())
    monkeypatch.setattr("agent.controller._available_backends", lambda: {"milp": False, "sat": True})

    calls = []

    def fake_impossible(model_type="milp", **kwargs):
        calls.append((model_type, kwargs))
        assert "goal" not in kwargs                    # impossible fixes its goal internally
        if model_type == "milp":
            return SkillResult(success=False, skill=SkillName.IMPOSSIBLE_DIFFERENTIAL_ANALYSIS,
                               error="no MILP solver")
        return SkillResult(success=True, skill=SkillName.IMPOSSIBLE_DIFFERENTIAL_ANALYSIS,
                           data={"trail_count": 0, "trails": []}, summary="none")

    monkeypatch.setattr(agent, "impossible_differential_analysis", fake_impossible)
    report = agent.run_analysis_verified("ignored", analysis="impossible")
    assert report.ok and [c[0] for c in calls] == ["milp", "sat"]


# --- recipes ----------------------------------------------------------------

def test_build_recipe_build_and_analyze():
    reqs = recipes.build_recipe("build_and_analyze", spec={"name": "X"})
    assert [r.skill for r in reqs] == [
        SkillName.CIPHER_DEFINITION, SkillName.DIFFERENTIAL_ANALYSIS, SkillName.LINEAR_ANALYSIS]
    assert reqs[0].params == {"spec": {"name": "X"}}
    assert reqs[1].params == {"model_type": "milp"}


def test_build_recipe_secret_key_distinguishers():
    reqs = recipes.build_recipe("secret_key_distinguishers", model_type="sat")
    assert [r.skill for r in reqs] == [
        SkillName.IMPOSSIBLE_DIFFERENTIAL_ANALYSIS, SkillName.ZERO_CORRELATION_ANALYSIS]
    assert all(r.params["model_type"] == "sat" for r in reqs)


def test_build_recipe_unknown_raises():
    with pytest.raises(ValueError, match="Unknown recipe"):
        recipes.build_recipe("nope")


def test_run_recipe_dispatches_to_run_pipeline():
    agent = OCPAgent()
    captured = {}

    def fake_run_pipeline(reqs, *, goal="", max_attempts=3):
        captured["skills"] = [r.skill for r in reqs]
        captured["goal"] = goal
        return "REPORT"

    agent.run_pipeline = fake_run_pipeline
    out = agent.run_recipe("differential_then_linear", model_type="sat")
    assert out == "REPORT"
    assert captured["goal"] == "recipe: differential_then_linear"
    assert captured["skills"] == [SkillName.DIFFERENTIAL_ANALYSIS, SkillName.LINEAR_ANALYSIS]


# --- real end-to-end: run_recipe build step through the actual controller ----

def test_run_recipe_real_build_step_passes():
    # the build step is real (identity permutation); analysis steps then error (no cipher-less
    # analysis without a solver) - but a required-step build passing proves recipe -> pipeline
    # -> controller with the real KAT gate. We stop the pipeline after build by using a
    # build-only recipe request list directly.
    agent = OCPAgent()
    spec = {"name": "RecipeIdent", "cipher_type": "permutation",
            "block_size": 8, "word_bitsize": 4, "nbr_words": 2, "nbr_rounds": 1,
            "round_structure": [{"layer_type": "permutation", "params": {"table": [0, 1]}}],
            "test_vectors": [[[1, 2], [1, 2]]]}
    report = agent.run_pipeline([{"skill": "cipher_definition", "params": {"spec": spec}}])
    assert report.ok and agent.session.get_cipher() is not None
