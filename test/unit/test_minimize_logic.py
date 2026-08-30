import shutil

import pytest

from tools import minimize_logic
from tools.minimize_logic import espresso_pattern_to_ineq, ttb_to_ineq_logic


# ----------------------------- espresso_pattern_to_ineq (pure, no espresso needed) -----------------------------
def test_espresso_pattern_to_ineq_matches_docstring_example():
    # '0' -> +1, '1' -> -1 (and rhs -= 1), '-' -> 0 ; final rhs = -(#ones) + 1
    assert espresso_pattern_to_ineq("01-1") == [1, -1, 0, -1, -1]


@pytest.mark.parametrize("pattern,expected", [
    ("0", [1, 1]),    # +1 coeff, rhs = 0 + 1
    ("1", [-1, 0]),   # -1 coeff, rhs = -1 + 1
    ("-", [0, 1]),    # don't-care coeff, rhs = 0 + 1
])
def test_espresso_pattern_to_ineq_single_characters(pattern, expected):
    assert espresso_pattern_to_ineq(pattern) == expected


# ----------------------------- input validation (pure, no espresso needed) -----------------------------
@pytest.mark.parametrize("bad_mode", [3, -1, "x"])
def test_ttb_to_ineq_logic_rejects_invalid_mode(bad_mode):
    with pytest.raises(ValueError, match="Invalid mode"):
        ttb_to_ineq_logic("00", ["a"], mode=bad_mode)


def test_ttb_to_ineq_logic_rejects_unknown_tool_type(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))  # keep the intermediate PLA out of the repo
    with pytest.raises(ValueError, match="unknown tool type"):
        ttb_to_ineq_logic("00", ["a"], tool_type="bogus")


# ----------------------------- exclusion-semantics property test (needs the espresso CLI) -----------------------------
@pytest.mark.skipif(shutil.which("espresso") is None, reason="espresso CLI not on PATH")
def test_minimize_logic_matches_exclusion_semantics(monkeypatch, tmp_path):
    """A point is forbidden by some inequality iff it is in the ON-set (the
    invalid transitions, ttable[k]=='0'). Verified exhaustively for 3 variables."""
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    variables = ["a", "b", "c"]
    ttable = "01101001"  # arbitrary 3-variable table
    inequalities, _ = minimize_logic.ttb_to_ineq_logic(
        ttable, variables, tool_type="minimize_logic"
    )
    n = len(variables)
    for m in range(2 ** n):
        point = [(m >> (n - 1 - i)) & 1 for i in range(n)]  # variables[0] = MSB
        violated = any(
            sum(c * x for c, x in zip(ineq[:-1], point)) < ineq[-1]
            for ineq in inequalities
        )
        assert violated == (ttable[m] == "0")
