from types import SimpleNamespace

import pytest

from attacks import attacks


# ------------------------------- integral_attacks delegation -------------------------------
def test_integral_attacks_delegates(monkeypatch):
    captured = {}

    def fake(cipher, goal, constraints, objective_target, show_mode, config_model, config_solver):
        captured.update(cipher=cipher, goal=goal, objective_target=objective_target)
        return ["DIST"]

    monkeypatch.setattr(attacks.integral, "search_integral_distinguisher", fake)
    out = attacks.integral_attacks("C", goal="INTEGRAL_TWOSUBSET")
    assert out == ["DIST"]
    assert captured == {"cipher": "C", "goal": "INTEGRAL_TWOSUBSET", "objective_target": "EXISTENCE"}


# ------------------------------- two_stage_trail_search -------------------------------
def test_two_stage_trail_search_rejects_unsupported_goal():
    with pytest.raises(ValueError, match="Unsupported goal"):
        attacks.two_stage_trail_search(lambda r: object(), 3, goal="NOPE")


def test_two_stage_returns_none_when_no_truncated_trail(monkeypatch):
    monkeypatch.setattr(attacks, "diff_attacks", lambda *a, **k: [])
    assert attacks.two_stage_trail_search(lambda r: object(), 3, goal="DIFFERENTIALPATH_PROB") is None


def test_two_stage_returns_min_active_and_best_weight(monkeypatch):
    stage1_trail = SimpleNamespace(data={"diff_weight": 3}, solution_trace={})
    stage2_trail = SimpleNamespace(data={"diff_weight": 7}, solution_trace={})
    goals_seen = []

    def fake_diff(cipher, goal, **kwargs):
        goals_seen.append(goal)
        return [stage1_trail] if goal == "TRUNCATEDDIFF_SBOXCOUNT" else [stage2_trail]

    monkeypatch.setattr(attacks, "diff_attacks", fake_diff)
    # a cipher whose (empty) var layer makes stage-2 activity fixing a no-op
    cipher = SimpleNamespace(functions={"P": SimpleNamespace(nbr_rounds=1, nbr_layers=0, vars={1: {0: []}})})

    result = attacks.two_stage_trail_search(lambda r: cipher, 3, goal="DIFFERENTIALPATH_PROB")

    assert result == (3, 7)  # (stage-1 min active S-boxes, stage-2 best weight)
    assert goals_seen == ["TRUNCATEDDIFF_SBOXCOUNT", "DIFFERENTIALPATH_PROB"]


def test_two_stage_dispatches_to_linear_for_linear_goal(monkeypatch):
    goals_seen = []

    def fake_linear(cipher, goal, **kwargs):
        goals_seen.append(goal)
        return []  # no stage-1 trail -> stops after dispatch

    monkeypatch.setattr(attacks, "linear_attacks", fake_linear)
    attacks.two_stage_trail_search(lambda r: object(), 3, goal="LINEARPATH_CORR")
    assert goals_seen == ["TRUNCATEDLINEAR_SBOXCOUNT"]  # linear (not differential) path used
