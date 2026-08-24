"""Stage-1 architecture classification: a cheap LLM pass labels the cipher's structural
archetype so the formalize prompt targets the right representation instead of a repeated SPN.
"""
import json

from agent.interfaces.api import OCPAgent
from agent.llm.provider import LLMProvider
from agent.llm.prompt_templates import (
    build_cipher_facts_extraction_prompt, _classification_directive, CIPHER_ARCHETYPES,
)
from agent.skills.cipher_text_input import CipherInput


class _Provider(LLMProvider):
    """Returns a classification for the stage-1 prompt and facts for the stage-2 prompt."""
    def __init__(self, classification=None):
        self._cls = classification

    def parse_user_request(self, *a, **k):
        return None

    def generate_response(self, *a, **k):
        return "done"

    def handle_error(self, error, *a, **k):
        return str(error)

    def call_llm(self, prompt, image_data=None):
        if "classifying the STRUCTURE" in prompt:
            return json.dumps(self._cls) if self._cls is not None else "not json"
        return '{"name": "X", "cipher_type": "blockcipher"}'


def _agent(classification):
    return OCPAgent(llm_provider=_Provider(classification))


class TestClassifyArchitecture:
    def test_returns_valid_classification(self):
        ci = CipherInput(raw_text="PRINCE reflection cipher", source_type="direct_text")
        cls = {"archetype": "reflection_spn", "cipher_type": "blockcipher",
               "confidence": 0.9, "reason": "forward+middle+backward"}
        got = _agent(cls).classify_cipher_architecture(ci)
        assert got["archetype"] == "reflection_spn"

    def test_unknown_archetype_rejected(self):
        ci = CipherInput(raw_text="something", source_type="direct_text")
        got = _agent({"archetype": "not_a_real_archetype"}).classify_cipher_architecture(ci)
        assert got is None

    def test_unparseable_classification_is_none(self):
        ci = CipherInput(raw_text="something", source_type="direct_text")
        got = _agent(None).classify_cipher_architecture(ci)  # provider returns "not json"
        assert got is None

    def test_no_llm_is_none(self):
        ci = CipherInput(raw_text="something", source_type="direct_text")
        assert OCPAgent().classify_cipher_architecture(ci) is None


class TestDirectiveInjection:
    def test_directive_present_for_each_archetype(self):
        ci = CipherInput(raw_text="x", source_type="direct_text")
        for arch in CIPHER_ARCHETYPES:
            p = build_cipher_facts_extraction_prompt(ci, {"archetype": arch, "reason": "r"})
            assert f"CLASSIFIED ARCHETYPE: {arch}" in p

    def test_reflection_directive_warns_against_flattening(self):
        d = _classification_directive({"archetype": "reflection_spn", "reason": "r"})
        assert "reflection" in d.lower() and "ambiguities" in d.lower()

    def test_no_classification_leaves_prompt_unchanged(self):
        ci = CipherInput(raw_text="x", source_type="direct_text")
        assert _classification_directive(None) == ""
        p = build_cipher_facts_extraction_prompt(ci, None)
        assert "CLASSIFIED ARCHETYPE" not in p

    def test_arx_directive_mentions_index_bound(self):
        d = _classification_directive({"archetype": "arx", "reason": "modadd+rot+xor"})
        assert "index < nbr_words" in d
