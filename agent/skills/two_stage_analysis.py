from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.analysis_common import run_analysis_attack
from agent.skills.base import BaseSkill
from agent.skills.cipher_instantiation import resolve_cipher_factory

VALID_GOALS = ["DIFFERENTIALPATH_PROB", "LINEARPATH_CORR"]


class TwoStageTrailSearchSkill(BaseSkill):
    """Two-stage (truncated -> bit-level) optimal trail search for word-oriented ciphers.

    Stage 1 finds the minimum-active-S-box truncated pattern; stage 2 fixes it and searches
    the best bit-level trail on it. Because each stage needs a FRESH cipher, this skill takes
    cipher_name/type/version/rounds (rebuilt via the cipher catalog) instead of the loaded
    cipher. Wraps attacks.two_stage_trail_search.
    """

    @property
    def name(self) -> SkillName:
        return SkillName.TWO_STAGE_TRAIL_SEARCH

    @property
    def description(self) -> str:
        return (
            "Two-stage (truncated then bit-level) optimal differential/linear trail search for "
            "word-oriented ciphers (e.g. AES, SKINNY). Rebuilds the named cipher per stage, so it "
            "takes cipher_name/type/version/rounds. Goals: " + ", ".join(VALID_GOALS) + "."
        )

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "cipher_name": {"type": "string", "required": True, "description": "Cipher name (e.g. 'aes', 'skinny')."},
            "cipher_type": {
                "type": "string",
                "required": False,
                "default": "blockcipher",
                "description": "'permutation', 'blockcipher', or 'keypermutation'.",
            },
            "version": {"type": "any", "required": False, "description": "Version (int or list, cipher-dependent)."},
            "rounds": {"type": "int", "required": True, "description": "Number of rounds."},
            "goal": {
                "type": "string",
                "required": False,
                "default": "DIFFERENTIALPATH_PROB",
                "description": "Analysis goal.",
                "enum": VALID_GOALS,
            },
        }

    def execute(self, request: SkillRequest, session: Session) -> SkillResult:
        import attacks.attacks as attacks

        params = request.params
        goal = params.get("goal", "DIFFERENTIALPATH_PROB")
        if goal not in VALID_GOALS:
            return SkillResult(success=False, skill=self.name, error=f"Invalid goal: '{goal}'. Valid: {VALID_GOALS}")

        rounds = params.get("rounds")
        if not isinstance(rounds, int) or rounds <= 0:
            return SkillResult(success=False, skill=self.name, error="Invalid rounds: provide a positive integer.")

        factory, error = resolve_cipher_factory(
            params.get("cipher_name"), params.get("cipher_type", "blockcipher"), params.get("version")
        )
        if error:
            return SkillResult(success=False, skill=self.name, error=error)

        result, failure = run_analysis_attack(
            skill_name=self.name,
            expected_error_prefix="Two-stage trail search failed",
            unexpected_error_prefix="Unexpected two-stage trail search failure",
            attack_fn=attacks.two_stage_trail_search,
            cipher_factory=factory,
            r=rounds,
            goal=goal,
        )
        if failure:
            return failure

        if result is None:
            return SkillResult(
                success=True,
                skill=self.name,
                data={"goal": goal, "rounds": rounds, "found": False},
                summary=f"Two-stage trail search ({goal}, {rounds} rounds): no truncated trail found.",
            )

        min_active, best_weight = result
        return SkillResult(
            success=True,
            skill=self.name,
            data={
                "goal": goal,
                "rounds": rounds,
                "found": True,
                "min_active_sboxes": min_active,
                "best_weight": best_weight,
            },
            summary=(
                f"Two-stage trail search ({goal}, {rounds} rounds): "
                f"min active S-boxes = {min_active}, best weight = {best_weight}."
            ),
        )
