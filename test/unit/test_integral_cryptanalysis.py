import pytest

import variables.variables as var
from attacks import integral_cryptanalysis as integral


# ------------------------------- pure helpers (no cipher / no solver) -------------------------------
def test_expand_var_ids():
    assert integral._expand_var_ids(var.Variable(4, ID="x")) == ["x_0", "x_1", "x_2", "x_3"]
    assert integral._expand_var_ids(var.Variable(1, ID="y")) == ["y"]


def test_normalize_bit_positions_dedup_sort_and_none():
    assert integral._normalize_bit_positions(None, 4) == []
    assert integral._normalize_bit_positions([3, 1, 1, 2], 4) == [1, 2, 3]
    assert integral._normalize_bit_positions([], 4) == []


def test_normalize_bit_positions_rejects_out_of_range():
    with pytest.raises(ValueError, match="Invalid bit position"):
        integral._normalize_bit_positions([4], 4)  # 4 == bit_size, out of range
    with pytest.raises(ValueError, match="Invalid bit position"):
        integral._normalize_bit_positions([-1], 4)


def test_build_final_objective():
    assert integral._build_final_objective(["a", "b", "c"]) == [["a + b + c"]]


def test_extract_unit_final_var():
    ids = ["a", "b", "c"]
    assert integral._extract_unit_final_var({"a": 0, "b": 1, "c": 0}, ids) == "b"
    assert integral._extract_unit_final_var({"a": 1.0}, ids) == "a"        # float ~1 counts
    assert integral._extract_unit_final_var({"a": 0, "b": 0, "c": 0}, ids) is None
    assert integral._extract_unit_final_var({}, ids) is None               # missing -> 0


def test_gen_ban_final_var_constraint():
    assert integral._gen_ban_final_var_constraint("v_3_0_5") == "v_3_0_5 = 0"


def test_final_var_id_to_bit_position():
    assert integral._final_var_id_to_bit_position("v_3_0_5") == 5
    assert integral._final_var_id_to_bit_position("x_12") == 12
    with pytest.raises(ValueError, match="Invalid final state variable ID"):
        integral._final_var_id_to_bit_position("v_3_0_x")


def test_final_var_ids_to_bit_positions():
    assert integral._final_var_ids_to_bit_positions(["v_1_0_3", "v_1_0_7"]) == [3, 7]


def test_add_index():
    assert integral._add_index("a/b.json", 2) == "a/b_2.json"
    assert integral._add_index("x/y.txt", 0) == "x/y_0.txt"


# ------------------------------- cipher-based (no solver) -------------------------------
def _speck(r=3):
    from primitives.speck import SPECK_PERMUTATION

    return SPECK_PERMUTATION(r=r)


def test_state_var_ids_are_nonempty_bitlevel_and_equal_length():
    cipher = _speck()
    init = integral._get_initial_state_var_ids(cipher)
    final = integral._get_final_state_var_ids(cipher)
    assert init and all(isinstance(v, str) for v in init)
    assert len(init) == len(final)  # input and output state have the same bit width


def test_gen_initial_two_subset_constraints_requires_constant_bits():
    with pytest.raises(ValueError, match="constant_bits must be explicitly provided"):
        integral._gen_initial_two_subset_constraints(_speck(), constant_bits=None)


def test_gen_initial_two_subset_constraints_shape():
    cipher = _speck()
    cons = integral._gen_initial_two_subset_constraints(cipher, constant_bits=[0])
    assert cons[-1].startswith("Binary\n")            # trailing Binary declaration
    assert any(c.endswith("= 0") for c in cons[:-1])  # the constant bit fixed to 0
    assert any(c.endswith("= 1") for c in cons[:-1])  # active bits fixed to 1


def test_parse_and_set_configs_defaults_and_filename():
    cipher = _speck()
    cm, cs = integral._parse_and_set_configs(cipher, "INTEGRAL_TWOSUBSET", "EXISTENCE", {}, {})
    assert cm["model_type"] == "milp"
    assert cs["solver"] == "DEFAULT" and cs["solution_number"] == 1
    assert {"functions", "rounds", "layers", "positions"} <= set(cm)
    assert "INTEGRAL_TWOSUBSET" in cm["filename"] and cm["filename"].endswith("milp_model.lp")


def test_parse_and_set_configs_rejects_non_milp():
    with pytest.raises(ValueError, match="only 'milp'"):
        integral._parse_and_set_configs(_speck(), "INTEGRAL_TWOSUBSET", "EXISTENCE", {"model_type": "sat"}, {})
