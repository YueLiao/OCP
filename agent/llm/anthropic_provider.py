"""Anthropic Claude-based LLMProvider implementation.

Usage:
    from agent import run_cli
    from agent.llm.anthropic_provider import AnthropicProvider

    provider = AnthropicProvider(api_key="sk-ant-xxx")
    # or with custom model:
    provider = AnthropicProvider(api_key="sk-ant-xxx", model="claude-sonnet-4-20250514")

    # CLI mode
    run_cli(provider)

    # API mode
    from agent import OCPAgent
    agent = OCPAgent(llm_provider=provider)
    agent.chat("Analyze SPECK32/64 with differential cryptanalysis")
"""

from typing import List

from agent.types import UserIntent, SkillRequest, SkillResult
from agent.llm.provider import LLMProvider
from agent.llm.prompt_templates import build_parse_prompt, build_response_prompt
from agent.llm.response_parser import parse_llm_json_response


class AnthropicProvider(LLMProvider):
    """LLMProvider implementation using Anthropic Claude API."""

    def __init__(self, api_key, model="claude-sonnet-4-20250514"):
        """
        Args:
            api_key: Anthropic API key.
            model: Model name (default: "claude-sonnet-4-20250514").
        """
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic package is required. Install it with: pip install anthropic")
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def parse_user_request(self, user_message, conversation_history, available_skills, session_context):
        prompt = build_parse_prompt(user_message, available_skills, session_context)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=0,
        )
        intent = parse_llm_json_response(response.content[0].text)
        if intent is None:
            return UserIntent(
                raw_text=user_message,
                needs_clarification=True,
                clarification_prompt="I couldn't parse your request. Could you please rephrase it?",
            )
        return intent

    def generate_response(self, results, original_intent, conversation_history, session_context):
        results_dicts = [
            {"skill": r.skill.value, "success": r.success, "summary": r.summary, "error": r.error}
            for r in results
        ]
        prompt = build_response_prompt(results_dicts, session_context)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=prompt,
            messages=[{"role": "user", "content": "Please summarize the results."}],
            temperature=0.3,
        )
        return response.content[0].text

    def handle_error(self, error, failed_request, session_context):
        return f"Error executing {failed_request.skill.value}: {error}"
