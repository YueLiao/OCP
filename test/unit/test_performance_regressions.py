import variables.variables as var
import pytest
from attacks.common import parse_and_set_configs
from attacks.common import extract_trail_structures
from operators.Sbox import PRESENT_Sbox, _compute_ddt_cached, _compute_lat_cached
from operators.matrix import (
    _generate_binary_matrix_2_cached,
    _generate_binary_matrix_3_cached,
    find_primitive_element_gf2m,
    generate_binary_matrix_2,
    generate_binary_matrix_3,
    generate_pmr_for_mds,
)
from primitives.arx import chacha_quarter_rounds, salsa_quarter_rounds
from primitives.chacha import CHACHA_KEYPERMUTATION, CHACHA_PERMUTATION
from primitives.forro import (
    FORRO_KEYPERMUTATION,
    FORRO_KEYPERMUTATION_TEST_OUTPUT,
    FORRO_PERMUTATION,
    FORRO_PERMUTATION_TEST_OUTPUT,
    FORRO_KEYSTREAM_TEMP_START,
    FORRO_TEST_INPUT,
    _forro_subround_selection,
)
from primitives.salsa import SALSA_KEYPERMUTATION, SALSA_PERMUTATION
from tools.model_configuration import gen_round_model_constraint_obj_fun
from tools.model_generation_state import (
    IDENTITY_ELISION_ALIASES_KEY,
    IDENTITY_ELISION_PROFILE_KEY,
    MODEL_GENERATION_PROFILE_ENABLED_KEY,
)
from tools.model_io import write_sat_model
from tools.profile_model_generation import main, profile_case, summarize_identity_elision_candidates
from solving import solving


def test_sbox_ddt_lat_are_cached_across_instances():
    _compute_ddt_cached.cache_clear()
    _compute_lat_cached.cache_clear()
    inputs = [var.Variable(4, ID="in")]
    outputs = [var.Variable(4, ID="out")]

    PRESENT_Sbox(inputs, outputs, ID="S1").computeDDT()
    PRESENT_Sbox(inputs, outputs, ID="S2").computeDDT()
    PRESENT_Sbox(inputs, outputs, ID="S3").computeLAT()
    PRESENT_Sbox(inputs, outputs, ID="S4").computeLAT()

    assert _compute_ddt_cached.cache_info().hits == 1
    assert _compute_lat_cached.cache_info().hits == 1


def test_matrix_helpers_cache_and_return_mutable_copies():
    find_primitive_element_gf2m.cache_clear()
    _generate_binary_matrix_2_cached.cache_clear()
    _generate_binary_matrix_3_cached.cache_clear()

    matrix2 = generate_binary_matrix_2("0x1b", 8)
    matrix2[0][0] = 99
    assert generate_binary_matrix_2("0x1b", 8)[0][0] != 99

    matrix3 = generate_binary_matrix_3("0x1b", 8)
    matrix3[0][0] = 99
    assert generate_binary_matrix_3("0x1b", 8)[0][0] != 99

    assert find_primitive_element_gf2m("0x1b", 8) == find_primitive_element_gf2m("0x1b", 8)
    assert _generate_binary_matrix_2_cached.cache_info().hits >= 1
    assert _generate_binary_matrix_3_cached.cache_info().hits >= 1
    assert find_primitive_element_gf2m.cache_info().hits == 1


def test_pmr_generation_cache_returns_mutable_copies():
    mds = [[2, 3], [1, 1]]

    pmr = generate_pmr_for_mds(mds, "0x1b", 8)
    pmr[0][0] = 99

    assert generate_pmr_for_mds(mds, "0x1b", 8)[0][0] != 99


