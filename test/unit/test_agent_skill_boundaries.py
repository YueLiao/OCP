from types import SimpleNamespace

from agent.interfaces.api import OCPAgent
from agent.session import Session
from agent.skills.differential_analysis import DifferentialAnalysisSkill
from agent.skills.linear_analysis import LinearAnalysisSkill
from agent.types import SkillName, SkillRequest


def _session_with_cipher():
    session = Session()
    session.set_cipher(SimpleNamespace(name="Tiny", test_vectors=[]))
    return session


def test_analysis_skills_reject_invalid_model_type_at_boundary():
    for skill, skill_name in (
        (DifferentialAnalysisSkill(), SkillName.DIFFERENTIAL_ANALYSIS),
        (LinearAnalysisSkill(), SkillName.LINEAR_ANALYSIS),
    ):
        result = skill.execute(
            SkillRequest(skill_name, {"model_type": "cp"}),
            _session_with_cipher(),
        )

        assert not result.success
        assert "Invalid model_type" in result.error


def test_differential_analysis_returns_trail_artifact_links(monkeypatch, tmp_path):
    trail = SimpleNamespace(
        json_filename=tmp_path / "diff.json",
        txt_filename=tmp_path / "diff.txt",
    )

    def fake_diff_attacks(*args, **kwargs):
        return [trail]

    monkeypatch.setattr("attacks.attacks.diff_attacks", fake_diff_attacks)

    result = DifferentialAnalysisSkill().execute(
        SkillRequest(SkillName.DIFFERENTIAL_ANALYSIS, {}),
        _session_with_cipher(),
    )

    assert result.success
    assert result.data["artifact_links"] == [
        {"label": "trail_json_1", "path": str(tmp_path / "diff.json")},
        {"label": "trail_text_1", "path": str(tmp_path / "diff.txt")},
    ]


def test_linear_analysis_returns_trail_artifact_links(monkeypatch, tmp_path):
    trail = SimpleNamespace(
        json_filename=tmp_path / "linear.json",
        txt_filename=tmp_path / "linear.txt",
    )

    def fake_linear_attacks(*args, **kwargs):
        return [trail]

    monkeypatch.setattr("attacks.attacks.linear_attacks", fake_linear_attacks)

    result = LinearAnalysisSkill().execute(
        SkillRequest(SkillName.LINEAR_ANALYSIS, {}),
        _session_with_cipher(),
    )

    assert result.success
    assert result.data["artifact_links"] == [
        {"label": "trail_json_1", "path": str(tmp_path / "linear.json")},
        {"label": "trail_text_1", "path": str(tmp_path / "linear.txt")},
    ]


def test_agent_generate_code_uses_runtime_files_dir_by_default(monkeypatch, tmp_path):
    generated = {}

    def fake_generate_implementation(cipher, filename, language, unroll):
        generated["filename"] = filename

    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    monkeypatch.setattr(
        "implementations.implementations.generate_implementation",
        fake_generate_implementation,
    )

    agent = OCPAgent()
    agent.session.set_cipher(SimpleNamespace(name="Tiny", test_vectors=[]))

    result = agent.generate_code(language="python", test=False)

    assert result.success
    assert generated["filename"] == tmp_path / "Tiny.py"


def test_agent_visualization_uses_runtime_files_dir_by_default(monkeypatch, tmp_path):
    generated = {}

    def fake_generate_figure(cipher, filepath):
        generated["filepath"] = filepath

    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    monkeypatch.setattr("visualisations.visualisations.generate_figure", fake_generate_figure)

    agent = OCPAgent()
    agent.session.set_cipher(SimpleNamespace(name="Tiny"))

    result = agent.generate_visualization()

    assert result.success
    assert generated["filepath"] == tmp_path / "Tiny.pdf"
    assert result.data["filename"] == str(tmp_path / "Tiny.pdf")
    assert result.data["artifact_links"] == [
        {"label": "visualization", "path": str(tmp_path / "Tiny.pdf")}
    ]


def test_agent_visualization_wraps_output_directory_errors(tmp_path):
    blocked_output_dir = tmp_path / "not-a-dir"
    blocked_output_dir.write_text("file blocks mkdir", encoding="utf-8")

    agent = OCPAgent()
    agent.session.set_cipher(SimpleNamespace(name="Tiny"))

    result = agent.generate_visualization(output_dir=str(blocked_output_dir))

    assert not result.success
    assert result.error.startswith("Visualization failed:")
