"""OCP Agent - Web Chat Interface.

Usage:
    pip install flask
    cd /path/to/OCP
    python3 web/app.py

Then open http://localhost:5001 in your browser.
"""

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout, suppress
from pathlib import Path

# matplotlib must use a non-GUI backend here: web requests run on worker threads,
# and the default macOS (GUI) backend can only be driven from the main thread.
os.environ.setdefault("MPLBACKEND", "Agg")


class _Tee:
    """Write to both a capture buffer and the real stream (so the terminal still shows progress)."""

    def __init__(self, buf, real):
        self._buf = buf
        self._real = real

    def write(self, s):
        self._buf.write(s)
        try:
            self._real.write(s)
            self._real.flush()
        except Exception:
            pass
        return len(s)

    def flush(self):
        try:
            self._real.flush()
        except Exception:
            pass


def _run_capturing(fn, *args, **kwargs):
    """Run a callable, capturing its output for the web console while still echoing to the terminal."""
    buf = io.StringIO()
    with redirect_stdout(_Tee(buf, sys.stdout)), redirect_stderr(_Tee(buf, sys.stderr)):
        result = fn(*args, **kwargs)
    return result, buf.getvalue()


def _code_spec(requests):
    """Build an equivalent-code spec {c,t,version,rounds,fn,params} from executed skill requests."""
    if not requests:
        return None
    fns = {"differential_analysis", "linear_analysis", "code_generation", "visualization"}
    inst = next((r for r in requests if r.get("skill") == "cipher_instantiation"), None)
    act = next((r for r in requests if r.get("skill") in fns), None)
    if inst is None or act is None:
        return None
    p = inst.get("params", {})
    return {
        "c": p.get("cipher_name"),
        "t": p.get("cipher_type", "blockcipher"),
        "version": p.get("version"),
        "rounds": p.get("rounds"),
        "fn": act.get("skill"),
        "params": act.get("params", {}),
    }

# Add parent directory to path so we can import agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, render_template, request, jsonify, send_file, g

from agent.agentic import requires_confirmation
from agent.interfaces.api import OCPAgent
from agent.llm.factory import create_llm_provider
from agent.llm.provider_config import api_key_error, default_model, get_provider_defaults, resolve_api_key
from agent.result_payload import skill_result_payload
from agent.verifier import verify_action
from solving.solving import solver_capabilities

app = Flask(__name__)

# Global state (single-user for simplicity)
agent = None
config = {"provider": None, "model": None, "connected": False}


def _draft_payload(draft):
    try:
        from agent.skills.cipher_readback import spec_readback
        readback = spec_readback(draft.spec) if draft.spec else ""
    except Exception:
        readback = ""
    return {
        "spec": draft.spec,
        "readback": readback,
        "validation_errors": draft.validation_errors,
        "warnings": draft.warnings,
        "assumptions": draft.assumptions,
        "clarification_questions": draft.clarification_questions,
        "requires_user_confirmation": draft.requires_user_confirmation,
        "is_valid": draft.is_valid,
        "repair_log": getattr(draft, "repair_log", []),
    }


def _json_payload():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _error_response(message, status=400, code="request_error", **extra):
    payload = {"success": False, "error": message, "error_code": code}
    payload.update(extra)
    return jsonify(payload), status


def _unexpected_error_response(message, code):
    """Return a sanitized HTTP 500 response for unexpected server-side failures."""

    return _error_response(message, 500, code)


def _require_agent():
    if agent is None:
        return _error_response(
            "Not connected. Configure provider first.",
            400,
            "not_connected",
        )
    return None


def _require_json():
    data = _json_payload()
    if data is None:
        return None, _error_response(
            "JSON request body is required.",
            400,
            "invalid_json",
        )
    return data, None


def _skill_response(result, *, success_status=200, error_status=400, extra=None):
    ctx = agent.session.get_context() if agent else {}
    payload = skill_result_payload(result, context=ctx, extra=extra)
    return jsonify(payload), success_status if result.success else error_status


