import json
from pathlib import Path
from types import SimpleNamespace

from attacks import attack_trace
from attacks.attack_trace import DifferentialTrail, bin_to_hex
import pytest


class _FakeTrail:
    """Minimal trail stand-in so extract_and_format_trails can run without touching disk."""

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


def _trail_data():
    node = {"var_ID": "x", "variables": ["x_0", "x_1", "x_2", "x_3"], "bin_values": "1010"}
    return {
        "cipher": "toy",
        "rounds": {"PERMUTATION": [1]},
        "functions": ["PERMUTATION"],
        "config_model": {},
        "config_solver": {},
        "trail_struct": {
            "inputs": {"plaintext": [node]},
            "outputs": {"ciphertext": [node]},
            "functions": {
                "PERMUTATION": {
                    "rounds": [1],
                    "nbr_words": 1,
                    "nbr_temp_words": 0,
                    1: {0: [node]},
                }
            },
        },
        "diff_weight": 2,
        "rounds_diff_weight": [2],
    }


def test_bin_to_hex_left_pads_preserving_value(capsys):
    assert bin_to_hex("101") == "5"  # left-padded to "0101", value preserved
    assert "leading" in capsys.readouterr().out


def test_bin_to_hex_prints_warning_for_mixed_unknown_bits(capsys):
    assert bin_to_hex("10--") == "-"
    assert "mixed unknown bits" in capsys.readouterr().out


def test_trail_requires_cipher():
    with pytest.raises(ValueError, match="must contain 'cipher'"):
        DifferentialTrail({"rounds": []})


def test_trail_save_txt_writes_without_printing(tmp_path, capsys):
    trail = DifferentialTrail(_trail_data())
    trail.txt_filename = str(tmp_path / "trail.txt")

    text = trail.save_txt(show_mode=2)

    assert "Total Weight: 2" in text
    assert (tmp_path / "trail.txt").read_text() == text
    assert capsys.readouterr().out == ""  # save_txt is a pure write; print_trail handles display


def test_trail_print_trail_writes_to_stdout(capsys):
    trail = DifferentialTrail(_trail_data())

    trail.print_trail(show_mode=2)

    out = capsys.readouterr().out
    assert "========== Trail ==========" in out
    assert "Total Weight: 2" in out


def test_extract_and_format_trails_deduplicates_identical_structs(monkeypatch):
    # Two DISTINCT solutions that extract to the SAME structure must collapse to one trail,
    # i.e. the `if trail_struct in trail_structs: continue` branch actually fires.
    cipher = SimpleNamespace(name="toy", nbr_rounds=1)
    config_model = {"functions": ["PERMUTATION"], "rounds": {"PERMUTATION": [1]}}
    solutions = [
        {"obj_fun_value": 1, "rounds_obj_fun_values": [1]},
        {"obj_fun_value": 2, "rounds_obj_fun_values": [2]},
    ]
    monkeypatch.setattr(attack_trace, "extract_trail_structures",
                        lambda cipher, goal, sol, truncated_marker: {"same": "struct"})

    trails = attack_trace.extract_and_format_trails(
        cipher, "DIFFERENTIAL_PROB", config_model, {}, 2, solutions,
        _FakeTrail, "TRUNCATEDDIFF", "diff_weight", "rounds_diff_weight",
    )

    assert len(trails) == 1  # identical structs deduplicated to a single trail


def test_extract_and_format_trails_keeps_distinct_structs(monkeypatch):
    # Control for the dedup test: genuinely different structures are all kept.
    cipher = SimpleNamespace(name="toy", nbr_rounds=1)
    config_model = {"functions": ["PERMUTATION"], "rounds": {"PERMUTATION": [1]}}
    solutions = [
        {"obj_fun_value": 1, "rounds_obj_fun_values": [1]},
        {"obj_fun_value": 2, "rounds_obj_fun_values": [2]},
    ]
    monkeypatch.setattr(attack_trace, "extract_trail_structures",
                        lambda cipher, goal, sol, truncated_marker: {"id": sol["obj_fun_value"]})

    trails = attack_trace.extract_and_format_trails(
        cipher, "DIFFERENTIAL_PROB", config_model, {}, 2, solutions,
        _FakeTrail, "TRUNCATEDDIFF", "diff_weight", "rounds_diff_weight",
    )

    assert len(trails) == 2


def test_trail_to_dict_carries_tool_tag_and_core_sections():
    d = DifferentialTrail(_trail_data()).to_dict()
    assert set(d) == {"type", "data", "solution_trace", "tool"}
    assert d["tool"] == "OCP1.0"           # OCP version tag
    assert d["type"] == "DIFFERENTIAL"     # uppercased attack type
    assert d["data"]["diff_weight"] == 2


def test_trail_save_json_writes_serialized_to_dict(tmp_path):
    trail = DifferentialTrail(_trail_data())
    trail.json_filename = str(tmp_path / "trail.json")

    trail.save_json()

    loaded = json.loads((tmp_path / "trail.json").read_text(encoding="utf-8"))
    # (full equality would fail only because JSON coerces the trail_struct's int keys to strings)
    assert set(loaded) == {"type", "data", "solution_trace", "tool"}
    assert loaded["tool"] == "OCP1.0"
    assert loaded["type"] == "DIFFERENTIAL"
    assert loaded["data"]["diff_weight"] == 2


def test_solution_bit_only_suppresses_value_conversion_errors():
    class BrokenValue:
        def __round__(self):
            raise RuntimeError("unexpected solver value failure")

    assert attack_trace.solution_bit({"x": 1.0}, "x") == "1"
    assert attack_trace.solution_bit({"x": "not-a-number"}, "x") == "-"
    assert attack_trace.solution_bit({}, "x") == "-"

    with pytest.raises(RuntimeError, match="unexpected solver value failure"):
        attack_trace.solution_bit({"x": BrokenValue()}, "x")


def test_attack_trace_fallback_filename_honors_runtime_files_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))

    trail = DifferentialTrail(
        {
            "cipher": "toy",
            "rounds": [1],
            "config_model": {},
            "config_solver": {"solver": "DEFAULT"},
        }
    )

    assert Path(trail.json_filename).parent == tmp_path
    assert Path(trail.txt_filename).parent == tmp_path
