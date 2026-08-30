"""P2.3 multi-step pipeline composition + orchestrated chat turns.

`plan_from_requests` composes a list of SkillRequests into a verified controller plan (each
skill gated + repaired via the default registry, state flowing through the session). These
tests are hermetic: skills are faked, so they pin the composition/registry/orchestration
mechanics, not any real skill's behavior.
"""

from agent.controller import (
    ActionResult, AgentController, RunReport, StepOutcome,
    plan_from_requests, default_gate_for, default_repair_for,
    definition_verdict_gate, analysis_verdict_gate,
)
from agent.core import AgentCore
from agent.session import Session
from agent.types import SkillName, SkillRequest, SkillResult, UserIntent

import pytest


@pytest.fixture(autouse=True)
def _no_primitive_persist(monkeypatch):
    # Suppress the CIPHER_DEFINITION skill's auto-export to primitives/ + catalog registration,
    # so a real build step in these tests never pollutes the tracked primitives/ directory.
    monkeypatch.setattr("agent.skills.cipher_definition._persist_primitive", lambda spec: None)


# --- the skill -> gate/repair registry --------------------------------------

def test_default_gate_for_maps_skills():
    assert default_gate_for(SkillName.CIPHER_DEFINITION) is definition_verdict_gate
    assert default_gate_for(SkillName.DIFFERENTIAL_ANALYSIS) is analysis_verdict_gate
    assert default_gate_for(SkillName.TWO_STAGE_TRAIL_SEARCH) is analysis_verdict_gate
    assert default_gate_for(SkillName.CIPHER_INSTANTIATION) is None


def test_default_repair_for_only_backend_swappable_analysis():
    assert callable(default_repair_for(SkillName.DIFFERENTIAL_ANALYSIS, {}))
    assert callable(default_repair_for(SkillName.IMPOSSIBLE_DIFFERENTIAL_ANALYSIS, {}))
    assert default_repair_for(SkillName.INTEGRAL_ANALYSIS, {}) is None       # milp-only
    assert default_repair_for(SkillName.TWO_STAGE_TRAIL_SEARCH, {}) is None  # no model_type
    assert default_repair_for(SkillName.CIPHER_DEFINITION, {}) is None


# --- plan_from_requests -----------------------------------------------------

def _fake_execute(results_by_skill):
    seen = []

    def execute(req):
        seen.append((req.skill, dict(req.params)))
        return results_by_skill[req.skill](req)
    execute.seen = seen
    return execute


def test_pipeline_runs_all_steps_and_strips_internal_params():
    def ok(req):
        return SkillResult(success=True, skill=req.skill, summary=f"{req.skill.value} ok")

    execute = _fake_execute({SkillName.CIPHER_INSTANTIATION: ok, SkillName.CODE_GENERATION: ok})
    reqs = [
        SkillRequest(SkillName.CIPHER_INSTANTIATION, {"cipher": "x", "_internal": 1}),
        SkillRequest(SkillName.CODE_GENERATION, {"language": "python"}),
    ]
    report = AgentController().run("g", plan_from_requests(reqs, execute=execute))
    assert report.ok and [o.status for o in report.outcomes] == ["passed", "passed"]
    # the internal "_internal" key never reaches the skill
    assert execute.seen[0][1] == {"cipher": "x"}


def test_pipeline_halts_on_required_build_kat_failure():
    def failing_build(req):
        return SkillResult(success=True, skill=req.skill,
                           data={"verification": {"tested": True, "all_passed": False,
                                                  "passed": 0, "total": 1}})

    def analysis(req):
        return SkillResult(success=True, skill=req.skill, data={"trail_count": 0, "trails": []})

    execute = _fake_execute({SkillName.CIPHER_DEFINITION: failing_build,
                             SkillName.DIFFERENTIAL_ANALYSIS: analysis})
    reqs = [SkillRequest(SkillName.CIPHER_DEFINITION, {"spec": {}}),
            SkillRequest(SkillName.DIFFERENTIAL_ANALYSIS, {})]
    report = AgentController(max_attempts=1).run("build then analyze",
                                                plan_from_requests(reqs, execute=execute))
    assert report.status == "failed"
    assert [o.name for o in report.outcomes] == ["cipher_definition"]         # analysis never ran