def _require_confirmation(data, action):
    if requires_confirmation(action) and not data.get("confirmed"):
        return _error_response(
            f"Confirmation is required before running action: {action}.",
            409,
            "confirmation_required",
            action=action,
        )
    return None


def _verification_response(action, data):
    result = verify_action(action, agent.session, data)
    if result.ok:
        return None
    return _error_response(
        "Preflight verification failed.",
        400,
        "verification_failed",
        verification=result.to_dict(),
        context=agent.session.get_context(),
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/config", methods=["POST"])
def set_config():
    """Configure the LLM provider and create the agent."""
    global agent, config
    data = _json_payload()
    if data is None:
        return _error_response("JSON request body is required.", 400, "invalid_json")
    provider_name = data.get("provider", "openai")
    explicit_api_key = data.get("api_key", "")
    model = data.get("model", "")
    base_url = data.get("base_url", "")

    try:
        if provider_name in ("none", "direct", ""):
            agent = OCPAgent()
            config = {"provider": "none", "model": None, "connected": True}
            return jsonify({"success": True, "config": config})
        provider_defaults = get_provider_defaults(provider_name)
        api_key = resolve_api_key(provider_name, explicit_api_key, os.environ)
        if provider_defaults.requires_api_key and not api_key:
            return _error_response(api_key_error(provider_name), 400, "missing_api_key")

        provider = create_llm_provider(provider_name, api_key=api_key, model=model, base_url=base_url or None)
        agent = OCPAgent(llm_provider=provider)
        config = {
            "provider": provider_name,
            "model": model or default_model(provider_name),
            "connected": True,
        }
        return jsonify({"success": True, "config": config})
    except ValueError as e:
        return _error_response(str(e), 400, "invalid_provider_config")
    except Exception:
        return _unexpected_error_response(
            "Provider setup failed. Check provider settings and server logs.",
            "provider_setup_failed",
        )


@app.route("/api/chat", methods=["POST"])
def chat():
    """Send a chat message to the agent."""
    global agent
    blocked = _require_agent()
    if blocked:
        return blocked
    if config.get("provider") == "none":
        return _error_response(
            "Direct mode has no LLM connected. Use the control panel, or switch to chat mode in settings.",
            400,
            "no_llm",
        )

    data, error = _require_json()
    if error:
        return error
    message = data.get("message", "")
    if not message:
        return _error_response("Empty message.", 400, "empty_message")

    # Optional control-panel defaults to apply during this chat turn. Stored on
    # the session so they flow into the LLM prompt via get_context(); cleared
    # when the toggle is off so stale settings never linger.
    panel_settings = data.get("panel_settings")
    agent.session.set_metadata(
        "panel_settings",
        panel_settings if isinstance(panel_settings, dict) and panel_settings else None,
    )

    try:
        before_ids = {a.get("id") for a in agent.session.get_artifacts() if isinstance(a, dict)}
        response, console = _run_capturing(agent.chat, message)
        ctx = agent.session.get_context()
        new_artifacts = [
            a for a in agent.session.get_artifacts()
            if isinstance(a, dict) and a.get("id") not in before_ids
        ]
        code_spec = _code_spec(agent.session.get_metadata("last_requests"))
        return jsonify({
            "success": True,
            "response": response,
            "context": ctx,
            "console": console,
            "artifacts": new_artifacts,
            "code_spec": code_spec,
        })
    except Exception:
        return _unexpected_error_response(
            "Chat processing failed. Check provider settings and server logs.",
            "chat_failed",
        )


def _read_files_dir_text(filename):
    """Read a text file the user named in chat: resolve a bare name against the
    files/ folder, allow absolute paths. Returns (text, error_response). Text
    files only - PDFs/images must go through the upload button."""
    from tools.paths import get_files_dir

    path = os.path.expanduser(filename)
    if not os.path.isabs(path) and not os.path.exists(path):
        candidate = get_files_dir() / filename
        if candidate.exists():
            path = str(candidate)
    if not os.path.exists(path):
        return None, _error_response(
            f"File not found: {filename}. Put it in the files/ folder and give its name, or use the upload button.",
            400, "file_not_found")
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".md", ".tex", ".txt", ".rst"):
        return None, _error_response(
            "Naming a file works for text (.md/.tex/.txt). For PDF or images, use the upload button.",
            400, "unsupported_file")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read(), None
    except OSError as exc:
        return None, _error_response(f"Could not read {filename}: {exc}", 400, "file_read_error")


