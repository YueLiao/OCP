from io import BytesIO
from types import SimpleNamespace

import web.app as web_app

from agent.artifacts import normalize_artifact_links
from agent.interfaces.api import OCPAgent
from agent.llm.provider import LLMProvider
from agent.types import SkillName, SkillResult, UserIntent


class FakeFactsProvider(LLMProvider):
    def parse_user_request(self, user_message, conversation_history, available_skills, session_context):
        return UserIntent(raw_text=user_message)

    def generate_response(self, results, original_intent, conversation_history, session_context):
        return "ok"

    def handle_error(self, error, failed_request, session_context):
        return str(error)

    def call_llm(self, prompt, image_data=None):
        return """{
          "cipher_facts": {
            "name": "TinyARX",
            "primitive_type": "permutation",
            "state": {"block_size": 32, "word_bitsize": 16, "nbr_words": 2},
            "rounds": {"nbr_rounds": 2},
            "operations": [
              {"type": "rotation", "params": {"direction": "r", "amount": 7, "word_index": 0}},
              {"type": "modadd", "params": {"input_indices": [[0, 1]], "output_indices": [0]}},
              {"type": "rotation", "params": {"direction": "l", "amount": 2, "word_index": 1}},
              {"type": "xor", "params": {"input_indices": [[0, 1]], "output_indices": [1]}}
            ]
          }
        }"""


def setup_function():
    web_app.agent = None
    web_app.config = {"provider": None, "model": None, "connected": False}


