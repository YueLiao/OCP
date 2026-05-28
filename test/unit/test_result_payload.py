from dataclasses import dataclass
from pathlib import Path

from agent.result_payload import json_safe, skill_result_payload
from agent.types import SkillName, SkillResult


@dataclass
class DraftLike:
    path: Path


def test_json_safe_converts_dataclasses_paths_and_unknown_objects():
    data = {"draft": DraftLike(Path("/tmp/draft.json")), "objects": [object()]}

    safe = json_safe(data)

    assert safe["draft"]["path"] == "/tmp/draft.json"
    assert isinstance(safe["objects"][0], str)


def test_skill_result_payload_preserves_artifact_links():
    result = SkillResult(
        success=True,
        skill=SkillName.CODE_GENERATION,
        data={"artifact_links": [{"label": "code", "path": Path("/tmp/a.py")}]},
        summary="ok",
    )

    payload = skill_result_payload(result, context={"has_cipher": True})

    assert payload["skill"] == "code_generation"
    assert payload["data"]["artifact_links"][0]["path"] == "/tmp/a.py"
    assert payload["artifact_links"][0]["path"] == "/tmp/a.py"
    assert payload["context"]["has_cipher"] is True