@app.route("/api/text/draft", methods=["POST"])
def draft_text_cipher():
    """Extract text-first cipher facts and return a reviewable draft."""
    global agent
    blocked = _require_agent()
    if blocked:
        return blocked

    data, error = _require_json()
    if error:
        return error
    text = data.get("text", "")
    filename = (data.get("filename") or "").strip()
    if filename and not text.strip():
        text, file_error = _read_files_dir_text(filename)
        if file_error:
            return file_error
        data.setdefault("source_name", os.path.basename(filename))
    if not text.strip():
        return _error_response("Empty cipher text.", 400, "empty_cipher_text")

    # Deterministic pre-flight: block clearly-insufficient input before spending
    # any LLM tokens; otherwise collect non-blocking accuracy nudges.
    from agent.skills.cipher_text_input import lint_cipher_text
    blocking, input_warnings = lint_cipher_text(text)
    if blocking:
        return _error_response(input_warnings[0], 400, "insufficient_cipher_text")

    try:
        result = agent.extract_cipher_facts(
            text,
            source_type=data.get("source_type", "direct_text"),
            format_hint=data.get("format_hint", "mixed"),
            source_name=data.get("source_name"),
            language_hint=data.get("language_hint", "unknown"),
        )
        facts_extracted = isinstance(result.data, dict) and result.data.get("facts") is not None
        if not result.success and not facts_extracted:
            # Genuine failure (no LLM, unparseable response, no facts) - hard error.
            return _skill_response(result, error_status=400)
        # Stage-1 architecture classification (may be None if it failed / no LLM).
        classification = result.data.get("classification") if isinstance(result.data, dict) else None

        # Facts were extracted; draft (with the LLM auto-repair loop already run). The draft
        # payload carries repair_log so the UI can show each build attempt and what it fixed.
        draft = agent.draft_cipher_spec()
        job = agent.session.get_metadata("pending_text_job")
        # Auto-build without a manual confirmation step: when the auto-repaired draft is valid,
        # build + verify + persist it right away and return the result. (When it is NOT valid
        # after the repair loop, we return the draft + its remaining issues instead of building.)
        build_result = None
        if getattr(draft, "is_valid", False):
            try:
                r = agent.confirm_cipher_spec(version=data.get("version"),
                                              rounds=data.get("rounds") or None)
                build_result = {
                    "success": bool(getattr(r, "success", False)),
                    "summary": getattr(r, "summary", None),
                    "data": getattr(r, "data", None) if getattr(r, "success", False) else None,
                    "error": getattr(r, "error", None),
                }
            except Exception as exc:  # never let an auto-build crash the draft response
                build_result = {"success": False, "error": str(exc)}
        return jsonify(
            {
                "success": True,
                "draft": _draft_payload(draft),
                "classification": classification,
                "build": build_result,
                "job": job,
                "artifact_links": (job or {}).get("artifact_links", []),
                "input_warnings": input_warnings,
                "context": agent.session.get_context(),
            },
        )
    except ValueError as exc:
        return _error_response(str(exc), 400, "invalid_text_draft")
    except Exception:
        return _unexpected_error_response(
            "Text draft processing failed. Check provider settings and server logs.",
            "text_draft_failed",
        )


@app.route("/api/text/confirm", methods=["POST"])
def confirm_text_cipher():
    """Confirm and build the pending text-first CipherSpec draft."""
    global agent
    blocked = _require_agent()
    if blocked:
        return blocked

    data = _json_payload() or {}
    blocked = _require_confirmation(data, "confirm_cipher_spec")
    if blocked:
        return blocked

    # Round count / version are user choices from the control panel; a blank round
    # count builds the design's full rounds (the version default).
    version = data.get("version")
    rounds = data.get("rounds")
    result = agent.confirm_cipher_spec(version=version, rounds=rounds or None)
    return _skill_response(result)


