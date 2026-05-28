from pathlib import Path

from agent.artifacts import normalize_artifact_links
from agent.session import Session
from agent.verifier import verify_action


def test_normalize_artifact_links_adds_metadata(tmp_path):
    artifact_path = tmp_path / "trail.json"
    artifact_path.write_text("{}", encoding="utf-8")

    artifacts = normalize_artifact_links(
        [{"label": "trail_json_1", "path": str(artifact_path)}],
        source_skill="differential_analysis",
    )

    assert artifacts[0]["label"] == "trail_json_1"
    assert artifacts[0]["type"] == "json"
    assert artifacts[0]["source_skill"] == "differential_analysis"
    assert artifacts[0]["exists"] is True
    assert artifacts[0]["created_at"]


def test_verifier_blocks_risky_actions_without_cipher():
    session = Session()

    result = verify_action("code", session, {"language": "python"})

    assert not result.ok
    assert "No cipher is loaded" in result.blocking_errors[0]


def test_verifier_rejects_invalid_codegen_language():
    session = Session()
    session.set_cipher(object())

    result = verify_action("code", session, {"language": "rust"})

    assert not result.ok
    assert "language must be" in result.blocking_errors[0]
