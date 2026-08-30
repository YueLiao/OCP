"""Unit tests for tools/polyhedron.py - the truth-table -> MILP/SAT inequality kernel
(convex-hull method). The coefficient/geometry helpers are pure and tested directly; the
pycddlib-backed ttb_to_ineq_convex_hull is exercised end to end when pycddlib is installed
and for its ImportError path otherwise.
"""
from fractions import Fraction

import pytest

from tools import polyhedron as poly


# ------------------------------ cdd row <-> (coeff, rhs) conversions ------------------------------
def test_cdd_ineq_to_coeff_rhs():
    assert poly.cdd_ineq_to_coeff_rhs([2, 3, 4]) == [3, 4, -2]  # [b,a...] -> [a..., -b]


def test_cdd_eq_to_coeff_rhs_splits_into_two_inequalities():
    assert poly.cdd_eq_to_coeff_rhs([2, 3, 4]) == [[3, 4, -2], [-3, -4, 2]]


# ------------------------------ inequality normalization ------------------------------
def test_normalize_inequality_clears_denominators_then_divides_by_gcd():
    assert poly.normalize_inequality([Fraction(1, 2), Fraction(1, 4)]) == [2, 1]
    assert poly.normalize_inequality([2, 4, 6]) == [1, 2, 3]
    assert poly.normalize_inequality([-2, 4]) == [-1, 2]
    assert poly.normalize_inequality([0, 0]) == [0, 0]  # all-zero: guarded against gcd-0 division


# ------------------------------ point / inequality geometry ------------------------------
def test_is_sat_uses_last_entry_as_rhs():
    assert poly.is_sat([1, 1], [1, 1, 1]) is True    # 1*1 + 1*1 >= 1
    assert poly.is_sat([0, 0], [1, 1, 1]) is False   # 0 >= 1


def test_collect_cutoffs_returns_only_unsatisfied_points():
    pts = [[0, 0], [1, 0], [1, 1]]
    assert poly.collect_cutoffs(pts, [1, 1, 1]) == [[0, 0]]  # only 0+0 < 1


class _Poly:
    def __init__(self, text):
        self._text = text

    def __str__(self):
        return self._text


def test_extract_equalities_indices_parses_linearity_line():
    assert poly.extract_equalities_indices(_Poly("begin\nlinearity 3 1 5 8\nend")) == [1, 5, 8]
    assert poly.extract_equalities_indices(_Poly("begin\nno equalities here\nend")) == []


# ------------------------------ greedy minimal cover ------------------------------
def test_minimize_constraints_greedy_selects_covering_inequality():
    # ttable "1110": only point [1,1] (index 3) is impossible; -a-b >= -1 cuts it off
    selected = poly.minimize_constraints_greedy([[-1, -1, -1]], ["a", "b"], "1110")
    assert selected == [[-1, -1, -1]]


def test_minimize_constraints_greedy_warns_when_point_uncoverable(capsys):
    # an inequality that cuts off nothing leaves the impossible point uncovered -> warn and stop
    selected = poly.minimize_constraints_greedy([[1, 1, 0]], ["a", "b"], "1110")
    assert selected == []
    assert "No inequality can further remove" in capsys.readouterr().out


# ------------------------------ convex-hull frontend (pycddlib) ------------------------------
def test_ttb_to_ineq_convex_hull_raises_without_cdd(monkeypatch):
    monkeypatch.setattr(poly, "cdd", None)
    with pytest.raises(ImportError, match="pycddlib is required"):
        poly.ttb_to_ineq_convex_hull("1110", ["a", "b"])


@pytest.mark.skipif(poly.cdd is None, reason="pycddlib not installed")
def test_ttb_to_ineq_convex_hull_cuts_off_exactly_the_impossible_points():
    ttable = "1110"  # valid: 00, 01, 10 ; impossible: 11
    ineqs, information = poly.ttb_to_ineq_convex_hull(ttable, ["a", "b"])

    assert information["Backend"] == "convex_hull_cdd"
    points = [[0, 0], [0, 1], [1, 0], [1, 1]]
    for i, pt in enumerate(points):
        satisfies_all = all(poly.is_sat(pt, ineq) for ineq in ineqs)
        assert satisfies_all == (ttable[i] == "1")  # possible <=> satisfies every selected inequality


def test_minimize_constraints_greedy_picks_inequality_covering_most_points():
    # ttable "1100": impossible points [1,0] and [1,1]; [-1,-1,-1] cuts only [1,1] while
    # [-1,0,0] cuts both -> the greedy heuristic must select the higher-coverage one first.
    selected = poly.minimize_constraints_greedy([[-1, -1, -1], [-1, 0, 0]], ["a", "b"], "1100")
    assert selected == [[-1, 0, 0]]