@app.route("/api/text/draft/spec", methods=["POST"])
def revise_text_cipher_draft():
    """Validate and store a manually edited text-first CipherSpec draft."""
    global agent
    blocked = _require_agent()
    if blocked:
        return blocked

    data, error = _require_json()
    if error:
        return error
    spec = data.get("spec")
    if not isinstance(spec, dict):
        return _error_response("spec must be a JSON object.", 400, "invalid_spec")

    try:
        draft = agent.revise_cipher_spec_draft(spec)
    except ValueError as exc:
        return _error_response(str(exc), 400, "invalid_spec")

    # Auto-build a valid manual edit too (the escape hatch: paste a corrected spec and it builds
    # without a separate confirm step), mirroring the draft endpoint.
    build_result = None
    if getattr(draft, "is_valid", False):
        try:
            r = agent.confirm_cipher_spec(version=data.get("version"),
                                          rounds=data.get("rounds") or None)
            build_result = {
                "success": bool(getattr(r, "success", False)),
                "summary": getattr(r, "summary", None),
                "data": getattr(r, "data", None) if getattr(r, "success", False) else None,
                "error": getattr(r, "error", None),
            }
        except Exception as exc:
            build_result = {"success": False, "error": str(exc)}

    job = agent.session.get_metadata("pending_text_job")
    status = 200 if draft.is_valid else 400
    return jsonify(
        {
            "success": draft.is_valid,
            "draft": _draft_payload(draft),
            "build": build_result,
            "job": job,
            "artifact_links": (job or {}).get("artifact_links", []),
            "context": agent.session.get_context(),
        }
    ), status


@app.route("/api/text/draft/testvectors", methods=["POST"])
def add_text_test_vectors():
    """Inject test vectors into the pending draft: pasted JSON, or a JSON file in
    files/ (e.g. knot_test_vectors.json). Re-validates so Build can verify."""
    global agent
    blocked = _require_agent()
    if blocked:
        return blocked
    data, error = _require_json()
    if error:
        return error

    text = (data.get("text") or "").strip()
    filename = (data.get("filename") or "").strip()
    # Tolerate a filename pasted into the JSON box: a lone token ending in .json that
    # isn't JSON content is clearly a filename, so treat it as one.
    if text and not filename and "\n" not in text and not text.startswith(("{", "[")) \
            and text.lower().endswith(".json"):
        filename, text = text, ""
    raw = None
    if filename:
        from tools.paths import get_files_dir
        path = os.path.expanduser(filename)
        if not os.path.isabs(path) and not os.path.exists(path):
            candidate = get_files_dir() / filename
            if candidate.exists():
                path = str(candidate)
        if not os.path.exists(path):
            return _error_response(
                f"File not found: {filename}. Put it in the files/ folder and give its name.",
                400, "file_not_found")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw = handle.read()
        except OSError as exc:
            return _error_response(f"Could not read {filename}: {exc}", 400, "file_error")
    elif text:
        raw = text
    else:
        return _error_response(
            "Provide test vectors: paste the JSON, or name a JSON file in files/.",
            400, "no_test_vectors_input")

    try:
        tv_data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        hint = ""
        if raw and not raw.lstrip().startswith(("{", "[")):
            hint = (" - this doesn't look like JSON. If it's a file name, put it in the "
                    "file-name box instead of the paste box.")
        return _error_response(
            f"Could not parse test vectors as JSON: {exc}{hint}", 400, "invalid_test_vectors")

    try:
        draft = agent.add_test_vectors_to_draft(tv_data)
    except ValueError as exc:
        return _error_response(str(exc), 400, "no_pending_draft")

    job = agent.session.get_metadata("pending_text_job")
    status = 200 if draft.is_valid else 400
    return jsonify({
        "success": draft.is_valid,
        "draft": _draft_payload(draft),
        "job": job,
        "context": agent.session.get_context(),
    }), status


