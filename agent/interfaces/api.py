"""Programmatic API for the OCP agent."""

from typing import Any, Dict, List, Optional, Union

from agent.core import AgentCore
from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills import SkillRegistry, create_default_registry
from agent.skills.cipher_spec import CipherSpec
from agent.skills.cipher_text_input import (
    CipherFacts,
    CipherInput,
    CipherSpecDraft,
    build_cipher_spec_draft,
    parse_cipher_facts_response,
)
from agent.job_records import create_text_job_record, update_job_record
from agent.llm.prompt_templates import build_cipher_facts_extraction_prompt
from agent.llm.provider import LLMProvider


class OCPAgent:
    """High-level API for OCP cryptanalysis tasks.

    Supports two usage patterns:

    1. Direct API (no LLM required):
        agent = OCPAgent()
        agent.instantiate_cipher("speck", "blockcipher", version=[32, 64])
        agent.generate_code(language="python")
        agent.differential_analysis(goal="DIFFERENTIALPATH_PROB", model_type="milp")

    2. Chat with LLM:
        agent = OCPAgent(llm_provider=my_provider)
        response = agent.chat("Analyze SPECK32 with differential cryptanalysis using SAT")
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        skill_registry: Optional[SkillRegistry] = None,
        session: Optional[Session] = None,
    ):
        self._core = AgentCore(
            llm_provider=llm_provider,
            skill_registry=skill_registry or create_default_registry(),
            session=session or Session(),
        )

    @property
    def session(self) -> Session:
        return self._core.session

    def chat(self, message: str) -> str:
        """Send a natural language message and get a response (requires LLM provider)."""
        return self._core.process_message(message)

    def instantiate_cipher(
        self,
        cipher_name: str,
        cipher_type: str = "blockcipher",
        version: Any = None,
        rounds: Optional[int] = None,
    ) -> SkillResult:
        """Instantiate a cipher primitive.

        Args:
            cipher_name: Cipher name (e.g., "speck", "aes", "gift").
            cipher_type: "permutation", "blockcipher", or "keypermutation".
            version: Version parameter (int or list, cipher-dependent).
            rounds: Number of rounds (None for default).

        Returns:
            SkillResult with cipher info.
        """
        params = {"cipher_name": cipher_name, "cipher_type": cipher_type}
        if version is not None:
            params["version"] = version
        if rounds is not None:
            params["rounds"] = rounds
        return self._core.execute_direct(SkillRequest(skill=SkillName.CIPHER_INSTANTIATION, params=params))

    def generate_code(
        self,
        language: str = "python",
        unroll: bool = False,
        test: bool = True,
        output_dir: Optional[str] = None,
    ) -> SkillResult:
        """Generate implementation code for the current cipher.

        Args:
            language: Target language ("python", "c", "verilog").
            unroll: Whether to unroll loops.
            test: Whether to run test vectors.
            output_dir: Output directory.

        Returns:
            SkillResult with generated file info.
        """
        return self._core.execute_direct(SkillRequest(
            skill=SkillName.CODE_GENERATION,
            params={"language": language, "unroll": unroll, "test": test, "output_dir": output_dir},
        ))

    def generate_visualization(
        self,
        output_dir: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> SkillResult:
        """Generate a visualization figure for the current cipher.

        Args:
            output_dir: Output directory.
            filename: Custom filename (default: {cipher_name}.pdf).

        Returns:
            SkillResult with generated file info.
        """
        params = {"output_dir": output_dir}
        if filename is not None:
            params["filename"] = filename
        return self._core.execute_direct(SkillRequest(skill=SkillName.VISUALIZATION, params=params))

    def differential_analysis(
        self,
        goal: str = "DIFFERENTIALPATH_PROB",
        model_type: str = "milp",
        constraints: Optional[List[str]] = None,
        objective_target: str = "OPTIMAL",
        **kwargs,
    ) -> SkillResult:
        """Run differential cryptanalysis on the current cipher.

        Args:
            goal: Analysis goal (e.g., "DIFFERENTIALPATH_PROB", "DIFFERENTIAL_SBOXCOUNT").
            model_type: "milp" or "sat".
            constraints: Constraint list (default: ["INPUT_NOT_ZERO"]).
            objective_target: "OPTIMAL", "EXISTENCE", or "AT MOST N".
            **kwargs: Additional params (input_diff, output_diff, solver, solution_number, show_mode).

        Returns:
            SkillResult with trail data.
        """
        params = {
            "goal": goal,
            "model_type": model_type,
            "constraints": constraints or ["INPUT_NOT_ZERO"],
            "objective_target": objective_target,
        }
        params.update(kwargs)
        return self._core.execute_direct(SkillRequest(skill=SkillName.DIFFERENTIAL_ANALYSIS, params=params))

    def linear_analysis(
        self,
        goal: str = "LINEARPATH_CORR",
        model_type: str = "milp",
        constraints: Optional[List[str]] = None,
        objective_target: str = "OPTIMAL",
        **kwargs,
    ) -> SkillResult:
        """Run linear cryptanalysis on the current cipher.

        Args:
            goal: Analysis goal (e.g., "LINEARPATH_CORR", "LINEAR_SBOXCOUNT").
            model_type: "milp" or "sat".
            constraints: Constraint list (default: ["INPUT_NOT_ZERO"]).
            objective_target: "OPTIMAL", "EXISTENCE", or "AT MOST N".
            **kwargs: Additional params (solver, solution_number, show_mode).

        Returns:
            SkillResult with trail data.
        """
        params = {
            "goal": goal,
            "model_type": model_type,
            "constraints": constraints or ["INPUT_NOT_ZERO"],
            "objective_target": objective_target,
        }
        params.update(kwargs)
        return self._core.execute_direct(SkillRequest(skill=SkillName.LINEAR_ANALYSIS, params=params))

    def define_custom_cipher(self, spec: Union[dict, CipherSpec]) -> SkillResult:
        """Define and build a custom cipher from a CipherSpec.

        Args:
            spec: CipherSpec object or dict describing the cipher.

        Returns:
            SkillResult with the built cipher info.

        Example:
            from agent import OCPAgent, CipherSpec, LayerSpec
            spec = CipherSpec(
                name="MyARX",
                cipher_type="permutation",
                block_size=32, word_bitsize=16, nbr_words=2, nbr_rounds=22,
                round_structure=[
                    LayerSpec("rotation", {"direction": "r", "amount": 7, "word_index": 0}),
                    LayerSpec("modadd", {"input_indices": [[0, 1]], "output_indices": [0]}),
                    LayerSpec("rotation", {"direction": "l", "amount": 2, "word_index": 1}),
                    LayerSpec("xor", {"input_indices": [[0, 1]], "output_indices": [1]}),
                ],
            )
            agent = OCPAgent()
            agent.define_custom_cipher(spec)
            agent.differential_analysis(model_type="milp")
        """
        if isinstance(spec, CipherSpec):
            spec = spec.to_dict()
        return self._core.execute_direct(SkillRequest(
            skill=SkillName.CIPHER_DEFINITION,
            params={"spec": spec},
        ))

    def extract_cipher_facts(
        self,
        text: str,
        source_type: str = "direct_text",
        format_hint: str = "mixed",
        source_name: Optional[str] = None,
        language_hint: str = "unknown",
    ) -> SkillResult:
        """Extract text-first cipher facts with the configured LLM provider."""

        if self._core.llm is None:
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_EXTRACTION,
                error="No LLM provider configured for text-first fact extraction.",
            )

        cipher_input = CipherInput(
            raw_text=text,
            source_type=source_type,
            format_hint=format_hint,
            source_name=source_name,
            language_hint=language_hint,
        )
        input_errors = cipher_input.validate()
        if input_errors:
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_EXTRACTION,
                error="; ".join(input_errors),
            )

        prompt = build_cipher_facts_extraction_prompt(cipher_input)
        try:
            raw_response = self._core.llm.call_llm(prompt)
        except NotImplementedError as exc:
            return SkillResult(success=False, skill=SkillName.CIPHER_EXTRACTION, error=str(exc))

        facts = parse_cipher_facts_response(raw_response)
        if facts is None:
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_EXTRACTION,
                error="LLM response did not contain parseable cipher facts JSON.",
            )

        errors, warnings = facts.validate()
        job = create_text_job_record(
            cipher_input=cipher_input,
            prompt=prompt,
            raw_response=raw_response,
            facts=facts,
            errors=errors,
            warnings=warnings,
            provider=self._core.llm,
        )
        self.session.set_metadata("pending_cipher_facts", facts)
        self.session.set_metadata("pending_text_job", job)
        return SkillResult(
            success=not errors,
            skill=SkillName.CIPHER_EXTRACTION,
            data={
                "facts": facts,
                "validation_errors": errors,
                "warnings": warnings,
                "job": job,
                "artifact_links": job["artifact_links"],
            },
            summary=f"Extracted candidate facts for {facts.name or 'an unnamed cipher'}.",
            error="; ".join(errors) if errors else None,
        )

    def draft_cipher_spec(self, facts: Union[CipherFacts, Dict[str, Any], None] = None) -> CipherSpecDraft:
        """Create a user-reviewable CipherSpec draft from extracted facts."""

        if facts is None:
            facts = self.session.get_metadata("pending_cipher_facts")
        if isinstance(facts, dict):
            facts = CipherFacts.from_dict(facts)
        if not isinstance(facts, CipherFacts):
            raise ValueError("CipherFacts are required to draft a CipherSpec.")

        draft = build_cipher_spec_draft(facts)
        self.session.set_metadata("pending_cipher_spec_draft", draft)
        self.session.set_metadata("pending_cipher_spec", draft.spec)
        job = update_job_record(
            self.session.get_metadata("pending_text_job"),
            draft=draft,
        )
        if job:
            self.session.set_metadata("pending_text_job", job)
        return draft

    def confirm_cipher_spec(self, draft: Optional[Union[CipherSpecDraft, Dict[str, Any]]] = None) -> SkillResult:
        """Confirm and build a reviewed text-first CipherSpec draft."""

        if draft is None:
            draft = self.session.get_metadata("pending_cipher_spec_draft")
        if isinstance(draft, dict):
            draft = CipherSpecDraft(spec=draft)
            draft.validate_spec()
        if not isinstance(draft, CipherSpecDraft):
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_DEFINITION,
                error="No pending CipherSpecDraft is available to confirm.",
            )
        if draft.validation_errors:
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_DEFINITION,
                error="Cannot confirm CipherSpecDraft with validation errors: "
                + "; ".join(draft.validation_errors),
            )

        draft.requires_user_confirmation = False
        self.session.set_metadata("confirmed_cipher_spec", draft.spec)
        result = self.define_custom_cipher(draft.spec)
        job = update_job_record(
            self.session.get_metadata("pending_text_job"),
            confirmation={
                "confirmed": result.success,
                "build_result": {
                    "success": result.success,
                    "summary": result.summary,
                    "error": result.error,
                    "data": result.data,
                },
            },
        )
        if job:
            self.session.set_metadata("pending_text_job", job)
            if isinstance(result.data, dict):
                result.data["job"] = job
                result.data["artifact_links"] = job["artifact_links"]
        return result

    def extract_cipher_from_file(
        self,
        file_path: str,
        focus: Optional[str] = None,
        pages: Optional[str] = None,
        auto_build: bool = False,
    ) -> SkillResult:
        """Experimentally import a cipher specification from a PDF, image, or text file.

        Text-first extraction is preferred for accuracy. File extraction is a
        convenience helper and the resulting draft should be reviewed before use.

        Args:
            file_path: Path to the file (PDF, PNG, JPG, TXT).
            focus: Optional focus area (e.g., "the SPECK cipher", "Section 3").
            pages: For PDFs: page range (e.g., "1-5", "3,7").
            auto_build: If True, automatically build the cipher after extraction.
                This is not recommended for experimental PDF/image imports.

        Returns:
            SkillResult with extracted CipherSpec.

        Example:
            agent = OCPAgent(llm_provider=my_provider)
            agent.extract_cipher_from_file("paper.pdf", focus="the new ARX cipher")
            agent.define_custom_cipher(agent.session.get_metadata("pending_cipher_spec"))
        """
        params = {"file_path": file_path, "auto_build": auto_build}
        if focus:
            params["focus"] = focus
        if pages:
            params["pages"] = pages
        return self._core.execute_direct(SkillRequest(
            skill=SkillName.CIPHER_EXTRACTION,
            params=params,
        ))
