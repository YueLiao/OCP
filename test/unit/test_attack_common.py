from pathlib import Path
from types import SimpleNamespace

import pytest

import variables.variables as var
from attacks import common
from attacks.attack_trace import DifferentialTrail
from attacks import differential_cryptanalysis as diff
from attacks import linear_cryptanalysis as linear
from tools.model_generation_state import IDENTITY_ELISION_ALIASES_KEY
from tools import model_objective


def _boundary_cipher():
    inputs = [var.Variable(4, ID="x"), var.Variable(4, ID="y")]
    outputs = [var.Variable(4, ID="z")]
    return SimpleNamespace(
        inputs={"plaintext": inputs},
        outputs={"ciphertext": outputs},
        inputs_constraints=[SimpleNamespace(input_vars=inputs)],
    )


def test_fixed_input_constraints_expand_bits_consistently_for_diff_and_linear_sat():
    cipher = _boundary_cipher()
    config = {"model_type": "sat"}

    expected = ["-x_0", "-x_1", "-x_2", "x_3", "-y_0", "-y_1", "y_2", "-y_3"]

    assert diff.gen_fixed_input_output_constraints("input", "0x12", cipher, config) == expected
    assert linear.gen_fixed_input_output_constraints("input", "0x12", cipher, config) == expected


def test_fixed_output_constraints_generate_milp_binary_declarations():
    cipher = _boundary_cipher()

    assert common.gen_fixed_input_output_constraints(
        "output", "0b1010", cipher, {"model_type": "milp"}, value_name="fix_value"
    ) == [
        "z_0 = 1",
        "Binary\nz_0",
        "z_1 = 0",
        "Binary\nz_1",
        "z_2 = 1",
        "Binary\nz_2",
        "z_3 = 0",
        "Binary\nz_3",
    ]


def test_fixed_value_rejects_too_many_bits():
    with pytest.raises(ValueError, match="5 bits"):
        common.normalize_fixed_value_bits("0b10000", 4, "fix_value")


def test_fixed_value_rejects_malformed_hex_with_readable_error():
    with pytest.raises(ValueError, match="Invalid input_diff format"):
        common.normalize_fixed_value_bits("0xnothex", 4, "input_diff")


def test_input_non_zero_constraints_use_word_ids_for_truncated_goals():
    cipher = _boundary_cipher()

    assert diff.gen_input_non_zero_constraints(
        cipher, "TRUNCATEDDIFF_SBOXCOUNT", {"model_type": "sat"}
    ) == ["x y"]
    assert linear.gen_input_non_zero_constraints(
        cipher, "TRUNCATEDLINEAR_SBOXCOUNT", {"model_type": "sat"}
    ) == ["x y"]


def test_additional_constraints_expand_symbolic_input_nonzero_in_order():
    cipher = _boundary_cipher()

    assert common.gen_additional_constraints(
        cipher,
        "TRUNCATEDDIFF_SBOXCOUNT",
        ["custom >= 1", "INPUT_NOT_ZERO", "-tail"],
        {"model_type": "sat"},
        truncated_marker="TRUNCATEDDIFF",
    ) == ["custom >= 1", "x y", "-tail"]


def test_required_fixed_boundary_constraints_are_shared_for_diff_and_linear():
    cipher = _boundary_cipher()

    assert common.gen_required_fixed_boundary_constraints(
        "DIFFERENTIAL_PROB",
        "DIFFERENTIAL_PROB",
        cipher,
        {"model_type": "sat"},
        "0x12",
        None,
        "input_diff",
        "output_diff",
        "fix_diff",
    ) == ["-x_0", "-x_1", "-x_2", "x_3", "-y_0", "-y_1", "y_2", "-y_3"]

    with pytest.raises(ValueError, match="input_mask or output_mask"):
        common.gen_required_fixed_boundary_constraints(
            "LINEARHULL_CORR",
            "LINEARHULL_CORR",
            cipher,
            {"model_type": "sat"},
            None,
            None,
            "input_mask",
            "output_mask",
            "fix_mask",
        )


