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
    assert result.data["artifact_links"] == [
        {"label": "generated_code", "path": str(tmp_path / "Tiny.py")}
    ]


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


def test_code_generation_reports_structured_test_summary(monkeypatch, tmp_path):
    def fake_generate_implementation(cipher, filename, language, unroll):
        return None

    def fake_test_implementation_python(cipher, impl_name, test_input, expected_output):
        if expected_output == ["bad"]:
            raise AssertionError("mismatch")

    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    monkeypatch.setattr(
        "implementations.implementations.generate_implementation",
        fake_generate_implementation,
    )
    monkeypatch.setattr(
        "implementations.implementations.test_implementation_python",
        fake_test_implementation_python,
    )

    session = Session()
    session.set_cipher(
        SimpleNamespace(
            name="Tiny",
            test_vectors=[
                ([["input"]], ["ok"]),
                ([["input"]], ["bad"]),
            ],
        )
    )

    result = CodeGenerationSkill().execute(
        SkillRequest(SkillName.CODE_GENERATION, {"language": "python"}),
        session,
    )

    assert result.success
    assert result.data["test_results"][0] is True
    assert result.data["test_results"][1] == "mismatch"
    assert result.data["test_summary"] == {"passed": 1, "total": 2, "failed": 1}