def test_pipeline_analysis_backend_fallback(monkeypatch):
    monkeypatch.setattr("agent.controller._available_backends", lambda: {"milp": False, "sat": True})

    def diff(req):
        if req.params.get("model_type", "milp") == "milp":
            return SkillResult(success=False, skill=req.skill, error="no MILP solver")
        return SkillResult(success=True, skill=req.skill,
                           data={"trail_count": 1, "trails": [{"w": 3}]})

    execute = _fake_execute({SkillName.DIFFERENTIAL_ANALYSIS: diff})
    reqs = [SkillRequest(SkillName.DIFFERENTIAL_ANALYSIS, {"model_type": "milp"})]
    report = AgentController(max_attempts=2).run("g", plan_from_requests(reqs, execute=execute))
    assert report.ok and report.outcomes[0].attempts == 2
    assert execute.seen[-1][1]["model_type"] == "sat"                         # retried on sat


def test_analysis_step_failure_is_best_effort_and_does_not_halt(monkeypatch):
    # #4: an independent analysis failing is reported (skipped) but the pipeline continues,
    # matching the sequential path (which runs every request).
    monkeypatch.setattr("agent.controller._available_backends", lambda: {"milp": False, "sat": False})

    def failing(req):
        return SkillResult(success=False, skill=req.skill, error="no solver")

    def ok(req):
        return SkillResult(success=True, skill=req.skill, data={"trail_count": 0, "trails": []})

    execute = _fake_execute({SkillName.DIFFERENTIAL_ANALYSIS: failing, SkillName.LINEAR_ANALYSIS: ok})
    reqs = [SkillRequest(SkillName.DIFFERENTIAL_ANALYSIS, {}), SkillRequest(SkillName.LINEAR_ANALYSIS, {})]
    report = AgentController(max_attempts=1).run("g", plan_from_requests(reqs, execute=execute))
    assert report.status == "success"                              # optional failure != run failure
    assert [o.status for o in report.outcomes] == ["skipped", "passed"]


def test_pipeline_build_kat_repair_via_repair_spec():
    # #3: a build step gets KAT self-repair when repair_spec is supplied (pipeline/chat parity
    # with build_and_verify_cipher). Build fails KAT until repair_spec marks the spec fixed.
    def build(req):
        good = req.params.get("spec", {}).get("fixed") is True
        return SkillResult(success=True, skill=req.skill,
                           data={"verification": {"tested": True, "all_passed": good,
                                                  "passed": int(good), "total": 1}})

    def repair_spec(spec, problems):
        fixed = dict(spec)
        fixed["fixed"] = True
        return fixed

    execute = _fake_execute({SkillName.CIPHER_DEFINITION: build})
    reqs = [SkillRequest(SkillName.CIPHER_DEFINITION, {"spec": {"fixed": False}})]
    plan = plan_from_requests(reqs, execute=execute, repair_spec=repair_spec)
    report = AgentController(max_attempts=2).run("build", plan)
    assert report.ok and report.outcomes[0].attempts == 2


def test_pipeline_no_repair_spec_leaves_build_unrepaired():
    # without repair_spec a KAT-failing build has no repair and halts (unchanged behavior)
    def build(req):
        return SkillResult(success=True, skill=req.skill,
                           data={"verification": {"tested": True, "all_passed": False,
                                                  "passed": 0, "total": 1}})
    execute = _fake_execute({SkillName.CIPHER_DEFINITION: build})
    reqs = [SkillRequest(SkillName.CIPHER_DEFINITION, {"spec": {}})]
    report = AgentController(max_attempts=3).run("build", plan_from_requests(reqs, execute=execute))
    assert report.status == "failed" and report.outcomes[0].attempts == 1