def test_solution_bit_only_suppresses_value_conversion_errors():
    class BrokenValue:
        def __round__(self):
            raise RuntimeError("unexpected solver value failure")

    assert common.solution_bit({"x": 1.0}, "x") == "1"
    assert common.solution_bit({"x": "not-a-number"}, "x") == "-"
    assert common.solution_bit({}, "x") == "-"

    with pytest.raises(RuntimeError, match="unexpected solver value failure"):
        common.solution_bit({"x": BrokenValue()}, "x")


def test_solution_bit_resolves_identity_elision_aliases():
    aliases = {"v_1_2_3": "v_1_1_3"}

    assert common.solution_bit({"v_1_1_3_0": 1}, "v_1_2_3_0", aliases=aliases) == "1"
    assert common.solution_bit({"v_1_1_30_0": 1}, "v_1_2_3_0", aliases=aliases) == "-"


def test_solution_bit_resolves_chained_identity_elision_aliases():
    aliases = {"v_1_3_0": "v_1_2_0", "v_1_2_0": "v_1_1_0"}

    assert common.solution_bit({"v_1_1_0_1": 1}, "v_1_3_0_1", aliases=aliases) == "1"


def test_extract_trail_structures_uses_identity_elision_aliases():
    source = var.Variable(2, ID="v_1_1_0")
    elided = var.Variable(2, ID="v_1_2_0")
    cipher_function = SimpleNamespace(
        nbr_rounds=1,
        nbr_layers=1,
        nbr_words=1,
        nbr_temp_words=0,
        vars=[[[], []], [[source], [elided]]],
    )
    cipher = SimpleNamespace(
        inputs={},
        outputs={},
        functions={"PERMUTATION": cipher_function},
    )
    solution = {"v_1_1_0_0": 1, "v_1_1_0_1": 0}
    config_model = {IDENTITY_ELISION_ALIASES_KEY: {"v_1_2_0": "v_1_1_0"}}

    trail = common.extract_trail_structures(
        cipher,
        "DIFFERENTIALPATH_PROB",
        solution,
        truncated_marker="TRUNCATEDDIFF",
        config_model=config_model,
    )

    assert trail["functions"]["PERMUTATION"][1][0][0]["bin_values"] == "10"
    assert trail["functions"]["PERMUTATION"][1][1][0]["bin_values"] == "10"


def test_decimal_weight_detection_uses_lat_for_linear_goals():
    class FakeSbox:
        def __init__(self):
            self.ddt_called = False
            self.lat_called = False

        def computeDDT(self):
            self.ddt_called = True
            return [[1]]

        def computeLAT(self):
            self.lat_called = True
            return [[1]]

        def gen_weights(self, table):
            return [1.5]

    fake_sbox = FakeSbox()
    cipher_function = SimpleNamespace(
        nbr_rounds=1,
        nbr_layers=0,
        constraints={1: {0: [fake_sbox]}},
    )
    cipher = SimpleNamespace(functions={"PERMUTATION": cipher_function})

    assert model_objective.has_Sbox_with_decimal_weights(cipher, "LINEARPATH_CORR")
    assert fake_sbox.lat_called
    assert not fake_sbox.ddt_called


def test_attack_trail_formatting_respects_verbose_false(monkeypatch, capsys):
    class FakeTrail:
        def __init__(self, data, solution_trace=None):
            self.data = data
            self.solution_trace = solution_trace
            self.json_filename = "trail.json"
            self.txt_filename = "trail.txt"

        def save_json(self):
            return None

        def save_txt(self, show_mode=0, emit_print=True):
            if emit_print:
                print("unexpected trail output")
            return ""

    cipher = SimpleNamespace(
        name="toy",
        functions={"PERMUTATION": SimpleNamespace(nbr_rounds=1)},
    )
    config_model = {"functions": ["PERMUTATION"], "rounds": {"PERMUTATION": [1]}, "verbose": False}
    config_solver = {"verbose": False}
    solutions = [
        {"obj_fun_value": 1, "rounds_obj_fun_values": [1]},
        {"obj_fun_value": 2, "rounds_obj_fun_values": [2]},
    ]

    monkeypatch.setattr(diff, "DifferentialTrail", FakeTrail)
    monkeypatch.setattr(linear, "LinearTrail", FakeTrail)
    monkeypatch.setattr(diff, "extract_trail_structures", lambda cipher, goal, sol, config_model=None: {"id": sol["obj_fun_value"]})
    monkeypatch.setattr(linear, "extract_trail_structures", lambda cipher, goal, sol, config_model=None: {"id": sol["obj_fun_value"]})

    diff.extract_and_format_diff_trails(cipher, "DIFFERENTIAL_PROB", config_model, config_solver, 2, solutions)
    linear.extract_and_format_linear_trails(cipher, "LINEARHULL_CORR", config_model, config_solver, 2, solutions)

    assert capsys.readouterr().out == ""


