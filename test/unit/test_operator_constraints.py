"""Unit tests for tools/operator_constraints.py - the per-operator SAT/MILP constraint
builders. Covers the helpers not already exercised through test_model_constraints.py:
Binary/Integer declarations, equivalence / OR / implication, word-level XOR and n-XOR,
and the whole-matrix constraint/declaration generators.
"""
import pytest

from tools import operator_constraints as oc


# ------------------------------ Binary / Integer declarations ------------------------------
def test_binary_and_integer_declaration_flatten_groups():
    assert oc.binary_declaration(["a", "b"]) == "Binary\na b"
    assert oc.binary_declaration(["a"], ["b", "c"]) == "Binary\na b c"
    assert oc.integer_declaration(["d"]) == "Integer\nd"


def test_declaration_rejects_bare_string_and_non_string():
    with pytest.raises(TypeError, match="not a bare string"):
        oc.binary_declaration("ab")           # a bare string would iterate char by char
    with pytest.raises(TypeError, match="must be a string"):
        oc.binary_declaration([1])            # non-string variable


# ------------------------------ equivalence ------------------------------
def test_gen_equivalence_constraints_sat_and_milp():
    assert oc.gen_equivalence_constraints(["a"], ["b"], "sat") == ["-a b", "a -b"]
    assert oc.gen_equivalence_constraints(["a"], ["b"], "milp") == ["a - b = 0"]


def test_gen_equivalence_constraints_rejects_length_mismatch_and_bad_model():
    with pytest.raises(ValueError, match="equal length"):
        oc.gen_equivalence_constraints(["a"], ["b", "c"], "sat")
    with pytest.raises(ValueError, match="unknown model type"):
        oc.gen_equivalence_constraints(["a"], ["b"], "foo")


# ------------------------------ OR ------------------------------
def test_gen_or_constraints_sat_and_milp():
    assert oc.gen_or_constraints("a", "b", "c", "sat") == ["-a c", "-b c", "-c a b"]
    assert oc.gen_or_constraints("a", "b", "c", "milp") == ["c - a >= 0", "c - b >= 0", "a + b - c >= 0"]


def test_gen_or_constraints_rejects_bad_model_and_non_string():
    with pytest.raises(ValueError, match="unknown model type"):
        oc.gen_or_constraints("a", "b", "c", "foo")
    with pytest.raises(TypeError, match="must be strings"):
        oc.gen_or_constraints("a", "b", 1, "sat")


# ------------------------------ implication ------------------------------
def test_gen_implication_constraints_sat_and_milp():
    assert oc.gen_implication_constraints("a", "b", "sat") == ["-a b"]
    assert oc.gen_implication_constraints("a", "b", "milp") == ["b - a >= 0"]
    with pytest.raises(ValueError, match="unknown model type"):
        oc.gen_implication_constraints("a", "b", "foo")


# ------------------------------ word-level XOR ------------------------------
def test_gen_word_xor_constraints_sat_and_milp_v0():
    assert oc.gen_word_xor_constraints("a", "b", "c", "sat") == ["a b -c", "a -b c", "-a b c"]
    assert oc.gen_word_xor_constraints("a", "b", "c", "milp") == [
        "a + b - c >= 0", "b + c - a >= 0", "a + c - b >= 0",
    ]


def test_gen_word_xor_constraints_milp_v1_uses_dummy():
    assert oc.gen_word_xor_constraints("a", "b", "c", "milp", v_dummy="d", version=1) == [
        "a + b + c - 2 d >= 0", "d - a >= 0", "d - b >= 0", "d - c >= 0",
    ]


def test_gen_word_xor_constraints_rejects_bad_version_and_model():
    with pytest.raises(ValueError, match="Unknown version"):
        oc.gen_word_xor_constraints("a", "b", "c", "sat", version=1)
    with pytest.raises(ValueError, match="unknown model type"):
        oc.gen_word_xor_constraints("a", "b", "c", "foo")


