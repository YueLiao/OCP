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
        """Run the multi-step LLM pipeline to extract a CipherSpec from loaded file."""
        if self.llm is None:
            return None

        extraction_data = self.session.get_metadata("extraction_data")
        if not extraction_data:
            return None

        import json
        import re
        from agent.skills.cipher_spec import CipherSpec
        from agent.skills.cipher_extractor import (
            STEP1_LOCATE_PROMPT, STEP2_EXTRACT_PROMPT,
            STEP3_FORMALIZE_PROMPT, IMAGE_EXTRACTION_PROMPT,
        )

        pipeline = extraction_data.get("pipeline", "single")
        focus = extraction_data.get("focus", "")
        file_name = extraction_data.get("file_name", "")

        try:
            if extraction_data["file_type"] == "image":
                # Image: single-step with vision
                image_data = {"base64": extraction_data["image_base64"],
                              "mime_type": extraction_data["mime_type"]}
                raw = self.llm.call_llm(IMAGE_EXTRACTION_PROMPT, image_data=image_data)
                spec_data = self._parse_json_from_llm(raw)

            elif pipeline == "single":
                # Short document: single-step extraction
                from agent.skills.cipher_extractor import STEP3_FORMALIZE_PROMPT
                text = extraction_data["full_text"]
                prompt = STEP3_FORMALIZE_PROMPT.format(cipher_details=text)
                raw = self.llm.call_llm(prompt)
                spec_data = self._parse_json_from_llm(raw)

            else:
                # Multi-step pipeline for long papers
                full_text = extraction_data["full_text"]

                # --- Step 1: Locate relevant sections ---
                locate_prompt = STEP1_LOCATE_PROMPT
                if focus:
                    locate_prompt += f"\nFOCUS: The user is specifically interested in: {focus}\n\n"
                # Send first ~15k chars for structure scanning
                locate_prompt += full_text[:15000]
                if len(full_text) > 15000:
                    locate_prompt += "\n\n[... remaining content omitted for scanning ...]\n"
                    locate_prompt += "\n" + full_text[-3000:]  # also include end (references, appendix)

                step1_raw = self.llm.call_llm(locate_prompt)
                step1_data = self._parse_json_from_llm(step1_raw)

                cipher_name = step1_data.get("cipher_name", "Unknown")
                cipher_type = step1_data.get("design_type", step1_data.get("cipher_type", "unknown"))
                terminology = json.dumps(step1_data.get("paper_terminology", {}))
                relevant_pages = step1_data.get("relevant_pages", [])

                self.session.set_metadata("extraction_step1", step1_data)

                # --- Step 2: Extract details from relevant pages ---
                if relevant_pages and extraction_data["file_type"] == "pdf":
                    from agent.skills.cipher_extractor import extract_text_from_pdf
                    sections_content = extract_text_from_pdf(
                        extraction_data["file_path"], set(relevant_pages)
                    )
                else:
                    sections_content = full_text[:20000]

                step2_prompt = STEP2_EXTRACT_PROMPT.format(
                    cipher_name=cipher_name,
                    cipher_type=cipher_type,
                    terminology=terminology,
                    sections_content=sections_content,
                )
                step2_raw = self.llm.call_llm(step2_prompt)
                step2_data = self._parse_json_from_llm(step2_raw)

                self.session.set_metadata("extraction_step2", step2_data)

                # --- Step 3: Formalize into CipherSpec ---
                step3_prompt = STEP3_FORMALIZE_PROMPT.format(
                    cipher_details=json.dumps(step2_data, indent=2)
                )
                step3_raw = self.llm.call_llm(step3_prompt)
                spec_data = self._parse_json_from_llm(step3_raw)

        except NotImplementedError:
            return SkillResult(
                success=False, skill=SkillName.CIPHER_EXTRACTION,
                error="LLM provider does not implement call_llm().",
            )
        except Exception as e:
            return SkillResult(
                success=False, skill=SkillName.CIPHER_EXTRACTION,
                error=f"Extraction pipeline failed: {e}",
            )

        # Validate and store
        spec = CipherSpec.from_dict(spec_data)
        errors = spec.validate()
        self.session.set_metadata("pending_cipher_spec", spec_data)

        if errors:
            return SkillResult(
                success=True, skill=SkillName.CIPHER_EXTRACTION,
                data={"spec": spec_data, "validation_errors": errors,
                      "pipeline": pipeline},
                summary=f"Extracted '{spec.name}' from {file_name} "
                        f"(warnings: {'; '.join(errors)}). Review and fix.",
            )

        auto_build = self.session.get_metadata("extraction_auto_build", False)
        if auto_build:
            build_result = self._execute_skill(SkillRequest(
                skill=SkillName.CIPHER_DEFINITION, params={}
            ))
            self.session.add_result(build_result)
            return build_result

        return SkillResult(
            success=True, skill=SkillName.CIPHER_EXTRACTION,
            data={"spec": spec_data, "pipeline": pipeline},
            summary=f"Extracted '{spec.name}': {spec.cipher_type}, "
                    f"{spec.block_size}-bit, {spec.nbr_rounds} rounds, "
                    f"{len(spec.round_structure)} layers/round. "
                    f"Pipeline: {pipeline}-step.",
        )

    @staticmethod
    def _parse_json_from_llm(raw: str) -> dict:
        """Extract a JSON object from LLM response text."""
        import json
        import re

        text = raw.strip()
        fence = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()

        brace_start = text.find("{")
        if brace_start == -1:
            raise ValueError(f"No JSON found in LLM response: {raw[:300]}")

        depth, brace_end = 0, -1
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    brace_end = i
                    break

        if brace_end == -1:
            raise ValueError("Incomplete JSON in LLM response")

        json_str = text[brace_start:brace_end + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            fixed = re.sub(r",\s*([}\]])", r"\1", json_str)
            return json.loads(fixed)
