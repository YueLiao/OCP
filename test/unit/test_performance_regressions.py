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
