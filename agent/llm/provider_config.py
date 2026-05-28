"""Provider defaults and environment resolution for Agent launchers."""

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence


@dataclass(frozen=True)
class ProviderDefaults:
    """Static configuration used by CLI and web provider factories."""

    model: str
    env_vars: Sequence[str]
    base_url: Optional[str] = None
    requires_api_key: bool = True


PROVIDER_DEFAULTS = {
    "openai": ProviderDefaults(model="gpt-4o", env_vars=("OPENAI_API_KEY",)),
    "openai-compatible": ProviderDefaults(
        model="gpt-4o",
        env_vars=("OPENAI_COMPATIBLE_API_KEY", "OPENAI_API_KEY"),
    ),
    "deepseek": ProviderDefaults(
        model="deepseek-chat",
        env_vars=("DEEPSEEK_API_KEY",),
        base_url="https://api.deepseek.com",
    ),
    "anthropic": ProviderDefaults(
        model="claude-sonnet-4-20250514",
        env_vars=("ANTHROPIC_API_KEY",),
    ),
    "gemini": ProviderDefaults(model="gemini-2.5-flash", env_vars=("GOOGLE_API_KEY",)),
    "ollama": ProviderDefaults(
        model="llama3",
        env_vars=(),
        base_url="http://localhost:11434",
        requires_api_key=False,
    ),
}


def supported_providers() -> tuple[str, ...]:
    """Return provider names accepted by the built-in launchers."""

    return tuple(PROVIDER_DEFAULTS)


def get_provider_defaults(provider_name: str) -> ProviderDefaults:
    """Return defaults for a provider or raise a clear error."""

    try:
        return PROVIDER_DEFAULTS[provider_name]
    except KeyError as exc:
        raise ValueError(f"Unknown provider: {provider_name}") from exc


def default_model(provider_name: str) -> str:
    """Return the default model for a provider."""

    return get_provider_defaults(provider_name).model


def default_base_url(provider_name: str) -> Optional[str]:
    """Return the default base URL for a provider, when it has one."""

    return get_provider_defaults(provider_name).base_url


def resolve_api_key(
    provider_name: str,
    explicit_api_key: Optional[str] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> Optional[str]:
    """Resolve an API key from an explicit value or provider-specific env vars."""

    if explicit_api_key:
        return explicit_api_key

    env = environ or {}
    for name in get_provider_defaults(provider_name).env_vars:
        value = env.get(name)
        if value:
            return value
    return None


def api_key_error(provider_name: str) -> str:
    """Build a user-facing API-key error for a provider."""

    defaults = get_provider_defaults(provider_name)
    env_names = " / ".join(defaults.env_vars)
    return f"Set {env_names} env var or pass --api-key"
