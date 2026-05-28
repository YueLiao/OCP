from types import SimpleNamespace

from tools import minimize_logic


def test_logic_minimization_uses_runtime_files_dir(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, capture_output=True, text=True, timeout=None, check=False):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="0 1\n", stderr="")

    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    monkeypatch.setattr(minimize_logic, "pyeda", SimpleNamespace(__version__="test"))
    monkeypatch.setattr(minimize_logic.subprocess, "run", fake_run)

    inequalities, information = minimize_logic.ttb_to_ineq_logic(
        "01",
        ["x"],
        tool_type="minimize_logic",
    )

    assert inequalities == [[1, 1]]
    assert information["Backend"] == "espresso_pyeda"
    assert (tmp_path / "sbox_modeling" / "ttable.txt").exists()
    assert (tmp_path / "sbox_modeling" / "sttable.txt").exists()
    assert calls[0][-1] == str(tmp_path / "sbox_modeling" / "ttable.txt")
