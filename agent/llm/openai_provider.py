"""OpenAI-based LLMProvider implementation.

Usage:
    from agent import run_cli
    from agent.llm.openai_provider import OpenAIProvider

    provider = OpenAIProvider(api_key="sk-xxx")
    # or with custom model:
    provider = OpenAIProvider(api_key="sk-xxx", model="gpt-4o")

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


class OpenAIProvider(LLMProvider):
    """LLMProvider implementation using OpenAI API (GPT-4, GPT-4o, etc.)."""

    def __init__(self, api_key, model="gpt-4o", base_url=None):
        """
        Args:
            api_key: OpenAI API key.
            model: Model name (default: "gpt-4o").
            base_url: Optional custom API base URL (for Azure, proxies, etc.).
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package is required. Install it with: pip install openai")
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model

    def parse_user_request(self, user_message, conversation_history, available_skills, session_context):
        prompt = build_parse_prompt(user_message, available_skills, session_context)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
        )
        intent = parse_llm_json_response(response.choices[0].message.content)
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
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content

    def handle_error(self, error, failed_request, session_context):
        return f"Error executing {failed_request.skill.value}: {error}"

    def call_llm(self, prompt, image_data=None):
        if image_data:
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:{image_data['mime_type']};base64,{image_data['base64']}"
                }},
            ]
        else:
            content = prompt
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            temperature=0,
        )
        return response.choices[0].message.content
