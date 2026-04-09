from abc import ABC, abstractmethod
from typing import List

from agent.types import UserIntent, SkillRequest, SkillResult


class LLMProvider(ABC):
    """Abstract interface for LLM integration.

    Users implement this class to connect their preferred LLM (OpenAI, Claude, local models, etc.)
    to the OCP agent framework. The framework calls these methods during conversation processing.

    Example implementation with OpenAI:

        class OpenAIProvider(LLMProvider):
            def __init__(self, api_key, model="gpt-4"):
                import openai
                self.client = openai.OpenAI(api_key=api_key)
                self.model = model

            def parse_user_request(self, user_message, conversation_history, available_skills, session_context):
                from agent.llm.prompt_templates import build_parse_prompt
                from agent.llm.response_parser import parse_llm_json_response
                prompt = build_parse_prompt(user_message, available_skills, session_context)
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": prompt}] + conversation_history,
                )
                return parse_llm_json_response(response.choices[0].message.content)

            def generate_response(self, results, original_intent, conversation_history, session_context):
                from agent.llm.prompt_templates import build_response_prompt
                prompt = build_response_prompt(results, session_context)
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": prompt}] + conversation_history,
                )
                return response.choices[0].message.content

            def handle_error(self, error, failed_request, session_context):
                return f"Error executing {failed_request.skill.value}: {error}"
    """

    @abstractmethod
    def parse_user_request(
        self,
        user_message: str,
        conversation_history: List[dict],
        available_skills: List[dict],
        session_context: dict,
    ) -> UserIntent:
        """Parse a natural language user message into structured UserIntent.

        Args:
            user_message: The raw user input.
            conversation_history: List of {"role": str, "content": str} messages.
            available_skills: List of skill descriptors from SkillRegistry.list_descriptors().
            session_context: Session state dict from Session.get_context().

        Returns:
            UserIntent with one or more SkillRequests, or with needs_clarification=True.
        """
        ...

    @abstractmethod
    def generate_response(
        self,
        results: List[SkillResult],
        original_intent: UserIntent,
        conversation_history: List[dict],
        session_context: dict,
    ) -> str:
        """Generate a human-readable response from skill execution results.

        Args:
            results: List of SkillResult from executed skills.
            original_intent: The parsed UserIntent that produced these results.
            conversation_history: Conversation history.
            session_context: Current session state.

        Returns:
            A natural language response string.
        """
        ...

    @abstractmethod
    def handle_error(
        self,
        error: Exception,
        failed_request: SkillRequest,
        session_context: dict,
    ) -> str:
        """Generate a helpful error message when a skill execution fails.

        Args:
            error: The exception that occurred.
            failed_request: The SkillRequest that failed.
            session_context: Current session state.

        Returns:
            A human-readable error message.
        """
        ...

    def extract_cipher_from_content(self, extraction_data: dict) -> str:
        """Extract a CipherSpec JSON from document content or image using LLM.

        This method is called by AgentCore after CipherExtractorSkill loads a file.
        Default implementation raises NotImplementedError. Providers with vision
        capabilities should override this to handle image inputs.

        Args:
            extraction_data: Dict with keys:
                - "prompt": The extraction prompt
                - "content": Text content (for PDF/text files)
                - "image_base64": Base64 image (for image files)
                - "mime_type": Image MIME type (for image files)
                - "file_type": "pdf", "text", or "image"

        Returns:
            Raw LLM response string (should be JSON).
        """
        raise NotImplementedError(
            "This LLM provider does not support document extraction. "
            "Override extract_cipher_from_content() to add support."
        )
