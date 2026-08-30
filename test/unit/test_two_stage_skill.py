import attacks.attacks as attacks
from agent.session import Session
from agent.skills.two_stage_analysis import TwoStageTrailSearchSkill
from agent.types import SkillName, SkillRequest


def _run(params):
    return TwoStageTrailSearchSkill().execute(SkillRequest(SkillName.TWO_STAGE_TRAIL_SEARCH, params), Session())


def test_two_stage_rejects_invalid_goal():
    result = _run({"cipher_name": "aes", "rounds": 3, "goal": "NOPE"})
    assert not result.success and "Invalid goal" in result.error


def test_two_stage_rejects_invalid_rounds():
    result = _run({"cipher_name": "aes", "rounds": 0})
    assert not result.success and "Invalid rounds" in result.error


def test_two_stage_rejects_unknown_cipher():
    result = _run({"cipher_name": "not_a_cipher", "rounds": 3})
    assert not result.success and "Unknown cipher" in result.error


def test_two_stage_reports_found_result(monkeypatch):
    captured = {}

    def fake_two_stage(cipher_factory, r, goal, **kwargs):
        captured.update(r=r, goal=goal, factory_callable=callable(cipher_factory))
        return (3, 7)

    monkeypatch.setattr(attacks, "two_stage_trail_search", fake_two_stage)

    result = _run({"cipher_name": "aes", "cipher_type": "blockcipher", "rounds": 4, "goal": "DIFFERENTIALPATH_PROB"})

    assert result.success
    assert result.data == {"goal": "DIFFERENTIALPATH_PROB", "rounds": 4, "found": True,
                           "min_active_sboxes": 3, "best_weight": 7}
    assert "min active S-boxes = 3, best weight = 7" in result.summary
    assert captured == {"r": 4, "goal": "DIFFERENTIALPATH_PROB", "factory_callable": True}


def test_two_stage_reports_no_trail_found(monkeypatch):
    monkeypatch.setattr(attacks, "two_stage_trail_search", lambda *a, **k: None)

    result = _run({"cipher_name": "aes", "rounds": 3})

    assert result.success
    assert result.data["found"] is False
    assert "no truncated trail found" in result.summary
