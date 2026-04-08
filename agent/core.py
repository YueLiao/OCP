from typing import List, Optional

from agent.types import SkillName, SkillRequest, SkillResult, UserIntent
from agent.session import Session
from agent.skills import SkillRegistry, create_default_registry
from agent.llm.provider import LLMProvider


class AgentCore:
    """Central orchestrator that connects LLM parsing, skill execution, and response generation.

    Can operate in two modes:
    1. With LLM: process_message() parses natural language -> executes skills -> generates response
    2. Without LLM: execute_direct() runs a skill request directly (for programmatic use)
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        skill_registry: Optional[SkillRegistry] = None,
        session: Optional[Session] = None,
    ):
        self.llm = llm_provider
        self.registry = skill_registry or create_default_registry()
        self.session = session or Session()

    def process_message(self, user_message: str) -> str:
        """Process a natural language message through the full LLM pipeline.

        Flow: parse user intent -> execute skills -> generate response.

        Args:
            user_message: Natural language input from the user.

        Returns:
            A human-readable response string.

        Raises:
            RuntimeError: If no LLM provider is configured.
        """
        if self.llm is None:
            raise RuntimeError("No LLM provider configured. Use execute_direct() for programmatic access.")

        self.session.add_message("user", user_message)

        # Parse user intent
        intent = self.llm.parse_user_request(
            user_message=user_message,
            conversation_history=self.session.get_history(),
            available_skills=self.registry.list_descriptors(),
            session_context=self.session.get_context(),
        )

        if intent is None:
            response = "I couldn't understand your request. Could you please rephrase it?"
            self.session.add_message("assistant", response)
            return response

        if intent.needs_clarification:
            self.session.add_message("assistant", intent.clarification_prompt)
            return intent.clarification_prompt

        # Execute skills sequentially
        results = []
        for req in intent.requests:
            result = self._execute_skill(req)
            results.append(result)
            self.session.add_result(result)

        # Generate response
        response = self.llm.generate_response(
            results=results,
            original_intent=intent,
            conversation_history=self.session.get_history(),
            session_context=self.session.get_context(),
        )

        self.session.add_message("assistant", response)
        return response

    def execute_direct(self, request: SkillRequest) -> SkillResult:
        """Execute a skill request directly without LLM involvement.

        Args:
            request: A SkillRequest with skill name and parameters.

        Returns:
            SkillResult from the skill execution.
        """
        result = self._execute_skill(request)
        self.session.add_result(result)
        return result

    def _execute_skill(self, request: SkillRequest) -> SkillResult:
        """Look up and execute a single skill request."""
        skill = self.registry.get(request.skill)
        if skill is None:
            return SkillResult(
                success=False,
                skill=request.skill,
                error=f"Unknown skill: {request.skill.value}",
            )

        try:
            return skill.execute(request, self.session)
        except Exception as e:
            if self.llm is not None:
                error_msg = self.llm.handle_error(e, request, self.session.get_context())
            else:
                error_msg = f"Skill '{request.skill.value}' failed: {e}"
            return SkillResult(
                success=False,
                skill=request.skill,
                error=error_msg,
            )
