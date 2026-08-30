import pytest

import variables.variables as var
from attacks import attacks
from attacks import zero_corr_linear as zc


# ---------- goal validation (checked before touching the cipher, so no solver needed) ----------
def test_zero_corr_search_rejects_unknown_goal():
    with pytest.raises(ValueError, match="Invalid goal"):
        zc.search_zc_distinguisher_enumeration(None, goal="NOPE")


# ---------- _gen_fixed_activity_constraints (pure constraint building) ----------
def test_fixed_activity_constraints_word_level_milp():
    vs = [var.Variable(1, ID="a"), var.Variable(1, ID="b"), var.Variable(1, ID="c")]
    cons = zc._gen_fixed_activity_constraints(vs, active_positions=[0, 2], model_type="milp", bitwise=False)
    assert cons == ["a = 1", "b = 0", "c = 1"]


def test_fixed_activity_constraints_word_level_sat():
    vs = [var.Variable(1, ID="a"), var.Variable(1, ID="b")]
    cons = zc._gen_fixed_activity_constraints(vs, active_positions=[1], model_type="sat", bitwise=False)
    assert cons == ["-a", "b"]  # inactive -> -a, active -> b


def test_fixed_activity_constraints_bit_level():
    vs = [var.Variable(2, ID="a")]  # -> ids a_0, a_1
    cons = zc._gen_fixed_activity_constraints(vs, active_positions=[1], model_type="milp", bitwise=True)
    assert cons == ["a_0 = 0", "a_1 = 1"]


# ---------- _parse_and_set_configs (defaults + filename), via a real cipher ----------
def test_parse_and_set_configs_defaults_and_filename():
    from primitives.speck import SPECK_PERMUTATION

    cipher = SPECK_PERMUTATION(r=3)
    goal = "ZEROCORRELATIONTRUNCATEDLINEAR"
    cm, cs = zc._parse_and_set_configs(cipher, goal, {}, {})
    assert cm["model_type"] == "milp"  # default backend
    assert cs["solver"] == "DEFAULT"
    assert {"functions", "rounds", "layers", "positions"} <= set(cm)  # scope filled
    assert goal in cm["filename"] and cm["filename"].endswith("milp_model.lp")
    # sat backend swaps the filename suffix
    cm_sat, _ = zc._parse_and_set_configs(cipher, goal, {"model_type": "sat"}, {})
    assert cm_sat["filename"].endswith("sat_model.cnf")


# ---------- facade delegation (attacks.py wiring) ----------
def test_zero_correlation_attacks_delegates(monkeypatch):
    captured = {}

    def fake(cipher, goal, config_model, config_solver, show_mode):
        captured.update(cipher=cipher, goal=goal)
        return [((2,), (3,))]

    monkeypatch.setattr(zc, "search_zc_distinguisher_enumeration", fake)
    out = attacks.zero_correlation_attacks("C")
    assert out == [((2,), (3,))]
    assert captured == {"cipher": "C", "goal": "ZEROCORRELATIONTRUNCATEDLINEAR"}