def test_text_draft_requires_connected_agent():
    client = web_app.app.test_client()

    response = client.post("/api/text/draft", json={"text": "x <- y"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "Not connected. Configure provider first."


def test_json_endpoints_reject_missing_json_body():
    web_app.agent = OCPAgent(llm_provider=FakeFactsProvider())
    web_app.config = {"provider": "fake", "model": "fake", "connected": True}
    client = web_app.app.test_client()

    for path in ("/api/config", "/api/chat", "/api/text/draft"):
        response = client.post(path, data="not json", content_type="text/plain")

        assert response.status_code == 400
        assert response.get_json()["success"] is False
        assert response.get_json()["error"] == "JSON request body is required."
        assert response.get_json()["error_code"] == "invalid_json"


def test_config_returns_400_for_unknown_provider():
    client = web_app.app.test_client()

    response = client.post("/api/config", json={"provider": "missing-provider"})

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "Unknown provider" in response.get_json()["error"]


def test_config_resolves_api_key_from_provider_environment(monkeypatch):
    captured = {}

    class FakeProvider:
        pass

    def fake_create_llm_provider(provider_name, api_key=None, model=None, base_url=None):
        captured.update(
            {
                "provider_name": provider_name,
                "api_key": api_key,
                "model": model,
                "base_url": base_url,
            }
        )
        return FakeProvider()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-deepseek-key")
    monkeypatch.setattr(web_app, "create_llm_provider", fake_create_llm_provider)
    client = web_app.app.test_client()

    response = client.post("/api/config", json={"provider": "deepseek"})
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["config"] == {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "connected": True,
    }
    assert captured == {
        "provider_name": "deepseek",
        "api_key": "env-deepseek-key",
        "model": "",
        "base_url": None,
    }


def test_config_hides_unexpected_provider_setup_details(monkeypatch):
    def fake_create_llm_provider(provider_name, api_key=None, model=None, base_url=None):
        raise RuntimeError("internal secret detail")

    monkeypatch.setattr(web_app, "create_llm_provider", fake_create_llm_provider)
    client = web_app.app.test_client()

    response = client.post(
        "/api/config",
        json={"provider": "openai", "api_key": "test-key"},
    )
    data = response.get_json()

    assert response.status_code == 500
    assert data["success"] is False
    assert data["error_code"] == "provider_setup_failed"
    assert "internal secret detail" not in data["error"]


def test_chat_hides_unexpected_processing_details():
    class FailingAgent:
        session = SimpleNamespace(get_context=lambda: {"has_cipher": False})

        def chat(self, message):
            raise RuntimeError("provider secret detail")

    web_app.agent = FailingAgent()
    web_app.config = {"provider": "fake", "model": "fake", "connected": True}
    client = web_app.app.test_client()

    response = client.post("/api/chat", json={"message": "hello"})
    data = response.get_json()

    assert response.status_code == 500
    assert data["error_code"] == "chat_failed"
    assert "provider secret detail" not in data["error"]


def test_upload_response_includes_data_and_artifact_links():
    class FakeUploadAgent:
        session = SimpleNamespace(get_context=lambda: {"has_cipher": False})

        def extract_cipher_from_file(self, file_path, focus=None, auto_build=False):
            return SkillResult(
                success=True,
                skill=SkillName.CIPHER_EXTRACTION,
                data={
                    "artifact_links": [{"label": "extract_log", "path": file_path}],
                    "note": "ok",
                },
                summary="uploaded",
            )

    web_app.agent = FakeUploadAgent()
    web_app.config = {"provider": "fake", "model": "fake", "connected": True}
    client = web_app.app.test_client()

    response = client.post(
        "/api/upload",
        data={"file": (BytesIO(b"cipher text"), "cipher.txt")},
        content_type="multipart/form-data",
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["data"]["note"] == "ok"
    assert data["artifact_links"][0]["label"] == "extract_log"


def test_upload_hides_unexpected_processing_details():
    class FailingUploadAgent:
        session = SimpleNamespace(get_context=lambda: {"has_cipher": False})

        def extract_cipher_from_file(self, file_path, focus=None, auto_build=False):
            raise RuntimeError("file parser secret detail")

    web_app.agent = FailingUploadAgent()
    web_app.config = {"provider": "fake", "model": "fake", "connected": True}
    client = web_app.app.test_client()

    response = client.post(
        "/api/upload",
        data={"file": (BytesIO(b"cipher text"), "cipher.txt")},
        content_type="multipart/form-data",
    )
    data = response.get_json()

    assert response.status_code == 500
    assert data["error_code"] == "upload_failed"
    assert "file parser secret detail" not in data["error"]


def test_upload_cleanup_does_not_mask_response_when_temp_file_is_missing(monkeypatch):
    class FakeUploadAgent:
        session = SimpleNamespace(get_context=lambda: {"has_cipher": False})

        def extract_cipher_from_file(self, file_path, focus=None, auto_build=False):
            return SkillResult(success=True, skill=SkillName.CIPHER_EXTRACTION, summary="uploaded")

    original_unlink = web_app.os.unlink

    def remove_then_unlink(path):
        original_unlink(path)
        original_unlink(path)

    web_app.agent = FakeUploadAgent()
    web_app.config = {"provider": "fake", "model": "fake", "connected": True}
    monkeypatch.setattr(web_app.os, "unlink", remove_then_unlink)
    client = web_app.app.test_client()

    response = client.post(
        "/api/upload",
        data={"file": (BytesIO(b"cipher text"), "cipher.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_text_draft_and_confirm_builds_cipher(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    web_app.agent = OCPAgent(llm_provider=FakeFactsProvider())
    web_app.config = {"provider": "fake", "model": "fake", "connected": True}
    client = web_app.app.test_client()

    draft_response = client.post("/api/text/draft", json={"text": "tiny arx text"})
    draft_data = draft_response.get_json()
    confirm_response = client.post("/api/text/confirm")
    confirm_data = confirm_response.get_json()

    assert draft_response.status_code == 200
    assert draft_data["success"] is True
    assert draft_data["draft"]["is_valid"] is True
    assert draft_data["draft"]["spec"]["name"] == "TinyARX"
    assert draft_data["artifact_links"][0]["label"] == "job_record"
    assert confirm_response.status_code == 200
    assert confirm_data["success"] is True
    assert confirm_data["data"]["cipher_name"] == "TinyARX_PERM"
    assert confirm_data["artifact_links"][0]["path"] == draft_data["artifact_links"][0]["path"]


def test_text_draft_spec_endpoint_validates_manual_edits(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    web_app.agent = OCPAgent(llm_provider=FakeFactsProvider())
    web_app.config = {"provider": "fake", "model": "fake", "connected": True}
    client = web_app.app.test_client()

    draft_response = client.post("/api/text/draft", json={"text": "tiny arx text"})
    draft_data = draft_response.get_json()
    spec = draft_data["draft"]["spec"]
    spec["name"] = "TinyARXEdited"

    edit_response = client.post("/api/text/draft/spec", json={"spec": spec})
    edit_data = edit_response.get_json()
    invalid_response = client.post("/api/text/draft/spec", json={"spec": {"name": "Broken"}})
    invalid_data = invalid_response.get_json()

    assert edit_response.status_code == 200
    assert edit_data["success"] is True
    assert edit_data["draft"]["spec"]["name"] == "TinyARXEdited"
    assert edit_data["artifact_links"][0]["path"] == draft_data["artifact_links"][0]["path"]
    assert invalid_response.status_code == 400
    assert invalid_data["success"] is False
    assert invalid_data["draft"]["validation_errors"]


def test_workflow_endpoints_return_standard_skill_payloads(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    web_app.agent = OCPAgent()
    web_app.agent.instantiate_cipher("speck", "blockcipher", version=[32, 64], rounds=1)
    web_app.config = {"provider": "fake", "model": "fake", "connected": True}
    client = web_app.app.test_client()

    blocked_code_response = client.post("/api/code", json={"language": "python", "test": False})
    code_response = client.post("/api/code", json={"language": "python", "test": False, "confirmed": True})
    visualize_response = client.post("/api/visualize", json={"confirmed": True})
    unconfirmed_analysis_response = client.post("/api/analyze", json={"analysis_type": "unknown"})
    invalid_analysis_response = client.post("/api/analyze", json={"analysis_type": "unknown", "confirmed": True})
    solver_response = client.get("/api/solvers")

    blocked_code_data = blocked_code_response.get_json()
    code_data = code_response.get_json()
    visualize_data = visualize_response.get_json()
    unconfirmed_analysis_data = unconfirmed_analysis_response.get_json()
    invalid_analysis_data = invalid_analysis_response.get_json()
    solver_data = solver_response.get_json()

    assert blocked_code_response.status_code == 409
    assert blocked_code_data["error_code"] == "confirmation_required"
    assert code_response.status_code == 200
    assert code_data["success"] is True
    assert code_data["skill"] == "code_generation"
    assert code_data["artifact_links"][0]["label"] == "generated_code"
    assert code_data["artifacts"][0]["source_skill"] == "code_generation"
    assert visualize_response.status_code == 200
    assert visualize_data["skill"] == "visualization"
    assert visualize_data["artifact_links"][0]["label"] == "visualization"
    assert unconfirmed_analysis_response.status_code == 409
    assert unconfirmed_analysis_data["error_code"] == "confirmation_required"
    assert invalid_analysis_response.status_code == 400
    assert invalid_analysis_data["error_code"] == "invalid_analysis_type"
    assert solver_response.status_code == 200
    assert solver_data["capabilities"]["default"]["milp"] == "GUROBI"


def test_analysis_response_includes_solver_capabilities(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    web_app.agent = OCPAgent()
    web_app.agent.instantiate_cipher("speck", "blockcipher", version=[32, 64], rounds=1)
    web_app.config = {"provider": "fake", "model": "fake", "connected": True}

    def fake_differential_analysis(**params):
        return SkillResult(
            success=True,
            skill=SkillName.DIFFERENTIAL_ANALYSIS,
            data={"params": params},
            summary="analysis skipped",
        )

    monkeypatch.setattr(web_app.agent, "differential_analysis", fake_differential_analysis)
    client = web_app.app.test_client()

    response = client.post(
        "/api/analyze",
        json={
            "analysis_type": "differential",
            "objective_target": "EXISTENCE",
            "confirmed": True,
        },
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["solver_capabilities"]["default"]["milp"] == "GUROBI"
    assert "PySAT" in data["solver_capabilities"]["sat"]


def test_workflow_preflight_blocks_without_cipher():
    web_app.agent = OCPAgent()
    web_app.config = {"provider": "fake", "model": "fake", "connected": True}
    client = web_app.app.test_client()

    response = client.post("/api/code", json={"language": "python", "confirmed": True})
    data = response.get_json()

    assert response.status_code == 400
    assert data["error_code"] == "verification_failed"
    assert "No cipher is loaded" in data["verification"]["blocking_errors"][0]


def test_artifact_download_is_limited_to_session_registry(tmp_path):
    artifact_path = tmp_path / "trail.txt"
    artifact_path.write_text("trail-data", encoding="utf-8")
    artifacts = normalize_artifact_links(
        [{"label": "trail_text_1", "path": str(artifact_path)}],
        source_skill="differential_analysis",
    )

    web_app.agent = OCPAgent()
    web_app.agent.session.add_artifacts(artifacts)
    web_app.config = {"provider": "fake", "model": "fake", "connected": True}
    client = web_app.app.test_client()

    response = client.get(f"/api/artifacts/{artifacts[0]['id']}/download")
    missing_response = client.get("/api/artifacts/not-registered/download")

    assert response.status_code == 200
    assert response.data == b"trail-data"
    assert missing_response.status_code == 404
    assert missing_response.get_json()["error_code"] == "artifact_not_found"
