from types import SimpleNamespace

import attacks.attacks as attacks
from agent.session import Session
from agent.skills.integral_analysis import IntegralAnalysisSkill
from agent.types import SkillName, SkillRequest


def _session_with_cipher():
    session = Session()
    session.set_cipher(SimpleNamespace(name="Tiny", test_vectors=[]))
    return session


def test_integral_analysis_requires_a_loaded_cipher():
    result = IntegralAnalysisSkill().execute(
        SkillRequest(SkillName.INTEGRAL_ANALYSIS, {"constant_bits": [0]}), Session()
    )
    assert not result.success
    assert "No cipher loaded" in result.error


def test_integral_analysis_rejects_missing_or_invalid_constant_bits():
    skill = IntegralAnalysisSkill()
    for params in ({}, {"constant_bits": []}, {"constant_bits": [0, "x"]}):
        result = skill.execute(SkillRequest(SkillName.INTEGRAL_ANALYSIS, params), _session_with_cipher())
        assert not result.success
        assert "constant_bits" in result.error


def test_integral_analysis_forwards_the_two_subset_request(monkeypatch):
    captured = {}

    def fake_integral_attacks(cipher, goal, constraints, objective_target, show_mode, config_model, config_solver):
        captured.update(
            goal=goal,
            constraints=constraints,
            objective_target=objective_target,
            model_type=config_model.get("model_type"),
            constant_bits=config_model.get("constant_bits"),
        )
        return [SimpleNamespace(json_filename="d.json", txt_filename="d.txt")]

    monkeypatch.setattr(attacks, "integral_attacks", fake_integral_attacks)

    result = IntegralAnalysisSkill().execute(
        SkillRequest(SkillName.INTEGRAL_ANALYSIS, {"constant_bits": [0, 1]}), _session_with_cipher()
    )

    assert result.success
    assert result.data["distinguisher_count"] == 1
    assert "found 1 distinguisher(s)" in result.summary
    assert result.data["artifact_links"][0]["label"] == "trail_json_1"
    # the skill fixes goal/objective/backend and routes constant_bits through config_model
    assert captured == {
        "goal": "INTEGRAL_TWOSUBSET",
        "constraints": ["TWO_SUBSET_INIT"],
        "objective_target": "EXISTENCE",
        "model_type": "milp",
        "constant_bits": [0, 1],
    }