@app.route("/api/text/repair", methods=["POST"])
def repair_text_cipher():
    """Targeted LLM fix of a CipherSpec given specific problems (not a re-extraction)."""
    global agent
    blocked = _require_agent()
    if blocked:
        return blocked
    if config.get("provider") == "none":
        return _error_response(
            "AI repair needs a connected LLM. Edit the JSON manually, or connect a provider.",
            400,
            "no_llm",
        )

    data, error = _require_json()
    if error:
        return error
    spec = data.get("spec")
    problems = data.get("problems") or []
    if not isinstance(spec, dict):
        return _error_response("spec must be a JSON object.", 400, "invalid_spec")

    try:
        corrected = agent.repair_cipher_spec(spec, problems)
        draft = agent.revise_cipher_spec_draft(corrected)
    except ValueError as exc:
        return _error_response(str(exc), 400, "repair_failed")
    except Exception:
        return _unexpected_error_response(
            "AI repair failed. Check provider settings and server logs.",
            "repair_failed",
        )

    job = agent.session.get_metadata("pending_text_job")
    return jsonify(
        {
            "success": True,
            "draft": _draft_payload(draft),
            "job": job,
            "context": agent.session.get_context(),
        }
    )


@app.route("/api/analyze", methods=["POST"])
def run_analysis():
    """Run a confirmed differential or linear analysis workflow."""
    blocked = _require_agent()
    if blocked:
        return blocked
    data, error = _require_json()
    if error:
        return error
    confirmation_error = _require_confirmation(data, "analyze")
    if confirmation_error:
        return confirmation_error

    analysis_type = data.get("analysis_type", "differential")
    if analysis_type not in {"differential", "linear"}:
        return _error_response("analysis_type must be 'differential' or 'linear'.", 400, "invalid_analysis_type")
    model_type = data.get("model_type", "milp")
    goal = data.get("goal")
    params = {
        "model_type": model_type,
        "constraints": data.get("constraints") or None,
        "objective_target": data.get("objective_target", "OPTIMAL"),
        "show_mode": data.get("show_mode", 0),
    }
    if goal:
        params["goal"] = goal
    if "solver" in data:
        params["solver"] = data["solver"]
    if "solution_number" in data:
        params["solution_number"] = data["solution_number"]
    for opt in ("input_diff", "output_diff", "input_mask", "output_mask"):
        if data.get(opt):
            params[opt] = data[opt]

    verification_error = _verification_response("analyze", params)
    if verification_error:
        return verification_error

    analysis_fn = agent.differential_analysis if analysis_type == "differential" else agent.linear_analysis
    result, console = _run_capturing(analysis_fn, **params)
    return _skill_response(result, extra={"solver_capabilities": agent.solver_capabilities(), "console": console})


@app.route("/api/code", methods=["POST"])
def generate_code():
    """Generate implementation code for the current cipher."""
    blocked = _require_agent()
    if blocked:
        return blocked
    data, error = _require_json()
    if error:
        return error
    confirmation_error = _require_confirmation(data, "code")
    if confirmation_error:
        return confirmation_error

    params = {
        "language": data.get("language", "python"),
        "unroll": bool(data.get("unroll", False)),
        "test": bool(data.get("test", True)),
    }
    verification_error = _verification_response("code", params)
    if verification_error:
        return verification_error
    result, console = _run_capturing(agent.generate_code, **params)
    return _skill_response(result, extra={"console": console})


@app.route("/api/visualize", methods=["POST"])
def generate_visualization():
    """Generate a visualization PDF for the current cipher."""
    blocked = _require_agent()
    if blocked:
        return blocked
    data = _json_payload() or {}
    confirmation_error = _require_confirmation(data, "visualize")
    if confirmation_error:
        return confirmation_error
    verification_error = _verification_response("visualize", data)
    if verification_error:
        return verification_error
    result, console = _run_capturing(agent.generate_visualization)
    return _skill_response(result, extra={"console": console})


