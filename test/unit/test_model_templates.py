"""Unit tests for tools/model_templates.py - focused on the pure helpers: the
template-variable replacer, the inequality -> SAT/MILP constraint formatters, and
load_constraints_template's parse/error branches. (generate_and_save_constraints and
instantiate_constraints_template are exercised through test_model_constraints.py.)
"""
import pytest

from tools import model_templates as mt


# ------------------------------ build_template_replacer ------------------------------
def test_build_template_replacer_substitutes_indexed_tokens():
    replace = mt.build_template_replacer(("a", ["x0", "x1"]))
    assert replace("a0 + a1") == "x0 + x1"


def test_build_template_replacer_handles_multiple_groups_and_word_boundaries():
    replace = mt.build_template_replacer(("a", ["x"]), ("b", ["y"]))
    assert replace("a0 ^ b0") == "x ^ y"
    assert replace("a00") == "a00"  # word-boundary: "a0" inside "a00" is not a token


def test_build_template_replacer_skips_none_groups_and_is_identity_when_empty():
    replace = mt.build_template_replacer(("p", None))  # no groups -> identity
    assert replace("p0") == "p0"
    assert replace(None) is None


def test_build_template_replacer_passes_none_through_when_active():
    replace = mt.build_template_replacer(("a", ["x0"]))
    assert replace(None) is None


# ------------------------------ inequality_to_constraint_sat ------------------------------
def test_inequality_to_constraint_sat_maps_signs_to_literals():
    assert mt.inequality_to_constraint_sat([1, -1, 0, -1, -1], ["x1", "x2", "x3", "x4"]) == "x1 -x2 -x4"


def test_inequality_to_constraint_sat_rejects_all_zero():
    with pytest.raises(ValueError, match="no literals"):
        mt.inequality_to_constraint_sat([0, 0, 0], ["a", "b"])


# ------------------------------ inequality_to_constraint_milp ------------------------------
def test_inequality_to_constraint_milp_formats_terms_and_rhs():
    assert mt.inequality_to_constraint_milp([1, -1, 0, -1, -1], ["x1", "x2", "x3", "x4"]) == "x1 - x2 - x4 >= -1"


def test_inequality_to_constraint_milp_keeps_non_unit_coefficients():
    assert mt.inequality_to_constraint_milp([2, -3, 5], ["a", "b"]) == "2 a - 3 b >= 5"


def test_inequality_to_constraint_milp_rejects_all_zero():
    with pytest.raises(ValueError, match="no left-hand side"):
        mt.inequality_to_constraint_milp([0, 0, 7], ["a", "b"])


# ------------------------------ load_constraints_template ------------------------------
def test_load_constraints_template_returns_none_for_missing_file(tmp_path):
    assert mt.load_constraints_template(str(tmp_path / "nope.txt")) == (None, None)


def test_load_constraints_template_parses_constraints_and_weight(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("Constraints: ['a0 - b0 >= 0', 'a1 + b1 >= 1']\nWeight: 2 p0\n", encoding="utf-8")

    constraints, objective_fun = mt.load_constraints_template(str(f))

    assert constraints == ["a0 - b0 >= 0", "a1 + b1 >= 1"]
    assert objective_fun == "2 p0"


def test_load_constraints_template_rejects_malformed_constraints(tmp_path):
    f = tmp_path / "bad.txt"
    f.write_text("Constraints: [not, valid, python\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Failed to parse constraints"):
        mt.load_constraints_template(str(f))
