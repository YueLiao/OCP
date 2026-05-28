from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from agent.types import SkillResult
from agent.artifacts import artifacts_from_result_data


def artifact_links_from_data(data: Any) -> list:
    if isinstance(data, dict):
        return data.get("artifact_links", []) or []
    return []


def json_safe(value: Any) -> Any:
    """Convert common Agent result objects into JSON-safe values."""
    if is_dataclass(value):
        return json_safe(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "to_dict"):
        return json_safe(value.to_dict())
    return repr(value)


def skill_result_payload(
    result: SkillResult,
    *,
    context: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Serialize a SkillResult into the stable Agent/Web response shape."""
    data = result.data
    payload = {
        "success": result.success,
        "skill": result.skill.value,
        "summary": result.summary,
        "error": result.error,
        "data": json_safe(data),
        "artifact_links": json_safe(artifact_links_from_data(data)),
        "artifacts": json_safe(artifacts_from_result_data(data, source_skill=result.skill.value)),
    }
    if isinstance(data, dict):
        if "job" in data:
            payload["job"] = data["job"]
        elif "job_id" in data:
            payload["job_id"] = data["job_id"]
    if context is not None:
        payload["context"] = context
    if extra:
        payload.update(extra)
    return payload
