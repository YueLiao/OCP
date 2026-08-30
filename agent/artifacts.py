import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def _artifact_type(label: str, path: str) -> str:
    suffix = Path(path).suffix.lower()
    if "job" in label or suffix == ".json":
        return "json"
    if suffix in {".py", ".c", ".sv", ".v"}:
        return "source"
    if suffix in {".pdf", ".png", ".jpg", ".jpeg", ".svg"}:
        return "visualization"
    if suffix in {".txt", ".log"}:
        return "text"
    return "file"


def _artifact_id(source_skill: str, label: str, path: str) -> str:
    raw = f"{source_skill}:{label}:{path}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def normalize_artifact_links(
    artifact_links: Optional[Iterable[Dict[str, Any]]],
    *,
    source_skill: str,
) -> List[Dict[str, Any]]:
    """Expand legacy artifact links into structured artifact records."""
    artifacts = []
    created_at = datetime.now(timezone.utc).isoformat()
    for link in artifact_links or []:
        label = str(link.get("label", "artifact"))
        path = str(link.get("path", ""))
        artifacts.append(
            {
                "id": _artifact_id(source_skill, label, path),
                "label": label,
                "path": path,
                "type": _artifact_type(label, path),
                "source_skill": source_skill,
                "exists": Path(path).exists() if path else False,
                "created_at": created_at,
            }
        )
    return artifacts


def artifacts_from_result_data(data: Any, *, source_skill: str) -> List[Dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    if "artifacts" in data:
        return list(data.get("artifacts") or [])
    return normalize_artifact_links(data.get("artifact_links"), source_skill=source_skill)
