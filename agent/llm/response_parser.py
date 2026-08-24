"""Utility for parsing LLM JSON responses into UserIntent objects.

This module helps LLMProvider implementors handle common issues with LLM outputs
such as markdown code fences, trailing commas, and invalid JSON.
"""

import json
import re
from typing import Any, Dict, Optional

from agent.types import UserIntent, SkillRequest, SkillName


# Map string names to SkillName enum values
_SKILL_NAME_MAP = {s.value: s for s in SkillName}


def _repair_json(text: str) -> str:
    """Repair common LLM JSON quirks so a near-miss reply still parses:
      - trailing commas before } or ]
      - 0x hex integer literals: JSON is decimal-only, but LLMs naturally emit hex
        for cryptographic constants and test vectors (e.g. [0x298650c13199cdec]),
        which otherwise makes the whole facts reply unparseable.
    """
    text = re.sub(r",\s*([}\]])", r"\1", text)
    text = re.sub(r"\b0[xX][0-9a-fA-F]+\b", lambda m: str(int(m.group(0), 16)), text)
    return text


def parse_llm_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """Extract a JSON object from common LLM response formats.

    Handles common output quirks:
    - Strips markdown code fences (```json ... ```)
    - Extracts JSON from surrounding text
    - Removes trailing commas before ``}`` or ``]``
    """

    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # Strip markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try to find JSON object in the text
    brace_start = text.find("{")
    if brace_start == -1:
        return None

    # Find matching closing brace
    depth = 0
    brace_end = -1
    for i in range(brace_start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                brace_end = i
                break

    if brace_end == -1:
        return None

    json_str = text[brace_start:brace_end + 1]

    for candidate in (json_str, _repair_json(json_str)):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def parse_llm_json_response(raw: str) -> Optional[UserIntent]:
    """Parse a raw LLM response string into a UserIntent.

    Args:
        raw: Raw string from the LLM.

    Returns:
        UserIntent if parsing succeeds, None if the response is unparseable.
    """

    data = parse_llm_json_object(raw)
    if data is None:
        return None

    # Build UserIntent
    intent = UserIntent(raw_text=raw)

    if data.get("needs_clarification", False):
        intent.needs_clarification = True
        intent.clarification_prompt = data.get("clarification_prompt", "Could you please clarify your request?")
        return intent

    for req_data in data.get("requests", []):
        skill_str = req_data.get("skill", "")
        if skill_str not in _SKILL_NAME_MAP:
            continue
        skill = _SKILL_NAME_MAP[skill_str]
        params = req_data.get("params", {})
        intent.requests.append(SkillRequest(skill=skill, params=params))

    return intent
