"""Utility for parsing LLM JSON responses into UserIntent objects.

This module helps LLMProvider implementors handle common issues with LLM outputs
such as markdown code fences, trailing commas, and invalid JSON.
"""

import json
import re
from typing import Optional

from agent.types import UserIntent, SkillRequest, SkillName


# Map string names to SkillName enum values
_SKILL_NAME_MAP = {s.value: s for s in SkillName}


def parse_llm_json_response(raw: str) -> Optional[UserIntent]:
    """Parse a raw LLM response string into a UserIntent.

    Handles common LLM output quirks:
    - Strips markdown code fences (```json ... ```)
    - Extracts JSON from surrounding text
    - Validates skill names and required fields

    Args:
        raw: Raw string from the LLM.

    Returns:
        UserIntent if parsing succeeds, None if the response is unparseable.
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

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # Try fixing trailing commas
        fixed = re.sub(r",\s*([}\]])", r"\1", json_str)
        try:
            data = json.loads(fixed)
        except json.JSONDecodeError:
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
