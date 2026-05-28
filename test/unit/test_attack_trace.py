from attacks.attack_trace import DifferentialTrail, bin_to_hex


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


def test_bin_to_hex_can_suppress_warnings(capsys):
    assert bin_to_hex("10-", warn=False) == "-"
    assert capsys.readouterr().out == ""


def test_trail_save_txt_can_suppress_printing(tmp_path, capsys):
    trail = DifferentialTrail(_trail_data())
    trail.txt_filename = str(tmp_path / "trail.txt")

    text = trail.save_txt(show_mode=2, emit_print=False)

    assert "Total Weight: 2" in text
    assert (tmp_path / "trail.txt").read_text() == text
    assert capsys.readouterr().out == ""