def test_duplicate_skills_get_distinct_step_names():
    def ok(req):
        return SkillResult(success=True, skill=req.skill)
    execute = _fake_execute({SkillName.LINEAR_ANALYSIS: ok})
    reqs = [SkillRequest(SkillName.LINEAR_ANALYSIS, {}), SkillRequest(SkillName.LINEAR_ANALYSIS, {})]
    report = AgentController().run("g", plan_from_requests(reqs, execute=execute))
    assert [o.name for o in report.outcomes] == ["linear_analysis", "linear_analysis#2"]


# --- OCPAgent.run_pipeline (real build step) --------------------------------

def _identity_perm_spec():
    return {
        "name": "PipeIdent", "cipher_type": "permutation",
        "block_size": 8, "word_bitsize": 4, "nbr_words": 2, "nbr_rounds": 1,
        "round_structure": [{"layer_type": "permutation", "params": {"table": [0, 1]}}],
        "test_vectors": [[[1, 2], [1, 2]]],
    }


def test_run_pipeline_real_build_passes_and_sets_session_cipher():
    from agent.interfaces.api import OCPAgent
    agent = OCPAgent()
    report = agent.run_pipeline([
        {"skill": "cipher_definition", "params": {"spec": _identity_perm_spec()}},
    ])
    assert report.ok and report.outcomes[0].status == "passed"
    assert agent.session.get_cipher() is not None


# --- orchestrated process_message -------------------------------------------

class _FakeSkill:
    def __init__(self, name, result):
        self._name, self._result = name, result

    @property
    def name(self):
        return self._name

    def execute(self, request, session):
        return self._result

    def to_descriptor(self):
        return {"name": self._name.value}


class _FakeLLM:
    def __init__(self, requests):
        self._requests = requests

    def parse_user_request(self, **kwargs):
        return UserIntent(requests=self._requests)


def test_process_message_orchestrated_runs_through_controller():
    from agent.skills import SkillRegistry
    registry = SkillRegistry()
    result = SkillResult(success=True, skill=SkillName.CIPHER_INSTANTIATION, summary="instantiated speck")
    registry.register(_FakeSkill(SkillName.CIPHER_INSTANTIATION, result))

    core = AgentCore(
        llm_provider=_FakeLLM([SkillRequest(SkillName.CIPHER_INSTANTIATION, {"cipher": "speck"})]),
        skill_registry=registry,
        orchestrate=True,
    )
    response = core.process_message("load speck")
    assert "instantiated speck" in response
    # the orchestrated turn still records last_requests like the sequential path
    assert core.session.get_metadata("last_requests")[0]["skill"] == "cipher_instantiation"


def test_orchestration_off_by_default_uses_sequential_path():
    from agent.skills import SkillRegistry
    registry = SkillRegistry()
    result = SkillResult(success=True, skill=SkillName.CIPHER_INSTANTIATION, summary="seq path")
    registry.register(_FakeSkill(SkillName.CIPHER_INSTANTIATION, result))
    core = AgentCore(
        llm_provider=_FakeLLM([SkillRequest(SkillName.CIPHER_INSTANTIATION, {})]),
        skill_registry=registry,
    )  # orchestrate defaults False
    assert not core._orchestrate_enabled()
    assert "seq path" in core.process_message("go")


def test_orchestrate_enabled_metadata_overrides_constructor():
    # constructor default holds when no per-session choice is set...
    on_default = AgentCore(orchestrate=True)
    off_default = AgentCore(orchestrate=False)
    assert on_default._orchestrate_enabled() and not off_default._orchestrate_enabled()
    # ...and an explicit session choice overrides it in BOTH directions
    on_default.session.set_metadata("orchestrate", False)
    off_default.session.set_metadata("orchestrate", True)
    assert not on_default._orchestrate_enabled() and off_default._orchestrate_enabled()


def test_summarize_report_formats_each_status():
    report = RunReport(goal="g", outcomes=[
        StepOutcome("a", "passed", summary="a done"),
        StepOutcome("b", "failed", error="broke"),
        StepOutcome("c", "skipped", error="meh"),
    ])
    text = AgentCore._summarize_report(report)
    assert "a done" in text and "b failed: broke" in text and "c: skipped (meh)" in text
