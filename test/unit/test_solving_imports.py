import os
import subprocess
import sys


def test_solving_module_import_is_quiet():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    result = subprocess.run(
        [sys.executable, "-c", "import solving.solving"],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "[WARNING]" not in result.stdout
    assert "[WARNING]" not in result.stderr
