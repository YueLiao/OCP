from agent.llm.provider import LLMProvider

__all__ = ["LLMProvider", "OpenAIProvider", "AnthropicProvider"]


def OpenAIProvider(*args, **kwargs):
    """Lazy import to avoid requiring openai as a dependency."""
    from agent.llm.openai_provider import OpenAIProvider as _Cls
    return _Cls(*args, **kwargs)


def AnthropicProvider(*args, **kwargs):
    """Lazy import to avoid requiring anthropic as a dependency."""
    from agent.llm.anthropic_provider import AnthropicProvider as _Cls
    return _Cls(*args, **kwargs)
