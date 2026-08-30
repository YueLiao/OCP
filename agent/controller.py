"""Agentic orchestration harness: a bounded plan -> act -> verify -> repair -> decide loop.

`AgentController` runs an ordered `plan` of `Step`s toward a goal. Each step ACTS (does the
work), then a GATE verifies the result against an OBJECTIVE signal - a build KAT, a spec
validation, a solver status - NOT the model's own say-so. On a gate failure the step's
REPAIR is invoked and the step retried, up to a per-step attempt budget; the loop stops
early on no-progress (repair changed nothing), a required-step failure, or a cancellation
signal.

This generalizes the cipher-draft self-repair loop (OCPAgent._auto_repair_draft, which is
KAT-driven but scoped to drafting and buried in the facade) into a reusable engine. The
engine itself is domain-agnostic and LLM-free: steps are plain callables, so the loop
mechanics are hermetically testable and later phases plug in build / analysis / report
steps without touching this file.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ActionResult:
    """What a step's `action` returns: did the work run, and what did it produce.

    `ok=False` means the action itself could not run (an exception, a missing input); the
    gate is skipped and `error` becomes the step's problem. `ok=True` hands off to the gate,
    which decides correctness against an objective signal.
    """
    ok: bool
    data: Any = None
    summary: str = ""
    error: Optional[str] = None


@dataclass
class StepOutcome:
    """The result of running one step (across all its attempts)."""
    name: str
    status: str                      # "passed" | "failed" | "skipped" | "cancelled"
    attempts: int = 0
    problems: List[str] = field(default_factory=list)
    summary: str = ""
    data: Any = None
    error: Optional[str] = None


@dataclass
class RunReport:
    """The result of running a whole plan toward a goal."""
    goal: str
    outcomes: List[StepOutcome] = field(default_factory=list)
    status: str = "success"          # "success" | "failed" | "cancelled"
    summary: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "success"

    @property
    def failed_step(self) -> Optional[StepOutcome]:
        for o in self.outcomes:
            if o.status in ("failed", "cancelled"):
                return o
        return None


# Type aliases for the step callables (documentation only; not enforced at runtime).
# action(ctx) -> ActionResult
# gate(ctx, action_result) -> List[str]  (empty = passed)
# repair(ctx, problems, attempt) -> bool (True = changed something worth retrying)
ActionFn = Callable[[Dict[str, Any]], ActionResult]
GateFn = Callable[[Dict[str, Any], ActionResult], List[str]]
RepairFn = Callable[[Dict[str, Any], List[str], int], bool]


@dataclass
class Step:
    """One unit of work in a plan.

    action:  does the work, reading/writing the shared `ctx` dict, returns an ActionResult.
    gate:    verifies the action's result against an objective signal, returns a list of
             problems (empty = passed). None = the action's own `ok` is the verdict.
    repair:  attempts to fix `ctx` after a gate failure; returns True if it changed
             something (so a retry is worthwhile) or False to stop retrying this step.
             None = no repair (the step fails on the first gate failure).
    required: when True, a failed step stops the run; when False, it is skipped and the run
             continues (a best-effort step).
    max_attempts: per-step override of the controller's default attempt budget.
    """
    name: str
    action: ActionFn
    gate: Optional[GateFn] = None
    repair: Optional[RepairFn] = None
    required: bool = True
    max_attempts: Optional[int] = None


class AgentController:
    """Runs a plan with per-step verify + repair, a budget, cancellation, and tracing."""

    def __init__(
        self,
        *,
        session=None,
        is_cancelled: Optional[Callable[[], bool]] = None,
        max_attempts: int = 3,
    ):
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.session = session
        self._is_cancelled = is_cancelled or (lambda: False)
        self.max_attempts = max_attempts

    def _trace(self, event: str, payload: Optional[Dict[str, Any]] = None):
        if self.session is not None:
            self.session.add_trace(event, payload or {})

    def run(self, goal: str, plan: List[Step], ctx: Optional[Dict[str, Any]] = None) -> RunReport:
        """Execute `plan` toward `goal`, returning a structured RunReport.

        The shared `ctx` dict threads state between steps (e.g. a step stores ctx["cipher"]
        that a later step reads). It is created empty if not supplied and is mutated in place.
        """
        ctx = ctx if ctx is not None else {}
        outcomes: List[StepOutcome] = []
        status = "success"
        self._trace("controller_run_start", {"goal": goal, "steps": [s.name for s in plan]})

        for step in plan:
            if self._is_cancelled():
                outcomes.append(StepOutcome(step.name, "cancelled", error="cancelled before start"))
                status = "cancelled"
                break

            outcome = self._run_step(step, ctx)
            outcomes.append(outcome)

            if outcome.status == "cancelled":
                status = "cancelled"
                break
            if outcome.status == "failed":       # only required steps yield "failed"
                status = "failed"
                break

        report = RunReport(goal=goal, outcomes=outcomes, status=status,
                           summary=self._summarize(goal, outcomes, status))
        self._trace("controller_run_finish",
                    {"goal": goal, "status": status,
                     "outcomes": [{"step": o.name, "status": o.status, "attempts": o.attempts}
                                  for o in outcomes]})
        return report

    def _run_step(self, step: Step, ctx: Dict[str, Any]) -> StepOutcome:
        budget = step.max_attempts or self.max_attempts
        last_problems: List[str] = []
        attempts = 0

        for attempt in range(1, budget + 1):
            if self._is_cancelled():
                return StepOutcome(step.name, "cancelled", attempts, last_problems,
                                   error="cancelled mid-step")
            attempts = attempt

            action = self._act(step, ctx)
            if action.ok:
                problems = self._gate(step, ctx, action)
            else:
                problems = [action.error or f"{step.name}: action failed"]

            self._trace("controller_step_attempt",
                        {"step": step.name, "attempt": attempt, "ok": action.ok,
                         "problems": problems})

            if not problems:
                return StepOutcome(step.name, "passed", attempt, [], action.summary, action.data)

            last_problems = problems

            # No point repairing if this was the last allowed attempt or there is no repair.
            if step.repair is None or attempt >= budget:
                break
            try:
                changed = step.repair(ctx, list(problems), attempt)
            except Exception as exc:                # a repair that blows up is a stop, not a crash
                self._trace("controller_repair_error", {"step": step.name, "error": str(exc)})
                last_problems = problems + [f"repair raised: {exc}"]
                break
            if not changed:                          # no-progress: stop retrying this step
                self._trace("controller_repair_no_progress", {"step": step.name, "attempt": attempt})
                break

        final_status = "failed" if step.required else "skipped"
        return StepOutcome(step.name, final_status, attempts, last_problems,
                           error="; ".join(last_problems) if last_problems else None)

    @staticmethod
    def _act(step: Step, ctx: Dict[str, Any]) -> ActionResult:
        try:
            result = step.action(ctx)
        except Exception as exc:                     # an action that raises is a failed action, not a crash
            return ActionResult(ok=False, error=f"{step.name}: action raised: {exc}")
        if not isinstance(result, ActionResult):
            return ActionResult(ok=False,
                                error=f"{step.name}: action returned {type(result).__name__}, expected ActionResult")
        return result

    @staticmethod
    def _gate(step: Step, ctx: Dict[str, Any], action: ActionResult) -> List[str]:
        if step.gate is None:
            return []
        try:
            problems = step.gate(ctx, action)
        except Exception as exc:                     # a gate that raises is a failed gate, not a crash
            return [f"{step.name}: gate raised: {exc}"]
        return list(problems or [])

    @staticmethod
    def _summarize(goal: str, outcomes: List[StepOutcome], status: str) -> str:
        parts = []
        for o in outcomes:
            tag = {"passed": "ok", "failed": "FAILED", "skipped": "skipped",
                   "cancelled": "cancelled"}.get(o.status, o.status)
            note = f" ({o.attempts} attempts)" if o.attempts > 1 else ""
            parts.append(f"{o.name}: {tag}{note}")
        head = {"success": "completed", "failed": "failed", "cancelled": "cancelled"}.get(status, status)
        return f"Goal '{goal}' {head}. Steps: " + "; ".join(parts) if parts else f"Goal '{goal}' {head}."


# --- objective gate helpers (crypto-domain; imported lazily so the engine core stays light) ---

def spec_validate_gate(ctx: Dict[str, Any], action: ActionResult) -> List[str]:
    """Gate: the spec in ctx['spec'] (or action.data) must pass CipherSpec.validate()."""
    from agent.skills.cipher_spec import CipherSpec
    spec_data = ctx.get("spec") if action.data is None else action.data
    if spec_data is None:
        return ["no spec available to validate"]
    spec = spec_data if isinstance(spec_data, CipherSpec) else CipherSpec.from_dict(spec_data)
    return list(spec.validate())


def _kat_problem(verification: Dict[str, Any]) -> List[str]:
    """Turn a verify_cipher_test_vectors result dict into gate problems ([] = passed)."""
    if not verification.get("tested"):
        return []                                    # no vectors -> no objective signal to fail on
    if verification.get("all_passed"):
        return []
    passed, total = verification.get("passed", 0), verification.get("total", 0)
    return [f"only {passed}/{total} test vectors pass; check layer order, key additions, "
            f"constants, and round count"]


def cipher_kat_gate(ctx: Dict[str, Any], action: ActionResult) -> List[str]:
    """Gate: the built cipher (action.data or ctx['cipher']) must reproduce its test vectors.

    Rebuilds an implementation and runs the spec's vectors. Coerces a spec dict to CipherSpec
    and normalizes its vectors first, so a raw spec still verifies. Returns [] when all vectors
    pass or when there are none (no objective signal to fail on).
    """
    from agent.skills.cipher_definition import verify_cipher_test_vectors, _normalize_test_vectors
    from agent.skills.cipher_definition import _effective_word_sizes
    from agent.skills.cipher_spec import CipherSpec
    cipher = action.data if action.data is not None else ctx.get("cipher")
    spec = ctx.get("spec")
    if cipher is None or spec is None:
        return ["no built cipher / spec available for KAT"]
    if not isinstance(spec, CipherSpec):
        spec = CipherSpec.from_dict(spec)
    try:
        wb, kwb = _effective_word_sizes(spec)
        spec.test_vectors = _normalize_test_vectors(spec.test_vectors, spec.cipher_type, wb, kwb)
    except Exception:
        pass                                         # if normalization fails, verify reports the mismatch
    return _kat_problem(verify_cipher_test_vectors(cipher, spec))


def definition_verdict_gate(ctx: Dict[str, Any], action: ActionResult) -> List[str]:
    """Gate for a CIPHER_DEFINITION skill result: read the KAT verdict it already computed.

    The definition skill builds, normalizes vectors, and runs the KAT itself, storing the
    outcome in result.data['verification']. This gate reads that objective verdict instead of
    re-building and re-running the vectors.
    """
    verification = (action.data or {}).get("verification") or {}
    return _kat_problem(verification)


def analysis_verdict_gate(ctx: Dict[str, Any], action: ActionResult) -> List[str]:
    """Gate for an analysis (differential / linear / integral / impossible / zero-corr / two-stage).

    An analysis is unlike a build: reaching a VERDICT is the objective signal, and BOTH outcomes
    are valid - a distinguisher was found, OR none exists up to these rounds (an UNSAT / 0-result
    answer is a real finding, not a failure). So a run that reached a verdict passes. (A run that
    ERRORED - solver missing, model build failed - never reaches this gate: the step's action
    returns ok=False, so the engine turns the error into the step's problem and triggers repair.)
    The only thing rejected is a self-inconsistent verdict: a positive result count whose list is
    missing or holds empty/None entries - a modeling bug, not a real distinguisher.

    The six analysis skills use two field conventions: differential/linear emit trail_count/trails;
    integral/impossible/zero-correlation emit distinguisher_count/distinguishers; two-stage emits
    neither (found/min_active_sboxes/best_weight), so any verdict it reaches passes.
    """
    data = action.data or {}
    count = data.get("trail_count")
    if count is None:
        count = data.get("distinguisher_count")
    items = data.get("trails")
    if items is None:
        items = data.get("distinguishers")
    if not count:                                    # 0 / None -> "no distinguisher", or no count field
        return []
    if not isinstance(items, list):
        return [f"analysis reports {count} result(s) but the list is missing "
                f"({type(items).__name__}) - a modeling/reporting bug"]
    if any(t is None or (hasattr(t, "__len__") and len(t) == 0) for t in items):
        return [f"analysis reports {count} result(s) but some are empty/None - a degenerate "
                f"distinguisher, check the model"]
    return []


def _available_backends() -> Dict[str, bool]:
    """{'milp': bool, 'sat': bool} - whether any installed backend can run that model type."""
    from solving.solving import solver_capabilities
    caps = solver_capabilities()
    return {mt: any(b.get("available") for b in caps.get(mt, {}).values())
            for mt in ("milp", "sat")}


def _swap_to_available_backend(store: Dict[str, Any], tried_key: str = "_tried_backends") -> bool:
    """Swap store['model_type'] to an installed, untried alternate backend (milp<->sat).

    Shared by the ctx-based single-step repair and the params-based pipeline repair. Records
    tried backends in store[tried_key] (an internal key, kept out of skill params). Returns
    True if it swapped, False when there is no untried, available alternate.
    """
    available = _available_backends()
    tried = store.setdefault(tried_key, set())
    tried.add(store.get("model_type", "milp"))
    for alt in ("milp", "sat"):
        if alt not in tried and available.get(alt):
            store["model_type"] = alt
            return True
    return False


def make_backend_fallback_repair(*, tried_key: str = "_tried_backends") -> RepairFn:
    """A repair that re-plans an errored analysis onto another AVAILABLE solver backend.

    On failure it swaps ctx['model_type'] to an alternate (milp<->sat) that is installed and
    not yet tried - the common "no MILP solver here, fall back to SAT" case. Returns False
    (no-progress) when there is no untried, available alternate, so the loop stops instead of
    spinning.
    """
    def repair(ctx: Dict[str, Any], problems: List[str], attempt: int) -> bool:
        return _swap_to_available_backend(ctx, tried_key)
    return repair


# --- skill -> gate/repair registry + composing a plan from SkillRequests -----

# Analysis skills whose result is judged by "did it reach a verdict" (analysis_verdict_gate).
def _analysis_skill_names():
    from agent.types import SkillName
    return {
        SkillName.DIFFERENTIAL_ANALYSIS, SkillName.LINEAR_ANALYSIS,
        SkillName.INTEGRAL_ANALYSIS, SkillName.IMPOSSIBLE_DIFFERENTIAL_ANALYSIS,
        SkillName.ZERO_CORRELATION_ANALYSIS, SkillName.TWO_STAGE_TRAIL_SEARCH,
    }


# Analysis skills that accept a model_type and support BOTH milp and sat, so an errored run can
# fall back to the other backend. (INTEGRAL is milp-only; TWO_STAGE takes no model_type.)
def _backend_swappable_skill_names():
    from agent.types import SkillName
    return {
        SkillName.DIFFERENTIAL_ANALYSIS, SkillName.LINEAR_ANALYSIS,
        SkillName.IMPOSSIBLE_DIFFERENTIAL_ANALYSIS, SkillName.ZERO_CORRELATION_ANALYSIS,
    }


def default_gate_for(skill) -> Optional[GateFn]:
    """The objective gate for a skill: KAT verdict for a build, verdict for an analysis, else none."""
    from agent.types import SkillName
    if skill == SkillName.CIPHER_DEFINITION:
        return definition_verdict_gate
    if skill in _analysis_skill_names():
        return analysis_verdict_gate
    return None


def default_repair_for(skill, params: Dict[str, Any]) -> Optional[RepairFn]:
    """The repair for a skill step, bound to that step's mutable `params`.

    Backend-swappable analysis skills get a solver-backend fallback that mutates params
    ['model_type']; everything else has no automatic repair (fails on its first gate failure).
    """
    if skill in _backend_swappable_skill_names():
        def repair(ctx: Dict[str, Any], problems: List[str], attempt: int) -> bool:
            return _swap_to_available_backend(params)
        return repair
    return None


def _make_definition_repair(params, repair_spec):
    """Repair a CIPHER_DEFINITION step: ask `repair_spec(spec, problems)` for a corrected spec
    (an LLM re-draft) and swap it into params for the next attempt. Returns False (no-progress)
    if the repair raises, returns nothing, or does not change the spec.
    """
    def repair(ctx, problems, attempt):
        try:
            fixed = repair_spec(params.get("spec"), list(problems))
        except Exception:
            return False
        if not isinstance(fixed, dict) or fixed == params.get("spec"):
            return False
        params["spec"] = fixed
        return True
    return repair


def plan_from_requests(requests, *, execute, repair_spec=None,
                       gate_for=default_gate_for, repair_for=default_repair_for):
    """Compose a list of SkillRequests into a verified controller plan.

    Each request becomes a Step: its action runs the skill via `execute` (a callable taking a
    SkillRequest and returning a SkillResult), its gate/repair come from the registry. Per-step
    params are copied into a mutable dict so a repair (e.g. backend fallback, or a spec re-draft)
    can adjust them between attempts; internal keys (leading '_', e.g. the tried-backends set) are
    stripped from what the skill actually receives. Cross-step state flows through the session, not
    ctx - e.g. a cipher a definition step builds is read from the session by a later analysis step.

    `repair_spec(spec, problems) -> fixed_spec`, when given, adds KAT self-repair to a build step
    (a CIPHER_DEFINITION whose test vectors fail is re-drafted and rebuilt), so a pipeline / chat
    build gets the same auto-repair as OCPAgent.build_and_verify_cipher.

    Analysis steps are best-effort (required=False): a failed independent analysis is reported
    (skipped) but does NOT halt the rest, matching the sequential path. Build / instantiate steps
    stay required because later steps depend on the cipher they put on the session.
    """
    from agent.types import SkillRequest, SkillName
    analysis = _analysis_skill_names()
    steps = []
    seen = {}
    for req in requests:
        skill = req.skill
        params = dict(req.params or {})
        name = skill.value
        seen[name] = seen.get(name, 0) + 1
        if seen[name] > 1:
            name = f"{name}#{seen[name]}"

        def make_action(skill=skill, params=params):
            def action(ctx):
                clean = {k: v for k, v in params.items() if not k.startswith("_")}
                result = execute(SkillRequest(skill=skill, params=clean))
                return ActionResult(ok=bool(result.success), data=result.data,
                                    summary=result.summary, error=result.error)
            return action

        repair = repair_for(skill, params)
        if repair is None and repair_spec is not None and skill == SkillName.CIPHER_DEFINITION:
            repair = _make_definition_repair(params, repair_spec)

        steps.append(Step(name, action=make_action(), gate=gate_for(skill),
                          repair=repair, required=(skill not in analysis)))
    return steps
