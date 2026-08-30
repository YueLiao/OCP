from types import SimpleNamespace

import pytest

import attacks.attacks as attacks
from agent.session import Session
from agent.skills.impossible_differential_analysis import ImpossibleDifferentialAnalysisSkill
from agent.skills.zero_correlation_analysis import ZeroCorrelationAnalysisSkill
from agent.types import SkillName, SkillRequest


def _session_with_cipher():
    session = Session()
    session.set_cipher(SimpleNamespace(name="Tiny", test_vectors=[]))
    return session


# (skill class, SkillName, attacks attribute mocked, fixed goal)
CASES = [
    (ImpossibleDifferentialAnalysisSkill, SkillName.IMPOSSIBLE_DIFFERENTIAL_ANALYSIS,
     "impossible_differential_attacks", "IMPOSSIBLETRUNCATEDDIFF"),
    (ZeroCorrelationAnalysisSkill, SkillName.ZERO_CORRELATION_ANALYSIS,
     "zero_correlation_attacks", "ZEROCORRELATIONTRUNCATEDLINEAR"),
]


@pytest.mark.parametrize("skill_cls,skill_name,_attr,_goal", CASES)
def test_requires_a_loaded_cipher(skill_cls, skill_name, _attr, _goal):
    result = skill_cls().execute(SkillRequest(skill_name, {}), Session())
    assert not result.success
    assert "No cipher loaded" in result.error


@pytest.mark.parametrize("skill_cls,skill_name,_attr,_goal", CASES)
def test_rejects_invalid_model_type(skill_cls, skill_name, _attr, _goal):
    result = skill_cls().execute(SkillRequest(skill_name, {"model_type": "cp"}), _session_with_cipher())
    assert not result.success
    assert "Invalid model_type" in result.error


@pytest.mark.parametrize("skill_cls,skill_name,attr,goal", CASES)
def test_forwards_the_distinguisher_search(monkeypatch, skill_cls, skill_name, attr, goal):
    captured = {}

    def fake_attack(cipher, goal, config_model, config_solver, show_mode):
        captured.update(goal=goal, model_type=config_model.get("model_type"), show_mode=show_mode)
        return [((0,), (1,)), ((2,), (3,))]

    monkeypatch.setattr(attacks, attr, fake_attack)

    result = skill_cls().execute(SkillRequest(skill_name, {"model_type": "sat", "show_mode": 2}), _session_with_cipher())

    assert result.success
    assert result.data["distinguisher_count"] == 2
    assert result.data["goal"] == goal
    assert captured == {"goal": goal, "model_type": "sat", "show_mode": 2}
