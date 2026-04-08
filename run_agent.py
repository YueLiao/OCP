"""OCP Agent - Interactive CLI launcher.

Usage:
    # OpenAI
    export OPENAI_API_KEY="sk-xxx"
    python3 run_agent.py

    # Anthropic Claude
    export ANTHROPIC_API_KEY="sk-ant-xxx"
    python3 run_agent.py --provider anthropic

    # Custom OpenAI-compatible endpoint (e.g., local model, Azure)
    export OPENAI_API_KEY="your-key"
    python3 run_agent.py --base-url http://localhost:8000/v1

    # Specify model
    python3 run_agent.py --provider openai --model gpt-4o
    python3 run_agent.py --provider anthropic --model claude-sonnet-4-20250514
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="OCP Agent - Automated Cryptanalysis Assistant")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai",
                        help="LLM provider (default: openai)")
    parser.add_argument("--model", type=str, default=None,
                        help="Model name (default: gpt-4o for openai, claude-sonnet-4-20250514 for anthropic)")
    parser.add_argument("--base-url", type=str, default=None,
                        help="Custom API base URL (for OpenAI-compatible endpoints)")
    parser.add_argument("--api-key", type=str, default=None,
                        help="API key (or set OPENAI_API_KEY / ANTHROPIC_API_KEY env var)")
    args = parser.parse_args()

    if args.provider == "openai":
        api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Error: Set OPENAI_API_KEY env var or pass --api-key")
            sys.exit(1)
        model = args.model or "gpt-4o"
        from agent.llm.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key=api_key, model=model, base_url=args.base_url)

    elif args.provider == "anthropic":
        api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: Set ANTHROPIC_API_KEY env var or pass --api-key")
            sys.exit(1)
        model = args.model or "claude-sonnet-4-20250514"
        from agent.llm.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider(api_key=api_key, model=model)

    from agent.interfaces.cli import run_cli
    run_cli(provider)


if __name__ == "__main__":
    main()
