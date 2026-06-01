"""Interactive CLI interface for the OCP agent."""

import json

from agent.interfaces.api import OCPAgent
from agent.llm.provider import LLMProvider


def _format_draft_review(draft):
    lines = ["CipherSpec draft:"]
    lines.append(json.dumps(draft.spec, indent=2))
    if draft.validation_errors:
        lines.append("\nValidation errors:")
        lines.extend(f"- {error}" for error in draft.validation_errors)
    if draft.warnings:
        lines.append("\nWarnings:")
        lines.extend(f"- {warning}" for warning in draft.warnings)
    if draft.assumptions:
        lines.append("\nAssumptions:")
        lines.extend(f"- {assumption}" for assumption in draft.assumptions)
    if draft.clarification_questions:
        lines.append("\nClarification questions:")
        lines.extend(f"- {question}" for question in draft.clarification_questions)
    return "\n".join(lines)


def _handle_text_draft(agent, text, input_func=input, output_func=print):
    extraction = agent.extract_cipher_facts(text, source_type="direct_text", format_hint="mixed")
    if not extraction.success:
        output_func(f"[Extraction error] {extraction.error}")
        return extraction

    draft = agent.draft_cipher_spec()
    output_func(_format_draft_review(draft))
    if draft.validation_errors:
        output_func("Draft has validation errors. Please revise the text before building.")
        return extraction

    answer = input_func("Build this cipher now? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        output_func("Draft saved in session metadata. Build skipped.")
        return extraction

    result = agent.confirm_cipher_spec(draft)
    if result.success:
        output_func(f"Built cipher: {result.data.get('cipher_name')}")
    else:
        output_func(f"[Build error] {result.error}")
    return result


def _format_cli_error(exc):
    """Return a concise interactive CLI error without provider internals policy changes."""

    return f"\n[Error] {exc}\n"


def run_cli(llm_provider: LLMProvider, input_func=input, output_func=print):
    """Run an interactive CLI session with the OCP agent.

    Args:
        llm_provider: An LLMProvider implementation for natural language processing.

    Example:
        from my_llm import MyOpenAIProvider
        from agent.interfaces.cli import run_cli
        run_cli(MyOpenAIProvider(api_key="sk-..."))
    """
    agent = OCPAgent(llm_provider=llm_provider)

    output_func("=" * 60)
    output_func("  OCP Agent - Automated Cryptanalysis Assistant")
    output_func("=" * 60)
    output_func("Commands: 'quit'/'exit', 'reset', 'draft <cipher text>'")
    output_func()

    while True:
        try:
            user_input = input_func("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            output_func("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            output_func("Goodbye!")
            break

        if user_input.lower() == "reset":
            agent.session.reset()
            output_func("Session reset.")
            continue

        if user_input.startswith("draft "):
            _handle_text_draft(agent, user_input[len("draft "):].strip(), input_func, output_func)
            continue

        try:
            response = agent.chat(user_input)
            output_func(f"\nAssistant> {response}\n")
        except Exception as e:
            output_func(_format_cli_error(e))
