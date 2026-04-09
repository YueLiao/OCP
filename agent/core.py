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

            # After extraction, automatically call LLM to parse content into CipherSpec
            if req.skill == SkillName.CIPHER_EXTRACTION and result.success:
                extraction_result = self._process_extraction(result)
                if extraction_result:
                    results.append(extraction_result)
                    self.session.add_result(extraction_result)

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

    def _process_extraction(self, extraction_result: SkillResult) -> Optional[SkillResult]:
        """After CipherExtractorSkill loads a file, use LLM to parse it into CipherSpec."""
        if self.llm is None:
            return None

        extraction_data = self.session.get_metadata("extraction_data")
        if not extraction_data:
            return None

        try:
            raw_response = self.llm.extract_cipher_from_content(extraction_data)
        except NotImplementedError:
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_EXTRACTION,
                error="This LLM provider does not support document extraction.",
            )
        except Exception as e:
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_EXTRACTION,
                error=f"LLM extraction failed: {e}",
            )

        # Parse JSON from LLM response
        from agent.llm.response_parser import parse_llm_json_response
        from agent.skills.cipher_spec import CipherSpec
        import json
        import re

        text = raw_response.strip()
        # Strip markdown code fences
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()
        # Find JSON
        brace_start = text.find("{")
        if brace_start == -1:
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_EXTRACTION,
                error=f"LLM did not return valid JSON. Response: {raw_response[:500]}",
            )
        depth = 0
        brace_end = -1
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    brace_end = i
                    break
        if brace_end == -1:
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_EXTRACTION,
                error="LLM returned incomplete JSON.",
            )

        try:
            spec_data = json.loads(text[brace_start:brace_end + 1])
        except json.JSONDecodeError:
            fixed = re.sub(r",\s*([}\]])", r"\1", text[brace_start:brace_end + 1])
            try:
                spec_data = json.loads(fixed)
            except json.JSONDecodeError as e:
                return SkillResult(
                    success=False,
                    skill=SkillName.CIPHER_EXTRACTION,
                    error=f"Failed to parse LLM JSON: {e}",
                )

        # Store spec and optionally auto-build
        spec = CipherSpec.from_dict(spec_data)
        errors = spec.validate()
        if errors:
            # Store anyway for user to review/fix
            self.session.set_metadata("pending_cipher_spec", spec_data)
            return SkillResult(
                success=True,
                skill=SkillName.CIPHER_EXTRACTION,
                data={"spec": spec_data, "validation_errors": errors},
                summary=f"Extracted cipher '{spec.name}' from document (with warnings: {'; '.join(errors)}). "
                        f"Review and use cipher_definition to build.",
            )

        self.session.set_metadata("pending_cipher_spec", spec_data)
        auto_build = self.session.get_metadata("extraction_auto_build", False)

        if auto_build:
            build_result = self._execute_skill(SkillRequest(
                skill=SkillName.CIPHER_DEFINITION, params={}
            ))
            self.session.add_result(build_result)
            return build_result

        return SkillResult(
            success=True,
            skill=SkillName.CIPHER_EXTRACTION,
            data={"spec": spec_data},
            summary=f"Extracted cipher '{spec.name}': {spec.cipher_type}, "
                    f"{spec.block_size}-bit, {spec.nbr_rounds} rounds, "
                    f"{len(spec.round_structure)} layers/round. "
                    f"Use cipher_definition to build it.",
        )