@app.route("/api/solvers", methods=["GET"])
def solvers():
    """Report optional solver backend availability before running analysis."""
    return jsonify({"success": True, "capabilities": solver_capabilities()})


@app.route("/api/schema", methods=["GET"])
def schema():
    """Expose the machine-readable catalog + skill param schemas for the control panel."""
    from agent.skills.cipher_instantiation import CIPHER_CATALOG
    from agent.skills import create_default_registry

    ciphers = {}
    for name, entry in CIPHER_CATALOG.items():
        ciphers[name] = {
            "types": list(entry.get("factories", {}).keys()),
            "default_version": entry.get("default_version", {}),
            "valid_versions": entry.get("valid_versions", {}),
            "module": entry.get("module", ""),
            "factories": entry.get("factories", {}),
        }
    registry = create_default_registry()
    skills = {d["name"]: d for d in registry.list_descriptors()}
    return jsonify({
        "success": True,
        "ciphers": ciphers,
        "skills": skills,
        "solvers": solver_capabilities(),
    })


_DEFAULT_ROUNDS_CACHE = {}


@app.route("/api/default_rounds", methods=["POST"])
def default_rounds_endpoint():
    """Resolve a cipher's own default (full) round count for a given version.

    Lets the control panel show and use each cipher's default rounds when the
    Rounds field is left blank, instead of guessing 1. Side-effect free: it
    builds the factory directly and never touches the session. Cached per
    (cipher, type, version).
    """
    data = _json_payload() or {}
    cipher = (data.get("cipher_name") or data.get("cipher") or "").lower()
    ctype = (data.get("cipher_type") or data.get("type") or "").lower()
    version = data.get("version")
    from agent.skills.cipher_instantiation import CIPHER_CATALOG

    entry = CIPHER_CATALOG.get(cipher)
    if not entry or ctype not in entry.get("factories", {}):
        return jsonify({"success": True, "rounds": None})
    key = (cipher, ctype, str(version))
    if key not in _DEFAULT_ROUNDS_CACHE:
        rounds = None
        try:
            import importlib
            import warnings

            mod = importlib.import_module(entry["module"])
            factory_fn = getattr(mod, entry["factories"][ctype])
            kwargs = {}
            if version is not None:
                kwargs["version"] = version
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                cipher_obj = factory_fn(**kwargs)
            for fn in cipher_obj.functions.values():
                rounds = fn.nbr_rounds
                break
        except Exception:
            rounds = None
        _DEFAULT_ROUNDS_CACHE[key] = rounds
    return jsonify({"success": True, "rounds": _DEFAULT_ROUNDS_CACHE[key]})


@app.route("/api/instantiate", methods=["POST"])
def instantiate_cipher_endpoint():
    """Instantiate a built-in cipher without the LLM (control-panel / direct mode)."""
    blocked = _require_agent()
    if blocked:
        return blocked
    data, error = _require_json()
    if error:
        return error
    cipher_name = data.get("cipher_name")
    if not cipher_name:
        return _error_response("cipher_name is required.", 400, "missing_cipher_name")
    kwargs = {"cipher_name": cipher_name, "cipher_type": data.get("cipher_type", "blockcipher")}
    if data.get("version") is not None:
        kwargs["version"] = data["version"]
    if data.get("rounds") is not None:
        kwargs["rounds"] = data["rounds"]
    result = agent.instantiate_cipher(**kwargs)
    return _skill_response(result)


