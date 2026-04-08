"""Google Gemini-based LLMProvider implementation.

Usage:
    from agent import run_cli
    from agent.llm.gemini_provider import GeminiProvider

    provider = GeminiProvider(api_key="AIza...")
    # or with custom model:
    provider = GeminiProvider(api_key="AIza...", model="gemini-2.5-flash")

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


class GeminiProvider(LLMProvider):
    """LLMProvider implementation using Google Gemini API."""

    def __init__(self, api_key, model="gemini-2.5-flash"):
        """
        Args:
            api_key: Google AI API key.
            model: Model name (default: "gemini-2.5-flash").
        """
        try:
            from google import genai
        except ImportError:
            raise ImportError(
                "google-genai package is required. Install it with: pip install google-genai"
            )
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def parse_user_request(self, user_message, conversation_history, available_skills, session_context):
        prompt = build_parse_prompt(user_message, available_skills, session_context)
        response = self.client.models.generate_content(
            model=self.model,
            contents=f"{prompt}\n\nUser request: {user_message}",
            config={"temperature": 0},
        )
        intent = parse_llm_json_response(response.text)
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
        response = self.client.models.generate_content(
            model=self.model,
            contents=f"{prompt}\n\nPlease summarize the results.",
            config={"temperature": 0.3},
        )
        return response.text

    def handle_error(self, error, failed_request, session_context):
        return f"Error executing {failed_request.skill.value}: {error}"
