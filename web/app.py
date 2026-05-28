"""OCP Agent - Web Chat Interface.

Usage:
    pip install flask
    cd /path/to/OCP
    python3 web/app.py

Then open http://localhost:5001 in your browser.
"""

import os
import sys
import tempfile
from contextlib import suppress

# Add parent directory to path so we can import agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, render_template, request, jsonify

from agent.agentic import requires_confirmation
from agent.interfaces.api import OCPAgent
from agent.llm.factory import create_llm_provider
from agent.llm.provider_config import default_model, get_provider_defaults
from agent.result_payload import skill_result_payload
from agent.verifier import verify_action
from solving.solving import solver_capabilities

app = Flask(__name__)

# Global state (single-user for simplicity)
agent = None
config = {"provider": None, "model": None, "connected": False}


def _draft_payload(draft):
    return {
        "spec": draft.spec,
        "validation_errors": draft.validation_errors,
        "warnings": draft.warnings,
        "assumptions": draft.assumptions,
        "clarification_questions": draft.clarification_questions,
        "requires_user_confirmation": draft.requires_user_confirmation,
        "is_valid": draft.is_valid,
    }


def _json_payload():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _error_response(message, status=400, code="request_error", **extra):
    payload = {"success": False, "error": message, "error_code": code}
    payload.update(extra)
    return jsonify(payload), status


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
    api_key = data.get("api_key", "")
    model = data.get("model", "")
    base_url = data.get("base_url", "")

    try:
        provider_defaults = get_provider_defaults(provider_name)
        if provider_defaults.requires_api_key and not api_key:
            return _error_response("API key is required.", 400, "missing_api_key")

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
    except Exception as e:
        return _error_response(str(e), 500, "provider_setup_failed")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Send a chat message to the agent."""
    global agent
    blocked = _require_agent()
    if blocked:
        return blocked

    data, error = _require_json()
    if error:
        return error
    message = data.get("message", "")
    if not message:
        return _error_response("Empty message.", 400, "empty_message")

    try:
        response = agent.chat(message)
        ctx = agent.session.get_context()
        return jsonify({
            "success": True,
            "response": response,
            "context": ctx,
        })
    except Exception as e:
        return _error_response(str(e), 500, "chat_failed")


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
    if not text.strip():
        return _error_response("Empty cipher text.", 400, "empty_cipher_text")

    result = agent.extract_cipher_facts(
        text,
        source_type=data.get("source_type", "direct_text"),
        format_hint=data.get("format_hint", "mixed"),
        source_name=data.get("source_name"),
        language_hint=data.get("language_hint", "unknown"),
    )
    if not result.success:
        return _skill_response(result, error_status=400)

    draft = agent.draft_cipher_spec()
    job = agent.session.get_metadata("pending_text_job")
    return _skill_response(
        result,
        extra={
            "draft": _draft_payload(draft),
            "job": job,
            "artifact_links": (job or {}).get("artifact_links", []),
        },
    )


@app.route("/api/text/confirm", methods=["POST"])
def confirm_text_cipher():
    """Confirm and build the pending text-first CipherSpec draft."""
    global agent
    blocked = _require_agent()
    if blocked:
        return blocked

    result = agent.confirm_cipher_spec()
    return _skill_response(result)


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

    verification_error = _verification_response("analyze", params)
    if verification_error:
        return verification_error

    if analysis_type == "differential":
        result = agent.differential_analysis(**params)
    else:
        result = agent.linear_analysis(**params)
    return _skill_response(result)


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
    result = agent.generate_code(**params)
    return _skill_response(result)


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
    result = agent.generate_visualization()
    return _skill_response(result)


@app.route("/api/solvers", methods=["GET"])
def solvers():
    """Report optional solver backend availability before running analysis."""
    return jsonify({"success": True, "capabilities": solver_capabilities()})


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
    except Exception as e:
        return _error_response(str(e), 500, "upload_failed")
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


@app.route("/api/status", methods=["GET"])
def status():
    """Get current agent status."""
    ctx = agent.session.get_context() if agent else {}
    trace = agent.session.get_trace() if agent else []
    artifacts = agent.session.get_artifacts() if agent else []
    return jsonify({
        "connected": config.get("connected", False),
        "config": config,
        "context": ctx,
        "trace": trace[-10:],
        "artifacts": artifacts,
    })


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    print(f"OCP Agent Web UI")
    print(f"Open http://localhost:{args.port} in your browser")
    app.run(host=args.host, port=args.port, debug=True)