@app.route("/api/verify", methods=["POST"])
def verify_endpoint():
    """Dry-run capability check so the panel can gate the run button before execution."""
    blocked = _require_agent()
    if blocked:
        return blocked
    data = _json_payload() or {}
    action = data.get("action", "analyze")
    params = data.get("params") or {}
    result = verify_action(action, agent.session, params)
    return jsonify({
        "success": True,
        "verification": result.to_dict(),
        "context": agent.session.get_context(),
    })


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Upload a text/PDF/image file for cipher extraction."""
    global agent
    blocked = _require_agent()
    if blocked:
        return blocked

    if "file" not in request.files:
        return _error_response("No file uploaded.", 400, "missing_upload")

    f = request.files["file"]
    focus = request.form.get("focus", "")

    # Save to temp file
    suffix = os.path.splitext(f.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        result = agent.extract_cipher_from_file(tmp_path, focus=focus or None, auto_build=False)
        return _skill_response(result)
    except ValueError as exc:
        return _error_response(str(exc), 400, "invalid_upload")
    except Exception:
        return _unexpected_error_response(
            "File upload processing failed. Check the file and server logs.",
            "upload_failed",
        )
    finally:
        with suppress(FileNotFoundError):
            os.unlink(tmp_path)


@app.route("/api/reset", methods=["POST"])
def reset():
    """Reset the agent session."""
    global agent
    if agent is not None:
        agent.session.reset()
    return jsonify({"success": True})


@app.route("/api/stop", methods=["POST"])
def stop():
    """Cancel in-progress multi-step LLM work (the draft auto-repair loop). The Stop button
    calls this alongside aborting its fetch, so no more tokens are spent between LLM calls.
    A single in-flight LLM call cannot be interrupted; this stops the loop from continuing."""
    global agent
    if agent is not None:
        agent.request_cancel()
    return jsonify({"success": True})


def _current_provider():
    """The active LLM provider (for token counters), or None."""
    if agent is None:
        return None
    return getattr(agent, "llm", None) or getattr(getattr(agent, "_core", None), "llm", None)


@app.before_request
def _record_tokens_before():
    provider = _current_provider()
    g.tokens_before = getattr(provider, "total_tokens", 0) if provider else 0


@app.after_request
def _inject_request_tokens(response):
    """Annotate every JSON response with request_tokens = tokens this request spent."""
    try:
        provider = _current_provider()
        if provider is not None and response.is_json:
            delta = getattr(provider, "total_tokens", 0) - getattr(g, "tokens_before", 0)
            data = response.get_json(silent=True)
            if isinstance(data, dict):
                data["request_tokens"] = max(0, delta)
                response.set_data(json.dumps(data))
    except Exception:
        pass
    return response


@app.route("/api/status", methods=["GET"])
def status():
    """Get current agent status."""
    ctx = agent.session.get_context() if agent else {}
    trace = agent.session.get_trace() if agent else []
    artifacts = agent.session.get_artifacts() if agent else []
    provider = _current_provider()
    token_usage = ({"total": getattr(provider, "total_tokens", 0),
                    "last": getattr(provider, "last_tokens", 0)} if provider else None)
    return jsonify({
        "connected": config.get("connected", False),
        "config": config,
        "context": ctx,
        "trace": trace[-10:],
        "artifacts": artifacts,
        "token_usage": token_usage,
    })


@app.route("/api/artifacts/<artifact_id>/download", methods=["GET"])
def download_artifact(artifact_id):
    """Download an artifact that was registered in the current session."""
    artifacts = agent.session.get_artifacts() if agent else []
    artifact = next((item for item in artifacts if str(item.get("id")) == artifact_id), None)
    if artifact is None:
        return _error_response("Artifact not found.", 404, "artifact_not_found")

    artifact_path = Path(str(artifact.get("path") or ""))
    if not artifact_path.is_file():
        return _error_response("Artifact file is missing.", 404, "artifact_missing")

    return send_file(artifact_path, as_attachment=True, download_name=artifact_path.name)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    print(f"OCP Agent Web UI")
    print(f"Open http://localhost:{args.port} in your browser")
    # use_reloader=False: code generation writes .py files into files/, which the
    # Flask stat-reloader would otherwise treat as a change and restart the server,
    # wiping the in-memory session/connection (forcing a reconnect).
    # threaded=True so /api/stop can run while a draft request is still inside the
    # auto-repair loop (the Stop button relies on that concurrency to cancel it).
    app.run(host=args.host, port=args.port, debug=True, use_reloader=False, threaded=True)
