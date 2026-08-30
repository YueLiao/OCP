from types import SimpleNamespace

import pytest

from attacks import attack_trace
from attacks import differential_cryptanalysis as diff


def _toy_cipher():
    return SimpleNamespace(
        name="toy",
        nbr_rounds=1,
        functions={"PERMUTATION": SimpleNamespace(nbr_rounds=1, nbr_layers=0, constraints={1: {0: []}})},
    )


# ---------- frontend request validation (all six branches, symmetric with linear) ----------
_DIFF_VALID = dict(
    goal="DIFFERENTIAL_SBOXCOUNT", constraints=[], objective_target="OPTIMAL",
    show_mode=0, config_model={}, config_solver={},
)


@pytest.mark.parametrize("override, error", [
    ({"goal": "NOPE"}, "Invalid goal"),
    ({"constraints": "INPUT_NOT_ZERO"}, "Invalid constraints"),       # a str, not a list
    ({"constraints": ["INPUT_NOT_ZERO", 1]}, "Invalid constraints"),  # a non-str element
    ({"objective_target": "MINIMIZE"}, "Invalid objective_target"),
    ({"show_mode": 9}, "Invalid show_mode"),
    ({"config_model": "x"}, "Invalid config_model"),                  # not a dict / None
    ({"config_solver": "x"}, "Invalid config_solver"),
])
def test_diff_validate_request_rejects_each_bad_field(override, error):
    with pytest.raises(ValueError, match=error):
        diff._validate_request(**dict(_DIFF_VALID, **override))


def test_diff_validate_request_accepts_valid_request():
    diff._validate_request(**_DIFF_VALID)  # must not raise
    diff._validate_request(**dict(_DIFF_VALID, config_model=None, config_solver=None))


# ---------- config defaults ----------
def test_diff_frontend_defaults_many_solutions_for_probability_goal(tmp_path):
    _, config_solver = diff._parse_and_set_configs(
        _toy_cipher(), "DIFFERENTIAL_PROB", "EXISTENCE", {"model_type": "sat", "filename": str(tmp_path / "m.cnf")}, {}
    )
    assert config_solver["solution_number"] == 1000000


# ---------- trail extraction / formatting ----------
def test_diff_extract_and_format_persists_each_distinct_trail(monkeypatch):
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

    monkeypatch.setattr(diff, "DifferentialTrail", FakeTrail)
    monkeypatch.setattr(
        attack_trace, "extract_trail_structures", lambda cipher, goal, sol, truncated_marker: {"id": sol["obj_fun_value"]}
    )

    trails = diff._extract_and_format_diff_trails(cipher, "DIFFERENTIAL_PROB", config_model, {}, 2, solutions)
    assert len(trails) == 2  # two distinct solutions -> two deduplicated trails
