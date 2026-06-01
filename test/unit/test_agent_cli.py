from agent.interfaces.api import OCPAgent
from agent.interfaces.cli import _format_cli_error, _format_draft_review, _handle_text_draft
from agent.llm.provider import LLMProvider
from agent.skills.cipher_text_input import CipherFacts, build_cipher_spec_draft
from agent.types import UserIntent


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


def test_format_draft_review_includes_errors_and_warnings():
    facts = CipherFacts(
        name="Broken",
        primitive_type="permutation",
        state={"block_size": 32, "word_bitsize": 16, "nbr_words": 2},
        rounds={"nbr_rounds": 2},
        operations=[],
        ambiguities=["round order missing"],
    )
    draft = build_cipher_spec_draft(facts)

    review = _format_draft_review(draft)

    assert "CipherSpec draft:" in review
    assert "Validation errors:" in review
    assert "At least one round operation is required." in review
    assert "Ambiguity: round order missing" in review


def test_handle_text_draft_builds_after_confirmation(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    agent = OCPAgent(llm_provider=FakeFactsProvider())
    outputs = []

    result = _handle_text_draft(
        agent,
        "tiny arx text",
        input_func=lambda prompt: "yes",
        output_func=outputs.append,
    )

    assert result.success
    assert agent.session.get_cipher().name == "TinyARX_PERM"
    assert any("CipherSpec draft:" in output for output in outputs)
    assert "Built cipher: TinyARX_PERM" in outputs


def test_handle_text_draft_can_skip_build(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    agent = OCPAgent(llm_provider=FakeFactsProvider())
    outputs = []

    result = _handle_text_draft(
        agent,
        "tiny arx text",
        input_func=lambda prompt: "no",
        output_func=outputs.append,
    )

    assert result.success
    assert agent.session.get_cipher() is None
    assert "Draft saved in session metadata. Build skipped." in outputs


def test_format_cli_error_preserves_existing_message_shape():
    assert _format_cli_error(RuntimeError("boom")) == "\n[Error] boom\n"
