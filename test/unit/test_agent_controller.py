"""Mechanics of the agentic orchestration harness (agent/controller.py).

These tests exercise the plan -> act -> verify -> repair -> decide loop with plain fake
steps (no LLM, no crypto), plus one real objective gate (CipherSpec.validate) driven to
convergence by the engine. They pin the decision policy: retry-with-repair up to a budget,
stop on no-progress, halt on a required-step failure, skip an optional one, and honor
cancellation - and that a raising action/gate becomes a failed step, never a crash.
"""

import pytest

from agent.controller import (
    ActionResult, Step, AgentController, RunReport, StepOutcome, spec_validate_gate,
)
from agent.session import Session


@pytest.fixture(autouse=True)
def _no_primitive_persist(monkeypatch):
    # Building a real cipher through the CIPHER_DEFINITION skill auto-exports it to primitives/
    # and registers it in files/custom_ciphers.json. Suppress that side effect so these tests
    # never pollute the tracked primitives/ directory or the catalog.
    monkeypatch.setattr("agent.skills.cipher_definition._persist_primitive", lambda spec: None)


def _ok(summary="", data=None):
    return lambda ctx: ActionResult(ok=True, summary=summary, data=data)


# --- happy path -------------------------------------------------------------

def test_single_step_passes_first_try():
    ctrl = AgentController()
    plan = [Step("a", action=_ok("did a"))]
    report = ctrl.run("goal", plan)
    assert report.ok and report.status == "success"
    assert [o.status for o in report.outcomes] == ["passed"]
    assert report.outcomes[0].attempts == 1 and report.outcomes[0].summary == "did a"


def test_ctx_threads_between_steps():
    def produce(ctx):
        ctx["value"] = 41
        return ActionResult(ok=True)

    def consume(ctx):
        ctx["value"] += 1
        return ActionResult(ok=True, data=ctx["value"])

    report = AgentController().run("g", [Step("produce", produce), Step("consume", consume)])
    assert report.ok and report.outcomes[1].data == 42


# --- gate + repair loop -----------------------------------------------------

def test_gate_fails_then_repair_then_passes():
    # gate fails while ctx['fixed'] is False; repair flips it; the retry passes.
    def gate(ctx, action):
        return [] if ctx.get("fixed") else ["not fixed yet"]

    def repair(ctx, problems, attempt):
        ctx["fixed"] = True
        return True

    step = Step("s", action=_ok(), gate=gate, repair=repair)
    report = AgentController(max_attempts=3).run("g", [step], ctx={"fixed": False})
    assert report.ok
    assert report.outcomes[0].status == "passed" and report.outcomes[0].attempts == 2


def test_no_progress_repair_stops_early():
    # repair returns False (changed nothing) -> stop retrying immediately, do not burn budget.
    calls = {"gate": 0}

    def gate(ctx, action):
        calls["gate"] += 1
        return ["always broken"]

    step = Step("s", action=_ok(), gate=gate, repair=lambda ctx, p, a: False)
    report = AgentController(max_attempts=5).run("g", [step])
    assert report.status == "failed"
    assert report.outcomes[0].attempts == 1 and calls["gate"] == 1


def test_budget_exhaustion_fails():
    # repair always "changes" something but the gate never passes -> fail after `budget` tries.
    step = Step("s", action=_ok(), gate=lambda c, a: ["broken"], repair=lambda c, p, a: True)
    report = AgentController(max_attempts=3).run("g", [step])
    assert report.status == "failed"
    assert report.outcomes[0].attempts == 3
    assert report.outcomes[0].problems == ["broken"]


def test_per_step_max_attempts_override():
    step = Step("s", action=_ok(), gate=lambda c, a: ["x"], repair=lambda c, p, a: True, max_attempts=2)
    report = AgentController(max_attempts=9).run("g", [step])
    assert report.outcomes[0].attempts == 2


# --- decision policy --------------------------------------------------------

def test_required_failure_halts_the_run():
    plan = [
        Step("first", action=_ok(), gate=lambda c, a: ["boom"]),   # required, fails
        Step("second", action=_ok("should not run")),
    ]
    report = AgentController(max_attempts=1).run("g", plan)
    assert report.status == "failed"
    assert [o.name for o in report.outcomes] == ["first"]          # second never ran
    assert report.failed_step.name == "first"


def test_optional_failure_is_skipped_and_run_continues():
    plan = [
        Step("opt", action=_ok(), gate=lambda c, a: ["meh"], required=False),
        Step("next", action=_ok("ran")),
    ]
    report = AgentController(max_attempts=1).run("g", plan)
    assert report.ok                                               # optional skip != run failure
    assert [o.status for o in report.outcomes] == ["skipped", "passed"]


# --- cancellation -----------------------------------------------------------

def test_cancellation_before_a_step():
    flag = {"cancel": False}
    plan = [Step("a", action=_ok()), Step("b", action=_ok())]

    def first_then_cancel(ctx):
        flag["cancel"] = True                                     # cancel after step a's action
        return ActionResult(ok=True)

    plan[0] = Step("a", action=first_then_cancel)
    report = AgentController(is_cancelled=lambda: flag["cancel"]).run("g", plan)
    assert report.status == "cancelled"
    assert [o.name for o in report.outcomes] == ["a", "b"]
    assert report.outcomes[1].status == "cancelled"


# --- robustness: a raising action/gate is a failed step, not a crash --------

def test_raising_action_becomes_failed_step():
    def boom(ctx):
        raise RuntimeError("kaboom")

    report = AgentController(max_attempts=1).run("g", [Step("s", action=boom)])
    assert report.status == "failed" and "kaboom" in report.outcomes[0].error


