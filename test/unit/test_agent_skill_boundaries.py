from types import SimpleNamespace

from agent.interfaces.api import OCPAgent
from agent.session import Session
from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cipher_definition import CipherDefinitionSkill
from agent.skills.cipher_instantiation import CipherInstantiationSkill
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


def test_analysis_skills_reject_invalid_solution_number_at_boundary():
    for skill, skill_name in (
        (DifferentialAnalysisSkill(), SkillName.DIFFERENTIAL_ANALYSIS),
        (LinearAnalysisSkill(), SkillName.LINEAR_ANALYSIS),
    ):
        result = skill.execute(
            SkillRequest(skill_name, {"solution_number": 0}),
            _session_with_cipher(),
        )

        assert not result.success
        assert "Invalid solution_number" in result.error


def test_analysis_skills_reject_non_integer_solution_number_at_boundary():
    for skill, skill_name in (
        (DifferentialAnalysisSkill(), SkillName.DIFFERENTIAL_ANALYSIS),
        (LinearAnalysisSkill(), SkillName.LINEAR_ANALYSIS),
    ):
        result = skill.execute(
            SkillRequest(skill_name, {"solution_number": "2"}),
            _session_with_cipher(),
        )

        assert not result.success
        assert "Invalid solution_number" in result.error


def test_analysis_skills_reject_invalid_constraints_at_boundary():
    for skill, skill_name in (
        (DifferentialAnalysisSkill(), SkillName.DIFFERENTIAL_ANALYSIS),
        (LinearAnalysisSkill(), SkillName.LINEAR_ANALYSIS),
    ):
        result = skill.execute(
            SkillRequest(skill_name, {"constraints": ["INPUT_NOT_ZERO", 1]}),
            _session_with_cipher(),
        )

        assert not result.success
        assert "Invalid constraints" in result.error


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


def test_differential_analysis_classifies_expected_and_unexpected_failures(monkeypatch):
    def raise_expected(*args, **kwargs):
        raise ValueError("bad objective")

    monkeypatch.setattr("attacks.attacks.diff_attacks", raise_expected)

    result = DifferentialAnalysisSkill().execute(
        SkillRequest(SkillName.DIFFERENTIAL_ANALYSIS, {}),
        _session_with_cipher(),
    )

    assert not result.success
    assert result.error == "Differential analysis failed: bad objective"

    def raise_unexpected(*args, **kwargs):
        raise TypeError("programming detail")

    monkeypatch.setattr("attacks.attacks.diff_attacks", raise_unexpected)

    result = DifferentialAnalysisSkill().execute(
        SkillRequest(SkillName.DIFFERENTIAL_ANALYSIS, {}),
        _session_with_cipher(),
    )

    assert not result.success
    assert result.error == "Unexpected differential analysis failure: programming detail"


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


def test_linear_analysis_classifies_expected_and_unexpected_failures(monkeypatch):
    def raise_expected(*args, **kwargs):
        raise RuntimeError("solver unavailable")

    monkeypatch.setattr("attacks.attacks.linear_attacks", raise_expected)

    result = LinearAnalysisSkill().execute(
        SkillRequest(SkillName.LINEAR_ANALYSIS, {}),
        _session_with_cipher(),
    )

    assert not result.success
    assert result.error == "Linear analysis failed: solver unavailable"

    def raise_unexpected(*args, **kwargs):
        raise TypeError("programming detail")

    monkeypatch.setattr("attacks.attacks.linear_attacks", raise_unexpected)

    result = LinearAnalysisSkill().execute(
        SkillRequest(SkillName.LINEAR_ANALYSIS, {}),
        _session_with_cipher(),
    )

    assert not result.success
    assert result.error == "Unexpected linear analysis failure: programming detail"


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


def test_agent_visualization_classifies_unexpected_failures(monkeypatch, tmp_path):
    def fake_generate_figure(cipher, filepath):
        raise TypeError("programming detail")

    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    monkeypatch.setattr("visualisations.visualisations.generate_figure", fake_generate_figure)

    agent = OCPAgent()
    agent.session.set_cipher(SimpleNamespace(name="Tiny"))

    result = agent.generate_visualization()

    assert not result.success
    assert result.error == "Unexpected visualization failure: programming detail"


def test_cipher_instantiation_classifies_expected_and_unexpected_failures(monkeypatch):
    session = Session()

    def raise_expected(**kwargs):
        raise ValueError("bad version")

    monkeypatch.setattr("primitives.speck.SPECK_BLOCKCIPHER", raise_expected)
    result = CipherInstantiationSkill().execute(
        SkillRequest(
            SkillName.CIPHER_INSTANTIATION,
            {"cipher_name": "speck", "cipher_type": "blockcipher", "version": [32, 64]},
        ),
        session,
    )

    assert not result.success
    assert result.error == "Failed to instantiate speck: bad version"

    def raise_unexpected(**kwargs):
        raise TypeError("programming detail")

    monkeypatch.setattr("primitives.speck.SPECK_BLOCKCIPHER", raise_unexpected)
    result = CipherInstantiationSkill().execute(
        SkillRequest(
            SkillName.CIPHER_INSTANTIATION,
            {"cipher_name": "speck", "cipher_type": "blockcipher", "version": [32, 64]},
        ),
        session,
    )

    assert not result.success
    assert result.error == "Unexpected cipher instantiation failure for speck: programming detail"


def test_cipher_definition_classifies_expected_and_unexpected_failures(monkeypatch):
    spec = CipherSpec(
        name="TinyARX",
        cipher_type="permutation",
        block_size=32,
        word_bitsize=16,
        nbr_words=2,
        nbr_rounds=2,
        round_structure=[
            LayerSpec("rotation", {"direction": "r", "amount": 7, "word_index": 0}),
            LayerSpec("xor", {"input_indices": [[0, 1]], "output_indices": [1]}),
        ],
    )
    session = Session()

    monkeypatch.setattr(
        "agent.skills.cipher_definition.build_permutation_from_spec",
        lambda spec: (_ for _ in ()).throw(ValueError("bad layer")),
    )
    result = CipherDefinitionSkill().execute(
        SkillRequest(SkillName.CIPHER_DEFINITION, {"spec": spec}),
        session,
    )

    assert not result.success
    assert result.error == "Failed to build cipher: bad layer"

    monkeypatch.setattr(
        "agent.skills.cipher_definition.build_permutation_from_spec",
        lambda spec: (_ for _ in ()).throw(TypeError("programming detail")),
    )
    result = CipherDefinitionSkill().execute(
        SkillRequest(SkillName.CIPHER_DEFINITION, {"spec": spec}),
        session,
    )

    assert not result.success
    assert result.error == "Unexpected cipher definition failure: programming detail"
