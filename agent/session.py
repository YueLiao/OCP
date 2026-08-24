from typing import Any, Dict, List, Optional


class Session:
    """Maintains conversation context and cipher state across interactions."""

    def __init__(self):
        self._cipher = None
        self._history = []  # list of {"role": str, "content": str}
        self._results = []
        self._metadata = {}
        self._trace = []
        self._artifacts = []

    def set_cipher(self, cipher):
        self._cipher = cipher

    def get_cipher(self):
        return self._cipher

    def add_message(self, role, content):
        self._history.append({"role": role, "content": content})

    def get_history(self):
        return list(self._history)

    def add_result(self, result):
        self._results.append(result)

    def get_results(self):
        return list(self._results)

    def add_trace(self, event, payload=None):
        self._trace.append({
            "step": len(self._trace) + 1,
            "event": event,
            "payload": payload or {},
        })

    def get_trace(self):
        return list(self._trace)

    def add_artifacts(self, artifacts):
        for artifact in artifacts or []:
            artifact_id = artifact.get("id") if isinstance(artifact, dict) else None
            if artifact_id is None:
                self._artifacts.append(artifact)
                continue
            self._artifacts = [
                existing
                for existing in self._artifacts
                if not (isinstance(existing, dict) and existing.get("id") == artifact_id)
            ]
            self._artifacts.append(artifact)

    def get_artifacts(self):
        return list(self._artifacts)

    def set_metadata(self, key, value):
        self._metadata[key] = value

    def get_metadata(self, key, default=None):
        return self._metadata.get(key, default)

    def get_context(self):
        """Return a summary dict for LLM prompt construction."""
        ctx = {
            "has_cipher": self._cipher is not None,
            "cipher_name": None,
            "cipher_type": None,
            "cipher_rounds": None,
            "recent_results": [],
            "trace_length": len(self._trace),
            "artifact_count": len(self._artifacts),
        }
        if self._cipher is not None:
            ctx["cipher_name"] = self._cipher.name
            cipher_cls = type(self._cipher).__bases__[0].__name__
            ctx["cipher_type"] = cipher_cls
            # Get rounds from the first function
            for fn in self._cipher.functions.values():
                ctx["cipher_rounds"] = fn.nbr_rounds
                break
        # Last 5 results summaries
        for r in self._results[-5:]:
            ctx["recent_results"].append({
                "skill": r.skill.value,
                "success": r.success,
                "summary": r.summary,
            })
        # Pre-set defaults from a UI control panel, if any. Surfaced so the LLM
        # can apply them to unspecified parameters and confirm on conflict.
        panel_settings = self._metadata.get("panel_settings")
        if panel_settings:
            ctx["panel_settings"] = panel_settings
        return ctx

    def reset(self):
        self._cipher = None
        self._history.clear()
        self._results.clear()
        self._metadata.clear()
        self._trace.clear()
        self._artifacts.clear()