# ------------------------------ word-level n-XOR ------------------------------
def test_gen_word_nxor_constraints_sat_and_milp():
    assert oc.gen_word_nxor_constraints(["a", "b"], "c", "milp") == [
        "a + b - c >= 0", "b + c - a >= 0", "a + c - b >= 0",
    ]
    assert oc.gen_word_nxor_constraints(["a", "b"], "c", "sat") == ["-c a b", "b c -a", "a c -b"]


def test_gen_word_nxor_constraints_rejects_bad_model():
    with pytest.raises(ValueError, match="unknown model type"):
        oc.gen_word_nxor_constraints(["a", "b"], "c", "foo")


# ------------------------------ whole-matrix constraints ------------------------------
def test_gen_matrix_constraints_dispatches_per_row_sat():
    # row 0 = [1,0] -> equivalence(s0,t0); row 1 = [1,1] -> XOR(s0,s1,t1)
    assert oc.gen_matrix_constraints([[1, 0], [1, 1]], ["s0", "s1"], ["t0", "t1"], "sat") == [
        "-s0 t0", "s0 -t0",
        "s0 s1 -t1", "s0 -s1 t1", "-s0 s1 t1", "-s0 -s1 -t1",
    ]


def test_gen_matrix_constraints_milp_three_inputs_use_named_dummy():
    # a row with 3 active inputs dispatches to n-XOR, whose MILP dummy is "<prefix>_<row>"
    assert oc.gen_matrix_constraints([[1, 1, 1]], ["s0", "s1", "s2"], ["t0"], "milp", dummy_prefix="dum") == [
        "s0 + s1 + s2 + t0 - 2 dum_0 = 0", "dum_0 >= 0", "dum_0 <= 2",
    ]


# ------------------------------ whole-matrix declarations ------------------------------
def test_gen_matrix_declarations_binary_only_when_no_wide_row():
    assert oc.gen_matrix_declarations([[1, 0], [1, 1]], ["s0", "s1"], ["t0", "t1"], "dum") == [
        "Binary\ns0 t0 s1 t1",
    ]


def test_gen_matrix_declarations_adds_integer_dummy_for_wide_row():
    assert oc.gen_matrix_declarations([[1, 1, 1]], ["s0", "s1", "s2"], ["t0"], "dum") == [
        "Binary\ns0 s1 s2 t0", "Integer\ndum_0",
    ]


# ------------------------------ bit-level XOR (MILP encodings) ------------------------------
def test_gen_xor_constraints_milp_versions():
    assert oc.gen_xor_constraints("a", "b", "c", "milp") == [
        "a + b - c >= 0", "b + c - a >= 0", "a + c - b >= 0", "a + b + c <= 2",
    ]
    assert oc.gen_xor_constraints("a", "b", "c", "milp", v_dummy="d", version=1) == [
        "a + b + c - 2 d >= 0", "a + b + c <= 2", "d - a >= 0", "d - b >= 0", "d - c >= 0",
    ]
    assert oc.gen_xor_constraints("a", "b", "c", "milp", v_dummy="d", version=2) == ["a + b + c - 2 d = 0"]


# ------------------------------ bit-level n-XOR (SAT parity + MILP encodings) ------------------------------
def test_gen_nxor_constraints_sat_parity_enumeration():
    # every subset with the wrong parity is forbidden: even |comb| -> -c, odd -> c
    assert oc.gen_nxor_constraints(["a", "b"], "c", "sat") == ["-c a b", "c -a b", "c a -b", "-c -a -b"]


def test_gen_nxor_constraints_milp_versions():
    assert oc.gen_nxor_constraints(["a", "b"], "c", "milp", v_dummy="d") == [
        "a + b + c - 2 d = 0", "d >= 0", "d <= 1",
    ]
    assert oc.gen_nxor_constraints(["a", "b"], "c", "milp", v_dummy=["d0"], version=1) == ["a + b + c - 2 d0 = 0"]


# ------------------------------ matrix-row dispatch: empty input ------------------------------
def test_matrix_row_constraints_reject_empty_inputs():
    with pytest.raises(ValueError, match="at least one input"):
        oc.gen_matrix_row_constraints([], "t", "sat")
    with pytest.raises(ValueError, match="at least one input"):
        oc.gen_word_matrix_row_constraints([], "t", "sat")
