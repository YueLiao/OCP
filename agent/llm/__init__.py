from agent.llm.provider import LLMProvider

__all__ = ["LLMProvider", "OpenAIProvider", "AnthropicProvider", "GeminiProvider", "OllamaProvider"]


def OpenAIProvider(*args, **kwargs):
    """Lazy import to avoid requiring openai as a dependency."""
    from agent.llm.openai_provider import OpenAIProvider as _Cls
    return _Cls(*args, **kwargs)


def AnthropicProvider(*args, **kwargs):
    """Lazy import to avoid requiring anthropic as a dependency."""
    from agent.llm.anthropic_provider import AnthropicProvider as _Cls
    return _Cls(*args, **kwargs)


def GeminiProvider(*args, **kwargs):
    """Lazy import to avoid requiring google-genai as a dependency."""
    from agent.llm.gemini_provider import GeminiProvider as _Cls
    return _Cls(*args, **kwargs)


def OllamaProvider(*args, **kwargs):
    """Lazy import to avoid requiring ollama as a dependency."""
    from agent.llm.ollama_provider import OllamaProvider as _Cls
    return _Cls(*args, **kwargs)