def test_forro_subround_helper_preserves_round_schedule_and_structure():
    assert _forro_subround_selection(1) == (0, 4, 8, 12, 3)
    assert _forro_subround_selection(8) == (3, 4, 9, 14, 2)
    assert _forro_subround_selection(9) == (0, 4, 8, 12, 3)

    permutation = FORRO_PERMUTATION(r=1).functions["PERMUTATION"]
    key_permutation = FORRO_KEYPERMUTATION(r=1).functions["PERMUTATION"]

    assert permutation.nbr_layers == 12
    assert key_permutation.nbr_layers == 13
    assert [len(permutation.constraints[1][i]) for i in range(permutation.nbr_layers)] == [
        16
    ] * 12
    assert [
        len(key_permutation.constraints[1][i]) for i in range(key_permutation.nbr_layers)
    ] == [32] * 13

    assert permutation.constraints[1][0][12].__class__.__name__ == "ModAdd"
    assert permutation.constraints[1][0][12].ID == "Add1_1_1_12"
    assert [var.ID for var in permutation.constraints[1][0][12].input_vars] == [
        "v_1_0_12",
        "v_1_0_3",
    ]
    assert [var.ID for var in permutation.constraints[1][0][12].output_vars] == ["v_1_1_12"]

    rot1 = next(cons for cons in permutation.constraints[1][3] if cons.__class__.__name__ == "Rot")
    assert (rot1.ID, rot1.direction, rot1.amount) == ("Rot1_1_4_4", "l", 10)
    assert [var.ID for var in rot1.input_vars] == ["v_1_3_4"]
    assert [var.ID for var in rot1.output_vars] == ["v_1_4_4"]

    assert [constraint.__class__.__name__ for constraint in key_permutation.constraints[1][0][:16]] == [
        "Equal",
    ] * 16
    assert [constraint.__class__.__name__ for constraint in key_permutation.constraints[1][0][16:]] == [
        "NoneOperator",
    ] * 16
    assert key_permutation.constraints[1][0][16].input_vars[0].ID == "v_1_0_0"
    assert key_permutation.constraints[1][0][16].output_vars[0].ID == (
        f"v_1_1_{FORRO_KEYSTREAM_TEMP_START}"
    )


def test_forro_factories_attach_reference_test_vectors():
    permutation = FORRO_PERMUTATION(r=1)
    key_permutation = FORRO_KEYPERMUTATION(r=1)

    assert permutation.test_vectors == [[[FORRO_TEST_INPUT], FORRO_PERMUTATION_TEST_OUTPUT]]
    assert key_permutation.test_vectors == [[[FORRO_TEST_INPUT], FORRO_KEYPERMUTATION_TEST_OUTPUT]]


def test_chacha_arx_helper_preserves_round_schedule_and_structure():
    assert chacha_quarter_rounds(1)[0] == (0, 4, 8, 12)
    assert chacha_quarter_rounds(2)[0] == (0, 5, 10, 15)

    permutation = CHACHA_PERMUTATION(r=1).functions["PERMUTATION"]
    key_permutation = CHACHA_KEYPERMUTATION(r=1).functions["PERMUTATION"]

    assert permutation.nbr_layers == 12
    assert key_permutation.nbr_layers == 13
    assert [len(permutation.constraints[1][i]) for i in range(permutation.nbr_layers)] == [
        16
    ] * 12
    assert [
        len(key_permutation.constraints[1][i]) for i in range(key_permutation.nbr_layers)
    ] == [32] * 13


def test_salsa_arx_helper_preserves_round_schedule_and_structure():
    assert salsa_quarter_rounds(1)[0] == (0, 4, 8, 12)
    assert salsa_quarter_rounds(2)[0] == (0, 1, 2, 3)

    permutation = SALSA_PERMUTATION(r=1).functions["PERMUTATION"]
    key_permutation = SALSA_KEYPERMUTATION(r=1).functions["PERMUTATION"]

    assert permutation.nbr_layers == 12
    assert key_permutation.nbr_layers == 13
    assert [len(permutation.constraints[1][i]) for i in range(permutation.nbr_layers)] == [
        20
    ] * 12
    assert [
        len(key_permutation.constraints[1][i]) for i in range(key_permutation.nbr_layers)
    ] == [36] * 13


def test_model_generation_profiler_reports_constraint_hotspots():
    report = profile_case("present:1", top_limit=1)

    assert report["case"] == "present:1"
    assert report["constraint_count"] == report["profile"]["total_constraints"]
    assert report["constraint_count"] > 0
    assert report["profile"]["operators"]["PRESENT_Sbox"]["calls"] == 16
    assert report["top_operators"][0]["name"] == "PRESENT_Sbox"
    assert report["top_operators"][0]["calls"] == 16
    assert report["top_operators"][0]["constraints"] == 880
    assert len(report["top_operator_prefixes"]) == 1
    assert report["generation_time_s"] >= 0

    assert profile_case("chacha:1")["profile"]["operators"]["ModAdd"]["calls"] == 16
    assert profile_case("salsa:1")["profile"]["operators"]["ModAdd"]["calls"] == 16


def test_model_generation_profiler_rejects_invalid_cases():
    for case in ("", ":1", "forro:abc", "forro:0"):
        with pytest.raises(ValueError, match="[Pp]rofile case|rounds"):
            profile_case(case)


def test_model_generation_profiler_rejects_invalid_top_limit():
    for top_limit in (0, -1):
        with pytest.raises(ValueError, match="top_limit"):
            profile_case("present:1", top_limit=top_limit)