def test_action_returning_wrong_type_is_failed():
    report = AgentController(max_attempts=1).run("g", [Step("s", action=lambda ctx: "nope")])
    assert report.status == "failed" and "expected ActionResult" in report.outcomes[0].error


def test_raising_gate_becomes_failed_step():
    def gate(ctx, action):
        raise ValueError("bad gate")

    report = AgentController(max_attempts=1).run("g", [Step("s", action=_ok(), gate=gate)])
    assert report.status == "failed" and "bad gate" in report.outcomes[0].error


# --- tracing ----------------------------------------------------------------

def test_run_is_traced_on_the_session():
    session = Session()
    ctrl = AgentController(session=session)
    ctrl.run("g", [Step("a", action=_ok())])
    events = [t["event"] for t in session.get_trace()]
    assert "controller_run_start" in events and "controller_run_finish" in events
    assert "controller_step_attempt" in events


# --- one real objective gate: CipherSpec.validate() -------------------------

def _tiny_spec(amount):
    # a valid tiny permutation, except `amount` may be >= word_bitsize (an invalid rotation)
    return {
        "name": "Tiny", "cipher_type": "permutation",
        "block_size": 8, "word_bitsize": 4, "nbr_words": 2, "nbr_rounds": 2,
        "round_structure": [
            {"layer_type": "rotation", "params": {"direction": "l", "amount": amount, "word_index": 0}}
        ],
    }


def test_real_validate_gate_broken_then_repaired():
    # amount=9 >= word_bitsize 4 -> validate flags it; repair resets it to a legal amount.
    def build_action(ctx):
        return ActionResult(ok=True, data=ctx["spec"])

    def repair(ctx, problems, attempt):
        ctx["spec"]["round_structure"][0]["params"]["amount"] = 1
        return True

    step = Step("draft", action=build_action, gate=spec_validate_gate, repair=repair)
    report = AgentController(max_attempts=3).run("build tiny cipher", [step],
                                                ctx={"spec": _tiny_spec(9)})
    assert report.ok and report.outcomes[0].attempts == 2


def test_real_validate_gate_passes_clean_spec_first_try():
    step = Step("draft", action=lambda ctx: ActionResult(ok=True, data=ctx["spec"]),
                gate=spec_validate_gate)
    report = AgentController().run("g", [step], ctx={"spec": _tiny_spec(1)})
    assert report.ok and report.outcomes[0].attempts == 1


# --- KAT gates on a real built cipher ---------------------------------------

def _identity_perm_spec(expected):
    # a 1-round identity permutation (output == input); `expected` lets us make the vector wrong
    return {
        "name": "IdentPerm", "cipher_type": "permutation",
        "block_size": 8, "word_bitsize": 4, "nbr_words": 2, "nbr_rounds": 1,
        "round_structure": [{"layer_type": "permutation", "params": {"table": [0, 1]}}],
        "test_vectors": [[[1, 2], expected]],
    }


def test_definition_verdict_gate_reads_kat_verdict():
    from agent.controller import definition_verdict_gate
    passed = ActionResult(ok=True, data={"verification": {"tested": True, "all_passed": True}})
    failed = ActionResult(ok=True, data={"verification": {"tested": True, "all_passed": False,
                                                          "passed": 0, "total": 1}})
    none = ActionResult(ok=True, data={"verification": {"tested": False}})
    assert definition_verdict_gate({}, passed) == []
    assert definition_verdict_gate({}, none) == []
    assert "0/1" in definition_verdict_gate({}, failed)[0]


def test_cipher_kat_gate_on_real_cipher():
    from agent.controller import cipher_kat_gate
    from agent.skills.cipher_definition import build_permutation_from_spec
    from agent.skills.cipher_spec import CipherSpec
    good = CipherSpec.from_dict(_identity_perm_spec([1, 2]))
    cipher = build_permutation_from_spec(good)
    assert cipher_kat_gate({"spec": good}, ActionResult(ok=True, data=cipher)) == []
    bad = CipherSpec.from_dict(_identity_perm_spec([3, 4]))
    bad_cipher = build_permutation_from_spec(bad)
    assert cipher_kat_gate({"spec": bad}, ActionResult(ok=True, data=bad_cipher))  # non-empty


# --- the first real end-to-end goal via OCPAgent.build_and_verify_cipher -----

def test_build_and_verify_cipher_passes_correct_cipher():
    from agent.interfaces.api import OCPAgent
    agent = OCPAgent()                                             # no LLM
    report = agent.build_and_verify_cipher(_identity_perm_spec([1, 2]))
    assert report.ok and report.outcomes[0].status == "passed"
    assert report.outcomes[0].attempts == 1
    assert agent.session.get_cipher() is not None


def test_build_and_verify_cipher_fails_kat_without_llm():
    from agent.interfaces.api import OCPAgent
    agent = OCPAgent()                                             # no LLM -> no repair
    report = agent.build_and_verify_cipher(_identity_perm_spec([9, 9]))
    assert report.status == "failed"
    assert report.outcomes[0].attempts == 1                       # no repair, no retry
    assert "test vectors pass" in report.outcomes[0].error


def test_build_and_verify_cipher_repairs_then_passes(monkeypatch):
    from agent.interfaces.api import OCPAgent
    agent = OCPAgent()
    agent._core.llm = object()                                    # non-None so repair is attempted

    # simulate an LLM repair that corrects the wrong expected vector to the right one
    def fake_repair(spec, problems):
        fixed = dict(spec)
        fixed["test_vectors"] = [[[1, 2], [1, 2]]]
        return fixed

    monkeypatch.setattr(agent, "repair_cipher_spec", fake_repair)
    report = agent.build_and_verify_cipher(_identity_perm_spec([9, 9]), max_attempts=3)
    assert report.ok and report.outcomes[0].attempts == 2
