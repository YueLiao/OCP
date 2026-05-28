from types import SimpleNamespace

from agent.session import Session
from agent.skills.code_generation import CodeGenerationSkill
from agent.types import SkillName, SkillRequest


def test_code_generation_uses_runtime_files_dir_by_default(monkeypatch, tmp_path):
    generated = {}

    def fake_generate_implementation(cipher, filename, language, unroll):
        generated["filename"] = filename
        generated["language"] = language
        generated["unroll"] = unroll

    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    monkeypatch.setattr(
        "implementations.implementations.generate_implementation",
        fake_generate_implementation,
    )

    session = Session()
    session.set_cipher(SimpleNamespace(name="Tiny", test_vectors=[]))

    result = CodeGenerationSkill().execute(
        SkillRequest(SkillName.CODE_GENERATION, {"language": "python", "test": False}),
        session,
    )

    assert result.success
    assert generated["filename"] == tmp_path / "Tiny.py"
    assert result.data["filename"] == str(tmp_path / "Tiny.py")


def test_code_generation_respects_explicit_output_dir(monkeypatch, tmp_path):
    explicit_dir = tmp_path / "explicit"
    generated = {}

    def fake_generate_implementation(cipher, filename, language, unroll):
        generated["filename"] = filename

    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path / "runtime"))
    monkeypatch.setattr(
        "implementations.implementations.generate_implementation",
        fake_generate_implementation,
    )

    session = Session()
    session.set_cipher(SimpleNamespace(name="Tiny", test_vectors=[]))

    result = CodeGenerationSkill().execute(
        SkillRequest(
            SkillName.CODE_GENERATION,
            {"language": "c", "output_dir": str(explicit_dir), "test": False},
        ),
        session,
    )

    assert result.success
    assert generated["filename"] == explicit_dir / "Tiny.c"
