"""Factory helpers for built-in LLM providers."""

from agent.llm.provider import LLMProvider
from agent.llm.provider_config import default_base_url, default_model


def create_llm_provider(provider_name, api_key=None, model=None, base_url=None) -> LLMProvider:
    """Create one of the built-in LLM providers."""

    resolved_model = model or default_model(provider_name)
    resolved_base_url = base_url or default_base_url(provider_name)

    if provider_name == "openai":
        from agent.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=api_key, model=resolved_model, base_url=resolved_base_url)
    if provider_name == "openai-compatible":
        from agent.llm.openai_compatible_provider import OpenAICompatibleProvider

        return OpenAICompatibleProvider(api_key=api_key, model=resolved_model, base_url=resolved_base_url)
    if provider_name == "deepseek":
        from agent.llm.openai_compatible_provider import DeepSeekProvider

        return DeepSeekProvider(api_key=api_key, model=resolved_model, base_url=resolved_base_url)
    if provider_name == "anthropic":
        from agent.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=api_key, model=resolved_model)
    if provider_name == "gemini":
        from agent.llm.gemini_provider import GeminiProvider

        return GeminiProvider(api_key=api_key, model=resolved_model)
    if provider_name == "ollama":
        from agent.llm.ollama_provider import OllamaProvider

        return OllamaProvider(model=resolved_model, host=resolved_base_url)

    raise ValueError(f"Unknown provider: {provider_name}")
