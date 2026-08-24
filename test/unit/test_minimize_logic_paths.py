from types import SimpleNamespace

from tools import minimize_logic


def test_minimize_logic_uses_pyeda_without_external_espresso(monkeypatch, tmp_path):
    """The 'minimize_logic' path minimizes with PyEDA's built-in Espresso and must
    NOT shell out to an external `espresso` binary."""

    def forbidden_run(*args, **kwargs):
        raise AssertionError("minimize_logic must not invoke subprocess")

    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    monkeypatch.setattr(minimize_logic.subprocess, "run", forbidden_run)

    inequalities, information = minimize_logic.ttb_to_ineq_logic(
        "01",
        ["x"],
        tool_type="minimize_logic",
    )

    # onset = minterms where ttable[k]=='0' -> {0}; the cover is ~x -> pattern '0'
    # -> coefficient [1] with rhs 1, i.e. x >= 1 forbids the invalid point x=0.
    assert inequalities == [[1, 1]]
    assert information["Backend"] == "espresso_pyeda"
    # the PLA input file is still written for parity/inspection, but no espresso
    # output file is produced because nothing shells out.
    assert (tmp_path / "sbox_modeling" / "ttable.txt").exists()


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


def test_external_espresso_version_probe_failure_does_not_stop_minimization(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, capture_output=True, text=True, timeout=None, check=False):
        calls.append(command)
        if command[-1] == "-v":
            raise OSError("version probe failed")
        return SimpleNamespace(returncode=0, stdout="0 1\n", stderr="")

    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    monkeypatch.setattr(minimize_logic.subprocess, "run", fake_run)

    inequalities, information = minimize_logic.ttb_to_ineq_logic(
        "01",
        ["x"],
        tool_type="minimize_logic_espresso",
    )

    assert inequalities == [[1, 1]]
    assert information["Backend"] == "espresso"
    assert information["Backend version"] == "unknown"
    assert calls[0][-1] == "-v"
    assert calls[1][-1] == str(tmp_path / "sbox_modeling" / "ttable.txt")
