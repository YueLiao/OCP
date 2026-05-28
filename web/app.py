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

# Add parent directory to path so we can import agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, render_template, request, jsonify

from agent.interfaces.api import OCPAgent
from agent.llm.factory import create_llm_provider
from agent.llm.provider_config import default_model, get_provider_defaults

app = Flask(__name__)

# Global state (single-user for simplicity)
agent = None
config = {"provider": None, "model": None, "connected": False}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/config", methods=["POST"])
def set_config():
    """Configure the LLM provider and create the agent."""
    global agent, config
    data = request.json
    provider_name = data.get("provider", "openai")
    api_key = data.get("api_key", "")
    model = data.get("model", "")
    base_url = data.get("base_url", "")

    try:
        provider_defaults = get_provider_defaults(provider_name)
        if provider_defaults.requires_api_key and not api_key:
            return jsonify({"success": False, "error": "API key is required."}), 400

        provider = create_llm_provider(provider_name, api_key=api_key, model=model, base_url=base_url or None)
        agent = OCPAgent(llm_provider=provider)
        config = {
            "provider": provider_name,
            "model": model or default_model(provider_name),
            "connected": True,
        }
        return jsonify({"success": True, "config": config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """Send a chat message to the agent."""
    global agent
    if agent is None:
        return jsonify({"success": False, "error": "Not connected. Configure provider first."}), 400

    data = request.json
    message = data.get("message", "")
    if not message:
        return jsonify({"success": False, "error": "Empty message."}), 400

    try:
        response = agent.chat(message)
        ctx = agent.session.get_context()
        return jsonify({
            "success": True,
            "response": response,
            "context": ctx,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Upload a text/PDF/image file for cipher extraction."""
    global agent
    if agent is None:
        return jsonify({"success": False, "error": "Not connected. Configure provider first."}), 400

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    f = request.files["file"]
    focus = request.form.get("focus", "")

    # Save to temp file
    suffix = os.path.splitext(f.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        result = agent.extract_cipher_from_file(tmp_path, focus=focus or None, auto_build=True)
        ctx = agent.session.get_context()
        return jsonify({
            "success": result.success,
            "summary": result.summary,
            "error": result.error,
            "context": ctx,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
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
    return jsonify({"connected": config.get("connected", False), "config": config, "context": ctx})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()
    print(f"OCP Agent Web UI")
    print(f"Open http://localhost:{args.port} in your browser")
    app.run(host=args.host, port=args.port, debug=True)
