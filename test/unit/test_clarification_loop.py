"""P2 human-in-the-loop clarification loop: a build gap (a version's missing S-box) is surfaced
as a structured clarification, and the user's chat answer is applied + rebuilt.

Hermetic: the LLM is faked for the resolution step; the build/detection is real. A fixture
suppresses the CIPHER_DEFINITION auto-export so the tests never write primitives/.
"""

import json
import pytest

from agent.interfaces.api import OCPAgent
from agent.types import SkillName, SkillRequest


@pytest.fixture(autouse=True)
def _no_primitive_persist(monkeypatch):
    monkeypatch.setattr("agent.skills.cipher_definition._persist_primitive", lambda spec: None)


class _FakeLLM:
    def __init__(self, response):
        self._response = response

    def call_llm(self, prompt, **kwargs):
        return self._response


# a 2-version permutation family: "good" uses the built-in PRESENT_Sbox (builds + KAT-passes),
# "bad" references a missing S-box -> dropped -> clarification.
_PRESENT = [12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2]  # PRESENT(1)=5, PRESENT(2)=6


def _family_spec():
    return {
        "name": "Fam", "cipher_type": "permutation", "sbox_tables": {},
        "round_structure": [{"layer_type": "sbox", "params": {"sbox_name": "$sb", "index": [[0], [1]]}}],
        "test_vectors": [{"input": [1, 2], "output": [5, 6]}],
        "default_version": "good",
        "versions": {
            "good": {"block_size": 8, "word_bitsize": 4, "nbr_words": 2, "nbr_rounds": 1,
                     "params": {"sb": "PRESENT_Sbox"}},
            "bad": {"block_size": 8, "word_bitsize": 4, "nbr_words": 2, "nbr_rounds": 1,
                    "params": {"sb": "MissingBox_SSb"}},
        },
    }


def _build(agent, spec):
    return agent._core.execute_direct(SkillRequest(SkillName.CIPHER_DEFINITION, {"spec": spec}))


# --- detection + surfacing (real build) -------------------------------------

def test_build_surfaces_clarification_and_stores_pending():
    agent = OCPAgent()
    result = _build(agent, _family_spec())
    assert result.success
    clar = (result.data or {}).get("clarifications")
    assert clar and clar[0]["kind"] == "missing_sbox" and clar[0]["item"] == "MissingBox_SSb"
    assert clar[0]["version"] == "bad"
    # and it is stored on the session for the next turn to resolve
    pending = agent.pending_clarification()
    assert pending and pending["clarifications"][0]["item"] == "MissingBox_SSb"
    assert "MissingBox_SSb" in result.summary          # the ask appears in the chat summary


# --- resolution loop (faked LLM) --------------------------------------------

def _corrected_single_version():
    # a simple buildable, KAT-verified spec the "resolution" produces
    return {
        "name": "Fixed", "cipher_type": "permutation",
        "block_size": 8, "word_bitsize": 4, "nbr_words": 2, "nbr_rounds": 1,
        "round_structure": [{"layer_type": "permutation", "params": {"table": [0, 1]}}],
        "test_vectors": [[[1, 2], [1, 2]]],
    }


def test_resolve_clarification_rebuilds_and_clears_pending():
    agent = OCPAgent()
    _build(agent, _family_spec())                      # opens a clarification
    assert agent.pending_clarification() is not None

    agent._core.llm = _FakeLLM(json.dumps({"spec": _corrected_single_version()}))
    result = agent.resolve_clarification("use the built-in, it is stored already")
    assert result is not None and result.success
    assert agent.pending_clarification() is None        # gap resolved -> cleared


def test_not_a_resolution_falls_through_and_keeps_pending():
    agent = OCPAgent()
    _build(agent, _family_spec())
    before = agent.pending_clarification()
    assert before is not None

    agent._core.llm = _FakeLLM(json.dumps({"not_a_resolution": True}))
    assert agent.resolve_clarification("actually, run differential analysis instead") is None
    assert agent.pending_clarification() == before      # unchanged, still open


def test_resolve_returns_none_without_pending_or_llm():
    agent = OCPAgent()
    assert agent.resolve_clarification("anything") is None   # nothing pending


# --- detection also covers a WRONG-SIZE S-box (not just a missing one) -------

def test_detect_wrong_size_sbox_with_cipher_named_suggestions():
    from agent.skills.cipher_spec import CipherSpec, LayerSpec
    from agent.skills.cipher_definition import detect_clarifications
    # a version with 8-bit cells reusing the default's 4-bit Sb0 (16 entries, needs 256) -
    # exactly the Midori128 case; suggestions come from the cipher's own built-in family.
    spec = CipherSpec(
        name="Midori", cipher_type="blockcipher",
        word_bitsize=4, nbr_words=16, block_size=64, nbr_rounds=1,
        key_size=128, key_word_bitsize=4, key_nbr_words=32,
        sbox_tables={"Sb0": list(range(16))},
        round_structure=[LayerSpec("sbox", {"sbox_name": "Sb0", "index": [[i] for i in range(16)]})],
        versions={"M128": {"word_bitsize": 8, "nbr_words": 16, "block_size": 128, "nbr_rounds": 1,
                           "key_size": 128, "key_word_bitsize": 8, "key_nbr_words": 16, "params": {}}},
        default_version="M128",
    )
    cl = detect_clarifications(spec, {"M128": {"tested": False}})
    assert cl and cl[0].kind == "wrong_size_sbox" and cl[0].item == "Sb0" and cl[0].version == "M128"
    assert any("SSb" in s for s in cl[0].suggestions)      # Midori128_SSb0-3 offered


# --- process_message routes a pending clarification to resolution ------------

class _FakeParseLLM(_FakeLLM):
    # for process_message: also needs parse_user_request, but it should NOT be reached while a
    # clarification is pending and the message resolves it.
    def parse_user_request(self, **kwargs):
        raise AssertionError("parse_user_request must not run while resolving a clarification")


def test_process_message_resolves_pending_before_intent_parsing():
    agent = OCPAgent()
    _build(agent, _family_spec())
    agent._core.llm = _FakeParseLLM(json.dumps({"spec": _corrected_single_version()}))
    response = agent._core.process_message("use Midori128_SSb0-3")
    assert "Fixed" in response and agent.pending_clarification() is None
