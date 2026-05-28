from pathlib import Path

from tools.paths import DEFAULT_FILES_DIR, get_files_dir


def test_get_files_dir_uses_repo_files_dir_by_default(monkeypatch):
    monkeypatch.delenv("OCP_FILES_DIR", raising=False)

    assert get_files_dir(create=False) == DEFAULT_FILES_DIR


def test_get_files_dir_honors_environment_override(monkeypatch, tmp_path):
    root = tmp_path / "ocp-artifacts"
    monkeypatch.setenv("OCP_FILES_DIR", str(root))

    nested = get_files_dir("models", "sat")

    assert nested == root / "models" / "sat"
    assert nested.is_dir()


def test_get_files_dir_can_skip_creation(monkeypatch, tmp_path):
    root = tmp_path / "not-created"
    monkeypatch.setenv("OCP_FILES_DIR", str(root))

    path = get_files_dir("later", create=False)

    assert path == root / "later"
    assert not path.exists()
