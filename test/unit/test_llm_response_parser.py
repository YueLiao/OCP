from agent.llm.response_parser import parse_llm_json_response
from agent.types import SkillName


def test_parse_llm_json_response_handles_fenced_json_and_trailing_commas():
    raw = """```json
    {
      "needs_clarification": false,
      "requests": [
        {
          "skill": "cipher_instantiation",
          "params": {"cipher_name": "speck", "cipher_type": "blockcipher",},
        },
      ],
    }
    ```"""

    intent = parse_llm_json_response(raw)

    assert intent is not None
    assert not intent.needs_clarification
    assert len(intent.requests) == 1
    assert intent.requests[0].skill is SkillName.CIPHER_INSTANTIATION
    assert intent.requests[0].params["cipher_name"] == "speck"


def test_parse_llm_json_response_handles_clarification():
    intent = parse_llm_json_response(
        '{"needs_clarification": true, "clarification_prompt": "Which cipher?", "requests": []}'
    )

    assert intent is not None
    assert intent.needs_clarification
    assert intent.clarification_prompt == "Which cipher?"


def test_parse_llm_json_response_ignores_unknown_skills():
    intent = parse_llm_json_response(
        '{"needs_clarification": false, "requests": [{"skill": "unknown", "params": {}}]}'
    )

    assert intent is not None
    assert intent.requests == []


def test_parse_llm_json_response_returns_none_for_invalid_text():
    assert parse_llm_json_response("not json") is None
