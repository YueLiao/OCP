"""OpenAI-compatible provider presets.

Many hosted and local LLM APIs expose the OpenAI chat-completions protocol.
This module keeps those endpoints explicit without duplicating the OpenAI
provider implementation.
"""

from agent.llm.openai_provider import OpenAIProvider
from agent.llm.provider_config import default_base_url, default_model


class OpenAICompatibleProvider(OpenAIProvider):
    """LLM provider for OpenAI-compatible chat-completions endpoints."""

    def __init__(self, api_key, model=None, base_url=None, provider_name="openai-compatible"):
        """
        Args:
            api_key: API key for the compatible endpoint.
            model: Model name accepted by the endpoint.
            base_url: Endpoint base URL, for example ``http://localhost:8000/v1``.
            provider_name: Provider key used for defaults.
        """
        resolved_base_url = base_url or default_base_url(provider_name)
        if not resolved_base_url:
            raise ValueError("OpenAI-compatible providers require a base_url.")
        super().__init__(
            api_key=api_key,
            model=model or default_model(provider_name),
            base_url=resolved_base_url,
        )


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek API preset using the OpenAI-compatible protocol."""

    def __init__(self, api_key, model=None, base_url=None):
        super().__init__(
            api_key=api_key,
            model=model or default_model("deepseek"),
            base_url=base_url or default_base_url("deepseek"),
            provider_name="deepseek",
        )
