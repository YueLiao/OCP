import json

from agent import CipherSpec, LayerSpec, OCPAgent
from agent.llm.provider import LLMProvider
from agent.types import UserIntent


class FakeFactsProvider(LLMProvider):
    def parse_user_request(self, user_message, conversation_history, available_skills, session_context):
        return UserIntent(raw_text=user_message)

    def generate_response(self, results, original_intent, conversation_history, session_context):
        return "ok"

    def handle_error(self, error, failed_request, session_context):
        return str(error)

    def call_llm(self, prompt, image_data=None):
        self.prompt = prompt
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


def test_custom_cipher_definition_validates_missing_round_structure():
    agent = OCPAgent()
    spec = CipherSpec(name="Incomplete", round_structure=[])

    result = agent.define_custom_cipher(spec)

    assert not result.success
    assert "round_structure must have at least one layer" in result.error


def test_custom_cipher_definition_builds_tiny_arx_permutation():
    agent = OCPAgent()
    spec = CipherSpec(
        name="TinyARX",
        cipher_type="permutation",
        block_size=32,
        word_bitsize=16,
        nbr_words=2,
        nbr_rounds=2,
        round_structure=[
            LayerSpec("rotation", {"direction": "r", "amount": 7, "word_index": 0}),
            LayerSpec("modadd", {"input_indices": [[0, 1]], "output_indices": [0]}),
            LayerSpec("rotation", {"direction": "l", "amount": 2, "word_index": 1}),
            LayerSpec("xor", {"input_indices": [[0, 1]], "output_indices": [1]}),
        ],
    )

    result = agent.define_custom_cipher(spec)

    assert result.success
    assert result.data["cipher_name"] == "TinyARX_PERM"
    assert agent.session.get_cipher().name == "TinyARX_PERM"


def test_text_first_extraction_requires_llm_provider():
    agent = OCPAgent()

    result = agent.extract_cipher_facts("x <- y")

    assert not result.success
    assert "No LLM provider configured" in result.error


def test_text_first_extract_draft_and_confirm_builds_cipher(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))
    provider = FakeFactsProvider()
    agent = OCPAgent(llm_provider=provider)

    extraction = agent.extract_cipher_facts(
        r"x_0 \leftarrow (x_0 \ggg 7) \boxplus x_1",
        format_hint="latex",
    )
    draft = agent.draft_cipher_spec()
    result = agent.confirm_cipher_spec(draft)

    assert extraction.success
    assert "x_0  <-  (x_0  ROTR  7)  MODADD  x_1" in provider.prompt
    job_path = extraction.data["job"]["path"]
    job_record = json.loads(open(job_path, encoding="utf-8").read())
    assert job_record["input"]["normalized_text"] == "x_0  <-  (x_0  ROTR  7)  MODADD  x_1"
    assert job_record["facts"]["name"] == "TinyARX"
    assert draft.is_valid
    assert not draft.requires_user_confirmation
    assert result.success
    assert result.data["cipher_name"] == "TinyARX_PERM"
    assert result.data["artifact_links"][0]["path"] == job_path
    updated_record = json.loads(open(job_path, encoding="utf-8").read())
    assert updated_record["draft"]["spec"]["name"] == "TinyARX"
    assert updated_record["confirmation"]["confirmed"] is True


def test_confirm_cipher_spec_rejects_invalid_draft():
    agent = OCPAgent()
    draft = agent.draft_cipher_spec(
        {
            "name": "Broken",
            "primitive_type": "permutation",
            "state": {"block_size": 32, "word_bitsize": 16, "nbr_words": 2},
            "rounds": {"nbr_rounds": 2},
            "operations": [],
        }
    )

    result = agent.confirm_cipher_spec(draft)

    assert not result.success
    assert "validation errors" in result.error


def test_agent_exposes_solver_capabilities():
    capabilities = OCPAgent().solver_capabilities()

    assert capabilities["default"]["milp"] == "GUROBI"
    assert "GUROBI" in capabilities["milp"]
    assert "PySAT" in capabilities["sat"]


def test_agent_rejects_unimplemented_shacal2_512_variant():
    result = OCPAgent().instantiate_cipher(
        "shacal2",
        "blockcipher",
        version=512,
    )

    assert not result.success
    assert "Invalid version" in result.error