def test_attack_model_filename_honors_runtime_files_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    cipher = SimpleNamespace(
        name="toy",
        nbr_rounds=2,
        functions={
            "PERMUTATION": SimpleNamespace(
                nbr_rounds=2,
                nbr_layers=0,
                constraints={1: {0: []}, 2: {0: []}},
            )
        },
    )

    config_model, _ = common.parse_and_set_configs(
        cipher,
        "DIFFERENTIAL_SBOXCOUNT",
        "EXISTENCE",
        {},
        {},
    )

    assert Path(config_model["filename"]).parent == tmp_path


def test_attack_model_filename_preserves_explicit_path(tmp_path):
    cipher = SimpleNamespace(
        name="toy",
        nbr_rounds=1,
        functions={
            "PERMUTATION": SimpleNamespace(
                nbr_rounds=1,
                nbr_layers=0,
                constraints={1: {0: []}},
            )
        },
    )
    filename = tmp_path / "custom.cnf"

    config_model, _ = common.parse_and_set_configs(
        cipher,
        "DIFFERENTIAL_SBOXCOUNT",
        "EXISTENCE",
        {"model_type": "SAT", "filename": str(filename)},
        {},
    )

    assert config_model["model_type"] == "sat"
    assert config_model["filename"] == str(filename)


def test_attack_search_config_exposes_typed_fields_and_legacy_dicts(tmp_path):
    cipher = SimpleNamespace(
        name="toy",
        nbr_rounds=1,
        functions={
            "PERMUTATION": SimpleNamespace(
                nbr_rounds=1,
                nbr_layers=0,
                constraints={1: {0: []}},
            )
        },
    )
    filename = tmp_path / "typed.lp"

    attack_config = common.build_attack_search_config(
        cipher,
        "DIFFERENTIAL_PROB",
        "EXISTENCE",
        {"model_type": "MILP", "filename": str(filename)},
        {},
        many_solution_goal="DIFFERENTIAL_PROB",
    )
    config_model, config_solver = attack_config.as_dicts()

    assert attack_config.model_type == "milp"
    assert attack_config.filename == str(filename)
    assert config_model["model_type"] == "milp"
    assert config_solver["solution_number"] == 1000000


def test_attack_config_rejects_invalid_solution_number():
    cipher = SimpleNamespace(
        name="toy",
        nbr_rounds=1,
        functions={
            "PERMUTATION": SimpleNamespace(
                nbr_rounds=1,
                nbr_layers=0,
                constraints={1: {0: []}},
            )
        },
    )

    with pytest.raises(ValueError, match="solution_number"):
        common.parse_and_set_configs(
            cipher,
            "DIFFERENTIAL_SBOXCOUNT",
            "EXISTENCE",
            {"model_type": "sat"},
            {"solution_number": 0},
        )


def test_attack_search_request_validation_uses_value_errors():
    with pytest.raises(ValueError, match="Invalid objective_target"):
        common.validate_attack_search_request(
            "DIFFERENTIAL_SBOXCOUNT",
            ["DIFFERENTIAL_SBOXCOUNT"],
            [],
            "AT MOST",
            0,
            {},
            {},
        )

    with pytest.raises(ValueError, match="Invalid constraints"):
        common.validate_attack_search_request(
            "DIFFERENTIAL_SBOXCOUNT",
            ["DIFFERENTIAL_SBOXCOUNT"],
            "INPUT_NOT_ZERO",
            "EXISTENCE",
            0,
            {},
            {},
        )

    with pytest.raises(ValueError, match="Invalid constraints"):
        common.validate_attack_search_request(
            "DIFFERENTIAL_SBOXCOUNT",
            ["DIFFERENTIAL_SBOXCOUNT"],
            ["INPUT_NOT_ZERO", 1],
            "EXISTENCE",
            0,
            {},
            {},
        )


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
