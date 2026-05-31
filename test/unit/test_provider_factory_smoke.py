import sys
from types import SimpleNamespace

from agent.llm.factory import create_llm_provider
from agent.llm.openai_compatible_provider import DeepSeekProvider, OpenAICompatibleProvider


class FakeOpenAIClient:
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key
        self.base_url = base_url


def test_deepseek_provider_uses_openai_compatible_defaults(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAIClient))

    provider = create_llm_provider("deepseek", api_key="test-key")

    assert isinstance(provider, DeepSeekProvider)
    assert provider.model == "deepseek-chat"
    assert provider.client.base_url == "https://api.deepseek.com"


def test_deepseek_provider_allows_openai_compatible_overrides(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAIClient))

    provider = create_llm_provider(
        "deepseek",
        api_key="test-key",
        model="deepseek-reasoner",
        base_url="https://example.invalid/v1",
    )

    assert isinstance(provider, DeepSeekProvider)
    assert provider.model == "deepseek-reasoner"
    assert provider.client.base_url == "https://example.invalid/v1"


def test_openai_compatible_provider_requires_base_url(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAIClient))

    provider = create_llm_provider(
        "openai-compatible",
        api_key="test-key",
        model="local-model",
        base_url="http://localhost:8000/v1",
    )

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.model == "local-model"
    assert provider.client.base_url == "http://localhost:8000/v1"


def test_openai_compatible_provider_fails_without_base_url(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAIClient))

    try:
        create_llm_provider("openai-compatible", api_key="test-key")
    except ValueError as exc:
        assert "base_url" in str(exc)
    else:
        raise AssertionError("OpenAI-compatible provider should require base_url.")