def test_model_generation_profiler_cli_reports_usage_errors(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["forro:abc"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "rounds must be a positive integer" in captured.err
    assert "Traceback" not in captured.err


def test_identity_elision_candidate_summary_is_conservative():
    report = profile_case("forro:1", top_limit=2)
    summary = report["identity_elision_candidates"]

    assert summary["estimated_constraints"] == 11520
    assert summary["estimated_ratio"] == round(11520 / report["constraint_count"], 6)
    assert summary["top_candidates"] == [
        {
            "name": "Equal:Add1_EQ",
            "calls": 15,
            "constraints": 960,
            "time_s": summary["top_candidates"][0]["time_s"],
        },
        {
            "name": "Equal:Add2_EQ",
            "calls": 15,
            "constraints": 960,
            "time_s": summary["top_candidates"][1]["time_s"],
        },
    ]

    profile = {
        "total_constraints": 20,
        "operator_prefixes": {
            "Equal:IN_LINK_EQ": {"calls": 1, "constraints": 2, "time_s": 0.0},
            "Equal:OUT_LINK_EQ": {"calls": 1, "constraints": 2, "time_s": 0.0},
            "Equal:LINK_EQ": {"calls": 1, "constraints": 2, "time_s": 0.0},
            "Equal:Add1_EQ": {"calls": 1, "constraints": 8, "time_s": 0.0},
        },
    }
    assert summarize_identity_elision_candidates(profile)["estimated_constraints"] == 8

    elided_profile = {
        "total_constraints": 20,
        "operator_prefixes": {
            "Equal:Add1_EQ": {"calls": 1, "constraints": 0, "time_s": 0.0},
        },
    }
    assert summarize_identity_elision_candidates(elided_profile) == {
        "estimated_constraints": 0,
        "estimated_ratio": 0.0,
        "top_candidates": [],
    }


def test_identity_elision_profile_can_skip_internal_equal_constraints():
    report = profile_case("forro:1", top_limit=2, identity_elision=True)

    assert report["identity_elision"] is True
    assert report["constraint_count"] == 5066
    assert report["identity_elision_profile"] == {
        "aliases": 180,
        "skipped_constraints": 180,
    }
    assert report["profile"]["operators"]["Equal"]["constraints"] == 2048
    assert report["top_operators"][0]["name"] == "ModAdd"


def test_identity_elision_supports_milp_model_generation():
    baseline = profile_case("forro:1", model_type="milp", top_limit=2)
    elided = profile_case(
        "forro:1",
        model_type="milp",
        top_limit=2,
        identity_elision=True,
    )

    assert baseline["constraint_count"] == 10029
    assert baseline["identity_elision_candidates"]["estimated_constraints"] == 5940
    assert elided["constraint_count"] == 4089
    assert elided["identity_elision_profile"] == {
        "aliases": 180,
        "skipped_constraints": 180,
    }
    assert elided["profile"]["operators"]["Equal"]["constraints"] == 1056


@pytest.mark.parametrize(
    ("case", "baseline_sat", "elided_sat", "baseline_milp", "elided_milp", "aliases"),
    [
        ("chacha:1", 20848, 11632, 15440, 10688, 144),
        ("salsa:1", 22896, 11632, 16496, 10688, 176),
    ],
)
def test_identity_elision_supports_chacha_and_salsa(case, baseline_sat, elided_sat, baseline_milp, elided_milp, aliases):
    sat_baseline = profile_case(case, top_limit=2)
    sat_elided = profile_case(case, top_limit=2, identity_elision=True)
    milp_baseline = profile_case(case, model_type="milp", top_limit=2)
    milp_elided = profile_case(case, model_type="milp", top_limit=2, identity_elision=True)

    assert sat_baseline["constraint_count"] == baseline_sat
    assert sat_elided["constraint_count"] == elided_sat
    assert sat_elided["identity_elision_profile"] == {
        "aliases": aliases,
        "skipped_constraints": aliases,
    }
    assert sat_elided["identity_elision_candidates"] == {
        "estimated_constraints": 0,
        "estimated_ratio": 0.0,
        "top_candidates": [],
    }

    assert milp_baseline["constraint_count"] == baseline_milp
    assert milp_elided["constraint_count"] == elided_milp
    assert milp_elided["identity_elision_profile"] == {
        "aliases": aliases,
        "skipped_constraints": aliases,
    }


def test_identity_elision_does_not_mutate_primitive_graph():
    cipher = FORRO_PERMUTATION(r=1)
    permutation = cipher.functions["PERMUTATION"]

    before_equal_edges = [
        (
            cons.ID,
            cons.input_vars[0].ID,
            cons.output_vars[0].ID,
        )
        for layer in range(permutation.nbr_layers)
        for cons in permutation.constraints[1][layer]
        if cons.__class__.__name__ == "Equal"
    ]
    before_var_ids = [
        var.ID
        for layer in range(permutation.nbr_layers + 1)
        for var in permutation.vars[1][layer]
    ]

    config_model, _ = parse_and_set_configs(
        cipher,
        "DIFFERENTIALPATH_PROB",
        "EXISTENCE",
        {
            "identity_elision": True,
            "model_type": "sat",
            MODEL_GENERATION_PROFILE_ENABLED_KEY: True,
        },
        {},
    )
    constraints, _ = gen_round_model_constraint_obj_fun(
        cipher,
        "DIFFERENTIALPATH_PROB",
        "sat",
        config_model,
    )

    after_equal_edges = [
        (
            cons.ID,
            cons.input_vars[0].ID,
            cons.output_vars[0].ID,
        )
        for layer in range(permutation.nbr_layers)
        for cons in permutation.constraints[1][layer]
        if cons.__class__.__name__ == "Equal"
    ]
    after_var_ids = [
        var.ID
        for layer in range(permutation.nbr_layers + 1)
        for var in permutation.vars[1][layer]
    ]

    assert len(constraints) == 5066
    assert config_model[IDENTITY_ELISION_PROFILE_KEY] == {
        "aliases": 180,
        "skipped_constraints": 180,
    }
    assert before_equal_edges == after_equal_edges
    assert before_var_ids == after_var_ids


def test_identity_elision_disabled_clears_private_state_on_reused_config():
    cipher = FORRO_PERMUTATION(r=1)
    config_model, _ = parse_and_set_configs(
        cipher,
        "DIFFERENTIALPATH_PROB",
        "EXISTENCE",
        {
            "identity_elision": True,
            "model_type": "sat",
            MODEL_GENERATION_PROFILE_ENABLED_KEY: True,
        },
        {},
    )
    gen_round_model_constraint_obj_fun(
        cipher,
        "DIFFERENTIALPATH_PROB",
        "sat",
        config_model,
    )

    config_model["identity_elision"] = False
    constraints, _ = gen_round_model_constraint_obj_fun(
        cipher,
        "DIFFERENTIALPATH_PROB",
        "sat",
        config_model,
    )

    assert len(constraints) == 16586
    assert IDENTITY_ELISION_ALIASES_KEY not in config_model
    assert IDENTITY_ELISION_PROFILE_KEY not in config_model


@pytest.mark.solver
def test_identity_elision_sat_solver_smoke_preserves_trail_lookup(pytestconfig, tmp_path):
    if not pytestconfig.getoption("--run-solver"):
        pytest.skip("external solver-dependent test; pass --run-solver to run")
    if not solving.is_solver_available("sat", "DEFAULT"):
        pytest.skip("PySAT backend is not available")

    cipher = FORRO_PERMUTATION(r=1)
    config_model, _ = parse_and_set_configs(
        cipher,
        "DIFFERENTIALPATH_PROB",
        "EXISTENCE",
        {
            "identity_elision": True,
            "model_type": "sat",
            "verbose": False,
        },
        {"solver": "DEFAULT", "solution_number": 1, "verbose": False},
    )
    config_model["filename"] = str(tmp_path / "forro_identity_elision.cnf")
    constraints, _ = gen_round_model_constraint_obj_fun(
        cipher,
        "DIFFERENTIALPATH_PROB",
        "sat",
        config_model,
    )
    model = write_sat_model(constraints, config_model["filename"])
    solutions = solving.solve_sat(
        config_model["filename"],
        model["variable_map"],
        {"solver": "DEFAULT", "solution_number": 1, "verbose": False},
    )

    assert solutions
    aliases = config_model[IDENTITY_ELISION_ALIASES_KEY]
    aliased_var, source_var = next(iter(aliases.items()))
    solution = solutions[0]
    trail = extract_trail_structures(
        cipher,
        "DIFFERENTIALPATH_PROB",
        solution,
        truncated_marker="TRUNCATEDDIFF",
        config_model=config_model,
    )

    def find_node(var_id):
        for round_store in trail["functions"]["PERMUTATION"].values():
            if not isinstance(round_store, dict):
                continue
            for layer_nodes in round_store.values():
                if not isinstance(layer_nodes, list):
                    continue
                for node in layer_nodes:
                    if node["var_ID"] == var_id:
                        return node
        return None

    source_node = find_node(source_var)
    aliased_node = find_node(aliased_var)
    assert source_node is not None
    assert aliased_node is not None
    assert aliased_node["bin_values"] == source_node["bin_values"]
    assert set(aliased_node["bin_values"]) <= {"0", "1"}
