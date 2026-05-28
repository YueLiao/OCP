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


def test_artifact_ids_are_deterministic():
    links = [{"label": "trail_json_1", "path": "/tmp/ocp/trail.json"}]

    first = normalize_artifact_links(links, source_skill="differential_analysis")
    second = normalize_artifact_links(links, source_skill="differential_analysis")
    different_label = normalize_artifact_links(
        [{"label": "trail_text_1", "path": "/tmp/ocp/trail.json"}],
        source_skill="differential_analysis",
    )

    assert first[0]["id"] == second[0]["id"]
    assert first[0]["id"] != different_label[0]["id"]
    assert len(first[0]["id"]) == 16


def test_session_artifact_registry_deduplicates_by_id():
    session = Session()
    first = {"id": "same", "label": "old", "path": "/tmp/old.txt"}
    latest = {"id": "same", "label": "new", "path": "/tmp/new.txt"}
    other = {"id": "other", "label": "other", "path": "/tmp/other.txt"}

    session.add_artifacts([first, other])
    session.add_artifacts([latest])

    assert session.get_artifacts() == [other, latest]
    assert session.get_context()["artifact_count"] == 2


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
