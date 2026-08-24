"""OCP Agent - Interactive CLI launcher.

Usage:
    # OpenAI
    export OPENAI_API_KEY="sk-xxx"
    python3 run_agent.py

    # Anthropic Claude
    export ANTHROPIC_API_KEY="sk-ant-xxx"
    python3 run_agent.py --provider anthropic

    # Custom OpenAI-compatible endpoint (e.g., local model, Azure)
    export OPENAI_COMPATIBLE_API_KEY="your-key"
    python3 run_agent.py --provider openai-compatible --base-url http://localhost:8000/v1

    # DeepSeek
    export DEEPSEEK_API_KEY="sk-xxx"
    python3 run_agent.py --provider deepseek

    # Google Gemini
    export GOOGLE_API_KEY="AIza..."
    python3 run_agent.py --provider gemini

    # Ollama (local models, no API key needed)
    python3 run_agent.py --provider ollama
    python3 run_agent.py --provider ollama --model qwen2.5

    # Specify model
    python3 run_agent.py --provider openai --model gpt-4o
    python3 run_agent.py --provider anthropic --model claude-sonnet-4-20250514
    python3 run_agent.py --provider gemini --model gemini-2.5-flash
    python3 run_agent.py --provider ollama --model llama3
"""

import argparse
import os
import sys

from agent.llm.provider_config import (
    api_key_error,
    default_base_url,
    default_model,
    get_provider_defaults,
    resolve_api_key,
    supported_providers,
)


def main():
    parser = argparse.ArgumentParser(description="OCP Agent - Automated Cryptanalysis Assistant")
    parser.add_argument("--provider", choices=supported_providers(), default="openai",
                        help="LLM provider (default: openai)")
    parser.add_argument("--model", type=str, default=None,
                        help="Model name (provider-specific default if omitted)")
    parser.add_argument("--base-url", type=str, default=None,
                        help="Custom API base URL (for OpenAI-compatible endpoints)")
    parser.add_argument("--api-key", type=str, default=None,
                        help="API key (or set the provider-specific env var)")
    args = parser.parse_args()

    model = args.model or default_model(args.provider)
    base_url = args.base_url or default_base_url(args.provider)
    api_key = resolve_api_key(args.provider, args.api_key, os.environ)
    provider_defaults = get_provider_defaults(args.provider)

    if provider_defaults.requires_api_key and not api_key:
        print(f"Error: {api_key_error(args.provider)}")
        sys.exit(1)
    if args.provider == "openai-compatible" and not base_url:
        print("Error: --base-url is required for openai-compatible")
        sys.exit(1)

    try:
        from agent.llm.factory import create_llm_provider

        provider = create_llm_provider(args.provider, api_key=api_key, model=model, base_url=base_url)
    except ImportError as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    from agent.interfaces.cli import run_cli
    run_cli(provider)


if __name__ == "__main__":
    main()

    # sk-a1d64dbd5e68489789853a737f0d1e63
