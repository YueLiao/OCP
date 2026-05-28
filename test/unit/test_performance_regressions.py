import variables.variables as var
from operators.Sbox import PRESENT_Sbox, _compute_ddt_cached, _compute_lat_cached
from operators.matrix import (
    _generate_binary_matrix_2_cached,
    _generate_binary_matrix_3_cached,
    find_primitive_element_gf2m,
    generate_binary_matrix_2,
    generate_binary_matrix_3,
)
from primitives.forro import (
    FORRO_KEYPERMUTATION,
    FORRO_PERMUTATION,
    _forro_subround_selection,
)
from tools.profile_model_generation import profile_case


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


def test_model_generation_profiler_reports_constraint_hotspots():
    report = profile_case("present:1")

    assert report["case"] == "present:1"
    assert report["constraint_count"] == report["profile"]["total_constraints"]
    assert report["constraint_count"] > 0
    assert report["profile"]["operators"]["PRESENT_Sbox"]["calls"] == 16
    assert report["generation_time_s"] >= 0
