"""Interactive CLI interface for the OCP agent."""

from agent.core import AgentCore
from agent.llm.provider import LLMProvider


def run_cli(llm_provider: LLMProvider):
    """Run an interactive CLI session with the OCP agent.

    Args:
        llm_provider: An LLMProvider implementation for natural language processing.

    Example:
        from my_llm import MyOpenAIProvider
        from agent.interfaces.cli import run_cli
        run_cli(MyOpenAIProvider(api_key="sk-..."))
    """
    agent = AgentCore(llm_provider=llm_provider)

    print("=" * 60)
    print("  OCP Agent - Automated Cryptanalysis Assistant")
    print("=" * 60)
    print("Commands: 'quit'/'exit' to leave, 'reset' to clear session")
    print()

    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        if user_input.lower() == "reset":
            agent.session.reset()
            print("Session reset.")
            continue

        try:
            response = agent.process_message(user_input)
            print(f"\nAssistant> {response}\n")
        except Exception as e:
            print(f"\n[Error] {e}\n")
