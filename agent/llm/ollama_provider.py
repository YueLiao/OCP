"""Ollama-based LLMProvider implementation for local models.

Usage:
    from agent import run_cli
    from agent.llm.ollama_provider import OllamaProvider

    provider = OllamaProvider()  # defaults to llama3, http://localhost:11434
    # or with custom model and host:
    provider = OllamaProvider(model="qwen2.5", host="http://localhost:11434")

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


class OllamaProvider(LLMProvider):
    """LLMProvider implementation using Ollama for local model inference.

    Requires Ollama running locally. Install from https://ollama.com
    Then pull a model: ollama pull llama3
    """

    def __init__(self, model="llama3", host="http://localhost:11434"):
        """
        Args:
            model: Ollama model name (default: "llama3").
            host: Ollama API host (default: "http://localhost:11434").
        """
        try:
            import ollama as _ollama
        except ImportError:
            raise ImportError("ollama package is required. Install it with: pip install ollama")
        self.client = _ollama.Client(host=host)
        self.model = model

    def parse_user_request(self, user_message, conversation_history, available_skills, session_context):
        prompt = build_parse_prompt(user_message, available_skills, session_context)
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
            options={"temperature": 0},
        )
        intent = parse_llm_json_response(response["message"]["content"])
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
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Please summarize the results."},
            ],
            options={"temperature": 0.3},
        )
        return response["message"]["content"]

    def handle_error(self, error, failed_request, session_context):
        return f"Error executing {failed_request.skill.value}: {error}"
