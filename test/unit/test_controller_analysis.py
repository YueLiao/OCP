"""P2.2 analysis gates + solver-backend fallback on the agentic harness.

Hermetic: no real solver. The analysis is mocked and _available_backends is patched, so these
pin the decision policy for analysis rather than any solver's behavior - a reached verdict
(distinguisher found OR provably none) passes; a solver/model error re-plans onto another
installed backend (milp <-> sat) and retries; an inconsistent trail set is rejected.
"""

from agent.controller import (
    ActionResult, Step, AgentController, analysis_verdict_gate, make_backend_fallback_repair,
)
from agent.types import SkillResult, SkillName


# --- analysis_verdict_gate --------------------------------------------------

def test_verdict_gate_passes_when_distinguisher_found():
    action = ActionResult(ok=True, data={"trail_count": 1, "trails": [{"weight": 5}]})
    assert analysis_verdict_gate({}, action) == []


def test_verdict_gate_passes_on_no_distinguisher():
    # 0 trails / UNSAT is a VALID finding, not a failure
    action = ActionResult(ok=True, data={"trail_count": 0, "trails": []})
    assert analysis_verdict_gate({}, action) == []


def test_verdict_gate_flags_count_without_trails():
    action = ActionResult(ok=True, data={"trail_count": 2, "trails": None})
    assert analysis_verdict_gate({}, action)          # non-empty problems


def test_verdict_gate_flags_degenerate_trail():
    action = ActionResult(ok=True, data={"trail_count": 2, "trails": [{"w": 1}, None]})
    assert analysis_verdict_gate({}, action)


def test_verdict_gate_reads_distinguisher_convention():
    # integral / impossible / zero-correlation emit distinguisher_count / distinguishers
    ok = ActionResult(ok=True, data={"distinguisher_count": 1, "distinguishers": [{"in": [0]}]})
    none = ActionResult(ok=True, data={"distinguisher_count": 0, "distinguishers": []})
    degenerate = ActionResult(ok=True, data={"distinguisher_count": 2, "distinguishers": [{"x": 1}, None]})
    missing = ActionResult(ok=True, data={"distinguisher_count": 1, "distinguishers": None})
    assert analysis_verdict_gate({}, ok) == []
    assert analysis_verdict_gate({}, none) == []
    assert analysis_verdict_gate({}, degenerate)
    assert analysis_verdict_gate({}, missing)


def test_verdict_gate_passes_two_stage_shape():
    # two-stage emits found / min_active_sboxes / best_weight - no count field, any verdict passes
    found = ActionResult(ok=True, data={"found": True, "min_active_sboxes": 3, "best_weight": 7})
    not_found = ActionResult(ok=True, data={"found": False})
    assert analysis_verdict_gate({}, found) == []
    assert analysis_verdict_gate({}, not_found) == []


# --- make_backend_fallback_repair -------------------------------------------

def test_fallback_swaps_milp_to_available_sat(monkeypatch):
    monkeypatch.setattr("agent.controller._available_backends", lambda: {"milp": False, "sat": True})
    repair = make_backend_fallback_repair()
    ctx = {"model_type": "milp"}
    assert repair(ctx, ["no MILP solver"], 1) is True
    assert ctx["model_type"] == "sat"
    # both now tried -> no further alternate
    assert repair(ctx, ["still broken"], 2) is False


def test_fallback_stops_when_no_alternate_available(monkeypatch):
    monkeypatch.setattr("agent.controller._available_backends", lambda: {"milp": False, "sat": False})
    ctx = {"model_type": "milp"}
    assert make_backend_fallback_repair()(ctx, ["boom"], 1) is False


# --- end-to-end through the controller (mocked analysis) ---------------------

def test_analysis_errors_then_backend_fallback_passes(monkeypatch):
    monkeypatch.setattr("agent.controller._available_backends", lambda: {"milp": False, "sat": True})

    def action(ctx):
        if ctx["model_type"] == "milp":
            return ActionResult(ok=False, error="no MILP solver installed")
        return ActionResult(ok=True, data={"trail_count": 1, "trails": [{"weight": 7}]},
                            summary="found 1 trail")

    step = Step("diff", action=action, gate=analysis_verdict_gate,
                repair=make_backend_fallback_repair())
    report = AgentController(max_attempts=2).run("analyze", [step], ctx={"model_type": "milp"})
    assert report.ok and report.outcomes[0].attempts == 2


def test_analysis_errors_no_backend_fails_without_spinning(monkeypatch):
    monkeypatch.setattr("agent.controller._available_backends", lambda: {"milp": False, "sat": False})
    step = Step("diff", action=lambda ctx: ActionResult(ok=False, error="no solver"),
                gate=analysis_verdict_gate, repair=make_backend_fallback_repair())
    report = AgentController(max_attempts=5).run("analyze", [step], ctx={"model_type": "milp"})
    assert report.status == "failed" and report.outcomes[0].attempts == 1   # no-progress stop


# --- facade: OCPAgent.run_analysis_verified ---------------------------------

def test_run_analysis_verified_falls_back_to_sat(monkeypatch):
    from agent.interfaces.api import OCPAgent
    agent = OCPAgent()
    agent.session.set_cipher(object())                 # pretend a cipher is built
    monkeypatch.setattr("agent.controller._available_backends", lambda: {"milp": False, "sat": True})

    seen = []

    def fake_diff(goal, model_type, **kw):
        seen.append(model_type)
        if model_type == "milp":
            return SkillResult(success=False, skill=SkillName.DIFFERENTIAL_ANALYSIS,
                               error="no MILP solver")
        return SkillResult(success=True, skill=SkillName.DIFFERENTIAL_ANALYSIS,
                           data={"trail_count": 0, "trails": []}, summary="no trail found")

    monkeypatch.setattr(agent, "differential_analysis", fake_diff)
    report = agent.run_analysis_verified("DIFFERENTIALPATH_PROB")
    assert report.ok and seen == ["milp", "sat"]       # tried milp, fell back to sat


def test_run_analysis_verified_requires_a_cipher():
    from agent.interfaces.api import OCPAgent
    report = OCPAgent().run_analysis_verified("DIFFERENTIALPATH_PROB", backend_fallback=False)
    assert report.status == "failed" and "no cipher" in report.outcomes[0].error


def test_run_analysis_verified_rejects_unknown_family():
    from agent.interfaces.api import OCPAgent
    import pytest
    with pytest.raises(ValueError, match="Unknown analysis"):
        OCPAgent().run_analysis_verified("X", analysis="bogus")
