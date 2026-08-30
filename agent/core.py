from typing import List, Optional

from agent.types import SkillName, SkillRequest, SkillResult, UserIntent
from agent.session import Session
from agent.skills import SkillRegistry, create_default_registry
from agent.llm.provider import LLMProvider
from agent.llm.response_parser import parse_llm_json_object
from agent.artifacts import artifacts_from_result_data


EXPECTED_SKILL_EXCEPTIONS = (ValueError, RuntimeError, OSError, ImportError, NotImplementedError)
EXPECTED_EXTRACTION_EXCEPTIONS = (ValueError, RuntimeError, OSError, KeyError)


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
        orchestrate: bool = False,
    ):
        self.llm = llm_provider
        self.registry = skill_registry or create_default_registry()
        self.session = session or Session()
        # When on, a chat turn's skills run through the AgentController (verify + repair per
        # step) instead of the plain sequential loop. Off by default (single-pass behavior
        # unchanged); also switchable per-session via metadata "orchestrate".
        self.orchestrate = orchestrate

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

        # Orchestrated path: run the turn's skills through the AgentController (each step
        # verified + repaired against an objective gate) instead of the plain loop. Extraction
        # turns keep the sequential path, which has its own multi-step LLM pipeline + auto-build.
        has_extraction = any(r.skill == SkillName.CIPHER_EXTRACTION for r in intent.requests)
        if self._orchestrate_enabled() and intent.requests and not has_extraction:
            response = self._run_orchestrated(intent.requests)
            self.session.add_message("assistant", response)
            return response

        # Execute skills sequentially
        results = []
        for req in intent.requests:
            result = self._execute_skill(req)
            results.append(result)
            self._record_result(result)

            # After extraction, automatically call LLM to parse content into CipherSpec
            if req.skill == SkillName.CIPHER_EXTRACTION and result.success:
                extraction_result = self._process_extraction(result)
                if extraction_result:
                    results.append(extraction_result)
                    self._record_result(extraction_result)

        # Store the executed requests so callers (e.g. the web UI) can reconstruct
        # the equivalent low-level OCP code for this turn.
        self.session.set_metadata(
            "last_requests",
            [{"skill": req.skill.value, "params": req.params} for req in intent.requests],
        )

        # For skill-execution turns, return deterministic summaries (no extra LLM
        # call, no hallucinated results). Fall back to the LLM only for
        # conversational turns that ran no skills.
        if results:
            lines = []
            for r in results:
                if r.success:
                    lines.append(r.summary or f"{r.skill.value}: done.")
                else:
                    lines.append(f"{r.skill.value} failed: {r.error}")
            response = "\n".join(lines) if lines else "Done."
        else:
            response = self.llm.generate_response(
                results=results,
                original_intent=intent,
                conversation_history=self.session.get_history(),
                session_context=self.session.get_context(),
            )

        self.session.add_message("assistant", response)
        return response

    def _orchestrate_enabled(self) -> bool:
        # An explicit per-session choice (e.g. a UI toggle setting metadata) overrides the
        # constructor default in BOTH directions; absent that, the constructor default holds.
        choice = self.session.get_metadata("orchestrate")
        if choice is not None:
            return bool(choice)
        return bool(self.orchestrate)

    def _repair_spec(self, spec, problems):
        """LLM-targeted CipherSpec repair: current spec + concrete problems -> corrected spec dict.

        Shared by the OCPAgent facade (repair_cipher_spec) and the orchestrated build step, so a
        chat/pipeline build that fails its KAT is re-drafted, not just reported. Raises when no LLM
        is connected or the response has no parseable spec.
        """
        if self.llm is None:
            raise RuntimeError("AI repair needs a connected LLM provider.")
        from agent.llm.prompt_templates import build_repair_prompt
        corrected = parse_llm_json_object(self.llm.call_llm(build_repair_prompt(spec, problems or [])))
        if corrected is None:
            raise ValueError("Could not parse a corrected CipherSpec from the LLM response.")
        return corrected

    def _run_orchestrated(self, requests) -> str:
        """Run a turn's SkillRequests through the AgentController and summarize the report.

        Each skill executes via execute_direct (which records results/artifacts and traces), so
        the orchestrated path adds per-step verify + repair on top of the sequential loop's
        recording. A cipher a definition step builds is on the session for a later analysis step
        to read; a build whose KAT fails is re-drafted via the LLM when one is connected.
        """
        from agent.controller import AgentController, plan_from_requests

        repair_spec = self._repair_spec if self.llm is not None else None
        plan = plan_from_requests(requests, execute=self.execute_direct, repair_spec=repair_spec)
        controller = AgentController(
            session=self.session,
            is_cancelled=lambda: bool(self.session.get_metadata("cancel_requested")),
            max_attempts=3,
        )
        report = controller.run("chat turn", plan, ctx={})
        self.session.set_metadata(
            "last_requests",
            [{"skill": r.skill.value, "params": r.params} for r in requests],
        )
        return self._summarize_report(report)

    @staticmethod
    def _summarize_report(report) -> str:
        """Turn a controller RunReport into the deterministic per-step summary process_message returns."""
        lines = []
        for o in report.outcomes:
            if o.status == "passed":
                lines.append(o.summary or f"{o.name}: done.")
            elif o.status == "skipped":
                lines.append(f"{o.name}: skipped ({o.error})")
            elif o.status == "cancelled":
                lines.append(f"{o.name}: cancelled")
            else:
                lines.append(f"{o.name} failed: {o.error}")
        return "\n".join(lines) if lines else (report.summary or "Done.")

    def execute_direct(self, request: SkillRequest) -> SkillResult:
        """Execute a skill request directly without LLM involvement.

        Args:
            request: A SkillRequest with skill name and parameters.

        Returns:
            SkillResult from the skill execution.
        """
        self.session.add_trace("skill_start", {"skill": request.skill.value, "params": request.params})
        result = self._execute_skill(request)
        artifacts = self._record_result(result)
        self.session.add_trace(
            "skill_finish",
            {
                "skill": request.skill.value,
                "success": result.success,
                "summary": result.summary,
                "error": result.error,
                "artifact_count": len(artifacts),
            },
        )
        return result

    def _record_result(self, result: SkillResult):
        """Store a skill result and register any artifacts it returned."""
        self.session.add_result(result)
        artifacts = artifacts_from_result_data(result.data, source_skill=result.skill.value)
        self.session.add_artifacts(artifacts)
        return artifacts

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
        except EXPECTED_SKILL_EXCEPTIONS as e:
            error_msg = self._format_skill_exception(request, e, unexpected=False)
            return SkillResult(
                success=False,
                skill=request.skill,
                error=error_msg,
            )
        except Exception as e:
            error_msg = self._format_skill_exception(request, e, unexpected=True)
            return SkillResult(
                success=False,
                skill=request.skill,
                error=error_msg,
            )

    def _format_skill_exception(self, request: SkillRequest, exc: Exception, *, unexpected: bool) -> str:
        """Format skill execution exceptions while preserving LLM-specific error handling."""

        if self.llm is not None:
            return self.llm.handle_error(exc, request, self.session.get_context())
        prefix = "Unexpected skill" if unexpected else "Skill"
        return f"{prefix} '{request.skill.value}' failed: {exc}"

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
        except EXPECTED_EXTRACTION_EXCEPTIONS as e:
            return SkillResult(
                success=False, skill=SkillName.CIPHER_EXTRACTION,
                error=f"Extraction pipeline failed: {e}",
            )
        except Exception as e:
            return SkillResult(
                success=False, skill=SkillName.CIPHER_EXTRACTION,
                error=f"Unexpected extraction pipeline failure: {e}",
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
        data = parse_llm_json_object(raw)
        if data is None:
            raise ValueError(f"No parseable JSON object found in LLM response: {raw[:300]}")
        return data
