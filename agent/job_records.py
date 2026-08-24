"""Replayable job records for Agent workflows."""

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from tools.paths import get_files_dir


def _json_safe(value):
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def _write_record(path, record):
    path.write_text(json.dumps(_json_safe(record), indent=2, sort_keys=True), encoding="utf-8")


def _content_hash(value):
    payload = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_record(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _provider_metadata(provider):
    if provider is None:
        return None
    return {
        "class": provider.__class__.__name__,
        "model": getattr(provider, "model", None),
        "base_url": getattr(provider, "base_url", None) or getattr(provider, "host", None),
    }


def create_text_job_record(cipher_input, prompt, raw_response, facts, errors, warnings,
                           provider=None, classification=None):
    """Create a replayable record for text-first cipher extraction."""

    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    job_id = f"text-{created_at.replace(':', '').replace('+00:00', 'Z')}-{uuid4().hex[:8]}"
    path = get_files_dir("agent_jobs") / f"{job_id}.json"
    record = {
        "job_id": job_id,
        "kind": "text_cipher_extraction",
        "created_at": created_at,
        "updated_at": created_at,
        "provider": _provider_metadata(provider),
        "metadata": {
            "prompt_version": "text-cipher-facts-v1",
            "raw_text_sha256": _content_hash(cipher_input.raw_text),
            "normalized_text_sha256": _content_hash(cipher_input.normalized_text),
            "prompt_sha256": _content_hash(prompt),
            "raw_response_sha256": _content_hash(raw_response),
        },
        "input": {
            "raw_text": cipher_input.raw_text,
            "normalized_text": cipher_input.normalized_text,
            "source_line_spans": cipher_input.source_line_spans,
            "source_type": cipher_input.source_type,
            "format_hint": cipher_input.format_hint,
            "source_name": cipher_input.source_name,
            "language_hint": cipher_input.language_hint,
        },
        "prompt": prompt,
        "raw_response": raw_response,
        "classification": classification,
        "facts": facts,
        "validation": {
            "errors": errors,
            "warnings": warnings,
        },
        "artifacts": {
            "job_record": str(path),
        },
    }
    _write_record(path, record)
    return {"job_id": job_id, "path": str(path), "artifact_links": [{"label": "job_record", "path": str(path)}]}


def update_job_record(job, **updates):
    """Merge updates into an existing job record."""

    if not job:
        return None
    path = Path(job["path"] if isinstance(job, dict) else job)
    if not path.exists():
        return None
    record = _read_record(path)
    metadata = record.setdefault("metadata", {})
    if "draft" in updates:
        metadata["draft_sha256"] = _content_hash(updates["draft"])
    if "confirmation" in updates:
        updates["confirmation"].setdefault(
            "confirmed_at",
            datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        )
        metadata["confirmation_sha256"] = _content_hash(updates["confirmation"])
    if "manual_revision" in updates:
        updates["manual_revision"].setdefault(
            "revised_at",
            datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        )
        metadata["manual_revision_sha256"] = _content_hash(updates["manual_revision"])
    record.update(updates)
    record["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    _write_record(path, record)
    return {"job_id": record["job_id"], "path": str(path), "artifact_links": [{"label": "job_record", "path": str(path)}]}
