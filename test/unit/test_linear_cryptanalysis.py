from types import SimpleNamespace

import pytest

from attacks import attack_trace
from attacks import linear_cryptanalysis as linear


def _toy_cipher():
    return SimpleNamespace(
        name="toy",
        nbr_rounds=1,
        functions={"PERMUTATION": SimpleNamespace(nbr_rounds=1, nbr_layers=0, constraints={1: {0: []}})},
    )


# ---------- frontend request validation (all six branches, symmetric with differential) ----------
_LINEAR_VALID = dict(
    goal="LINEAR_SBOXCOUNT", constraints=[], objective_target="OPTIMAL",
    show_mode=0, config_model={}, config_solver={},
)


@pytest.mark.parametrize("override, error", [
    ({"goal": "DIFFERENTIAL_SBOXCOUNT"}, "Invalid goal"),             # linear rejects a differential goal
    ({"constraints": "INPUT_NOT_ZERO"}, "Invalid constraints"),      # a str, not a list
    ({"constraints": ["INPUT_NOT_ZERO", 1]}, "Invalid constraints"),  # a non-str element
    ({"objective_target": "MINIMIZE"}, "Invalid objective_target"),
    ({"show_mode": 9}, "Invalid show_mode"),
    ({"config_model": "x"}, "Invalid config_model"),                 # not a dict / None
    ({"config_solver": "x"}, "Invalid config_solver"),
])
def test_linear_validate_request_rejects_each_bad_field(override, error):
    with pytest.raises(ValueError, match=error):
        linear._validate_request(**dict(_LINEAR_VALID, **override))


def test_linear_validate_request_accepts_valid_request():
    linear._validate_request(**_LINEAR_VALID)  # must not raise
    linear._validate_request(**dict(_LINEAR_VALID, config_model=None, config_solver=None))


# ---------- config defaults ----------
def test_linear_frontend_defaults_many_solutions_for_hull_goal(tmp_path):
    _, config_solver = linear._parse_and_set_configs(
        _toy_cipher(), "LINEARHULL_CORR", "OPTIMAL", {"model_type": "sat", "filename": str(tmp_path / "m.cnf")}, {}
    )
    assert config_solver["solution_number"] == 1000000


# ---------- trail extraction / formatting ----------
def test_linear_extract_and_format_persists_each_distinct_trail(monkeypatch):
    class FakeTrail:
        def __init__(self, data, solution_trace=None):
            self.data = data
            self.solution_trace = solution_trace
            self.json_filename = "trail.json"
            self.txt_filename = "trail.txt"

        def print_trail(self, show_mode=2, hex_format=True):
            return None

        def save_json(self):
            return None

        def save_txt(self, show_mode=2, hex_format=True):
            return ""

    cipher = SimpleNamespace(name="toy", nbr_rounds=1, functions={"PERMUTATION": SimpleNamespace(nbr_rounds=1)})
    config_model = {"functions": ["PERMUTATION"], "rounds": {"PERMUTATION": [1]}}
    solutions = [
        {"obj_fun_value": 1, "rounds_obj_fun_values": [1]},
        {"obj_fun_value": 2, "rounds_obj_fun_values": [2]},
    ]

    monkeypatch.setattr(linear, "LinearTrail", FakeTrail)
    monkeypatch.setattr(
        attack_trace, "extract_trail_structures", lambda cipher, goal, sol, truncated_marker: {"id": sol["obj_fun_value"]}
    )

    trails = linear._extract_and_format_linear_trails(cipher, "LINEARHULL_CORR", config_model, {}, 2, solutions)
    assert len(trails) == 2  # two distinct solutions -> two deduplicated trails
