from agent.llm.provider_config import (
    api_key_error,
    default_base_url,
    default_model,
    resolve_api_key,
    supported_providers,
)


def test_deepseek_defaults_are_openai_compatible():
    assert "deepseek" in supported_providers()
    assert default_model("deepseek") == "deepseek-chat"
    assert default_base_url("deepseek") == "https://api.deepseek.com"


def test_openai_compatible_can_reuse_openai_key():
    env = {"OPENAI_API_KEY": "openai-key"}
    assert resolve_api_key("openai-compatible", environ=env) == "openai-key"


def test_explicit_api_key_wins_over_environment():
    env = {"DEEPSEEK_API_KEY": "env-key"}
    assert resolve_api_key("deepseek", "explicit-key", env) == "explicit-key"


def test_api_key_error_names_provider_environment_variables():
    assert "DEEPSEEK_API_KEY" in api_key_error("deepseek")

