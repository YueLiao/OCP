from io import BytesIO
from types import SimpleNamespace

import web.app as web_app

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
        assert response.get_json() == {
            "success": False,
            "error": "JSON request body is required.",
        }


def test_config_returns_400_for_unknown_provider():
    client = web_app.app.test_client()

    response = client.post("/api/config", json={"provider": "missing-provider"})

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert "Unknown provider" in response.get_json()["error"]


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
