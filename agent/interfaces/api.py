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
from solving.solving import solver_capabilities


# Confusion/diffusion layers that ARE the cipher: dropping one makes the definition still
# build but compute the wrong value (the Midori "MixColumn vanished -> all-zero output"
# failure). The auto-repair, which optimizes for "pass validation", must never reduce their
# count to silence a test-vector mismatch. Key/constant additions (add_round_key,
# add_constant) and fillers (add_identity) are deliberately excluded - de-duplicating a
# redundant key addition is a legitimate repair.
_CRITICAL_LAYER_TYPES = frozenset({
    "sbox", "permutation", "matrix", "gf2_linear", "linear_diffusion",
    "rotation", "shift", "and", "or", "andxor", "modadd",
})


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
        orchestrate: bool = False,
    ):
        self._core = AgentCore(
            llm_provider=llm_provider,
            skill_registry=skill_registry or create_default_registry(),
            session=session or Session(),
            orchestrate=orchestrate,
        )

    @property
    def session(self) -> Session:
        return self._core.session

    def chat(self, message: str) -> str:
        """Send a natural language message and get a response (requires LLM provider)."""
        return self._core.process_message(message)

    def solver_capabilities(self) -> Dict[str, Any]:
        """Return optional MILP/SAT backend availability before running analysis."""
        return solver_capabilities()

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

    def integral_analysis(self, constant_bits: List[int], **kwargs) -> SkillResult:
        """Search for an integral (division-property) distinguisher on the current cipher.

        MILP-only. `constant_bits` are the input bit positions held constant (the rest are
        active/summed). Extra kwargs: active_bits, show_mode, solver, solution_number.
        """
        params: Dict[str, Any] = {"constant_bits": constant_bits}
        params.update(kwargs)
        return self._core.execute_direct(SkillRequest(skill=SkillName.INTEGRAL_ANALYSIS, params=params))

    def impossible_differential_analysis(self, model_type: str = "milp", **kwargs) -> SkillResult:
        """Search for an impossible-differential distinguisher on the current cipher.

        `model_type` is 'milp' or 'sat'. Extra kwargs: show_mode, solver, solution_number.
        """
        params: Dict[str, Any] = {"model_type": model_type}
        params.update(kwargs)
        return self._core.execute_direct(
            SkillRequest(skill=SkillName.IMPOSSIBLE_DIFFERENTIAL_ANALYSIS, params=params))

    def zero_correlation_analysis(self, model_type: str = "milp", **kwargs) -> SkillResult:
        """Search for a zero-correlation linear distinguisher on the current cipher.

        `model_type` is 'milp' or 'sat'. Extra kwargs: show_mode, solver, solution_number.
        """
        params: Dict[str, Any] = {"model_type": model_type}
        params.update(kwargs)
        return self._core.execute_direct(
            SkillRequest(skill=SkillName.ZERO_CORRELATION_ANALYSIS, params=params))

    def two_stage_trail_search(
        self,
        cipher_name: str,
        rounds: int,
        *,
        cipher_type: str = "blockcipher",
        version: Any = None,
        goal: str = "DIFFERENTIALPATH_PROB",
        **kwargs,
    ) -> SkillResult:
        """Two-stage (truncated then bit-level) optimal trail search for a word-oriented cipher.

        Unlike the other analyses this rebuilds the named cipher per stage, so it takes
        cipher_name/type/version/rounds rather than the loaded cipher. goal is
        DIFFERENTIALPATH_PROB or LINEARPATH_CORR.
        """
        params: Dict[str, Any] = {
            "cipher_name": cipher_name, "rounds": rounds,
            "cipher_type": cipher_type, "goal": goal,
        }
        if version is not None:
            params["version"] = version
        params.update(kwargs)
        return self._core.execute_direct(SkillRequest(skill=SkillName.TWO_STAGE_TRAIL_SEARCH, params=params))

    def define_custom_cipher(
        self,
        spec: Union[dict, CipherSpec],
        version: Any = None,
        rounds: Optional[int] = None,
    ) -> SkillResult:
        """Define and build a custom cipher from a CipherSpec.

        Args:
            spec: CipherSpec object or dict describing the cipher.
            version: For a parameterized family, which version to build (defaults
                to the spec's default_version).
            rounds: Round count to build; None uses the design's full rounds (the
                chosen version's nbr_rounds for a family).

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
        params: Dict[str, Any] = {"spec": spec}
        if version is not None:
            params["version"] = version
        if rounds is not None:
            params["rounds"] = rounds
        return self._core.execute_direct(SkillRequest(
            skill=SkillName.CIPHER_DEFINITION,
            params=params,
        ))

    def classify_cipher_architecture(self, cipher_input) -> Optional[Dict[str, Any]]:
        """Stage 1 of extraction: a cheap LLM pass that labels the cipher's STRUCTURAL archetype
        (standard_spn / bitsliced_spn / cell_sliced_spn / arx / feistel / gfn / reflection_spn /
        unknown) so the formalize pass builds the right representation rather than defaulting to a
        repeated SPN. Returns the classification dict, or None on any failure - extraction then
        proceeds un-targeted (the previous single-pass behavior), so this never blocks a build."""
        if self._core.llm is None:
            return None
        from agent.llm.prompt_templates import (
            build_cipher_classification_prompt, CIPHER_ARCHETYPES,
        )
        from agent.llm.response_parser import parse_llm_json_object
        try:
            raw = self._core.llm.call_llm(build_cipher_classification_prompt(cipher_input))
            result = parse_llm_json_object(raw)
        except Exception:
            return None
        if not isinstance(result, dict) or result.get("archetype") not in CIPHER_ARCHETYPES:
            return None
        return result

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
        # Keep the source text so the auto-repair loop can lazily generate a reference oracle
        # (Tier 1b) when the OCP KAT fails.
        self.session.set_metadata("pending_source_text", cipher_input.normalized_text)
        input_errors = cipher_input.validate()
        if input_errors:
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_EXTRACTION,
                error="; ".join(input_errors),
            )

        # Stage 1: classify the cipher's structural archetype so the formalize prompt targets
        # the right representation (instead of defaulting to a repeated SPN). Never fatal - a
        # failed/absent classification just falls back to un-targeted extraction.
        classification = self.classify_cipher_architecture(cipher_input)
        prompt = build_cipher_facts_extraction_prompt(cipher_input, classification)
        try:
            raw_response = self._core.llm.call_llm(prompt)
        except NotImplementedError as exc:
            return SkillResult(success=False, skill=SkillName.CIPHER_EXTRACTION, error=str(exc))
        except (RuntimeError, OSError, ValueError) as exc:
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_EXTRACTION,
                error=f"LLM provider call failed during text-first fact extraction: {exc}",
            )
        except Exception as exc:
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_EXTRACTION,
                error=f"Unexpected LLM provider failure during text-first fact extraction: {exc}",
            )

        try:
            facts = parse_cipher_facts_response(raw_response)
        except (TypeError, ValueError) as exc:
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_EXTRACTION,
                error=f"LLM response parsing failed during text-first fact extraction: {exc}",
            )
        if facts is None:
            # Save the raw reply so the failure can be inspected; a truncated or
            # non-JSON response is the usual cause.
            debug_path = None
            try:
                from tools.paths import get_files_dir
                debug_path = get_files_dir("agent_jobs") / "last_failed_extraction.txt"
                debug_path.write_text(raw_response or "", encoding="utf-8")
            except OSError:
                debug_path = None
            stripped = (raw_response or "").rstrip()
            # A valid facts reply is multi-KB JSON. A very short reply that isn't even
            # JSON (e.g. "not json") means the model misfired, not that the input was
            # too big - point at retrying rather than trimming the input.
            if stripped and len(stripped) < 40 and not stripped.lstrip().startswith(("{", "[")):
                hint = (f" The model returned an unusually short reply ({stripped!r}) instead "
                        "of JSON - usually a transient LLM error, rate limit, or quota issue. "
                        "Try again; if it persists, check the API key and credits.")
            elif stripped and not stripped.endswith("}"):
                hint = (" The response looks truncated - trim the input to the specification "
                        "section, or the model's output limit was hit.")
            else:
                hint = ""
            saved = f" Raw response saved to {debug_path}." if debug_path else ""
            return SkillResult(
                success=False,
                skill=SkillName.CIPHER_EXTRACTION,
                error=f"LLM response did not contain parseable cipher facts JSON.{hint}{saved}",
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
            classification=classification,
        )
        self.session.set_metadata("pending_cipher_facts", facts)
        self.session.set_metadata("pending_text_job", job)
        return SkillResult(
            success=not errors,
            skill=SkillName.CIPHER_EXTRACTION,
            data={
                "facts": facts,
                "classification": classification,
                "validation_errors": errors,
                "warnings": warnings,
                "job": job,
                "artifact_links": job["artifact_links"],
            },
            summary=f"Extracted candidate facts for {facts.name or 'an unnamed cipher'}.",
            error="; ".join(errors) if errors else None,
        )

    def request_cancel(self):
        """Signal any in-progress multi-step LLM work (e.g. the draft auto-repair loop) to
        stop at its next checkpoint. Set by the Stop button (/api/stop) so the user cancels
        further token use between LLM calls (a single in-flight call can't be interrupted)."""
        self.session.set_metadata("cancel_requested", True)

    def is_cancelled(self) -> bool:
        return bool(self.session.get_metadata("cancel_requested"))

    def reset_cancel(self):
        self.session.set_metadata("cancel_requested", False)

    def draft_cipher_spec(self, facts: Union[CipherFacts, Dict[str, Any], None] = None) -> CipherSpecDraft:
        """Create a user-reviewable CipherSpec draft from extracted facts."""

        if facts is None:
            facts = self.session.get_metadata("pending_cipher_facts")
        if isinstance(facts, dict):
            facts = CipherFacts.from_dict(facts)
        if not isinstance(facts, CipherFacts):
            raise ValueError("CipherFacts are required to draft a CipherSpec.")

        draft = build_cipher_spec_draft(facts)
        # Self-repair: if the draft has blocking problems and an LLM is connected, let the
        # model fix them itself (showing the fixes) rather than handing them to the user.
        self.reset_cancel()
        draft = self._auto_repair_draft(draft)
        self.session.set_metadata("pending_cipher_spec_draft", draft)
        self.session.set_metadata("pending_cipher_spec", draft.spec)
        job = update_job_record(
            self.session.get_metadata("pending_text_job"),
            draft=draft,
        )
        if job:
            self.session.set_metadata("pending_text_job", job)
        return draft

    def _auto_repair_draft(self, draft: CipherSpecDraft, max_attempts: int = 6) -> CipherSpecDraft:
        """Iteratively let the LLM fix a draft's own validation problems.

        Each round feeds the current spec + its concrete problems back to the model and
        re-validates the result, recording the before/after in draft.repair_log so the
        user sees what was found and fixed. Stops when the draft is clean, when a round
        makes no progress (same problem set), when repair fails, or after max_attempts.
        """
        if self._core.llm is None:
            return draft

        ref_cache: Dict[str, Any] = {}   # lazily-generated reference code, shared across attempts

        def _reference_hint(spec_dict):
            # Tier 1b: on an OCP KAT mismatch, generate a reference oracle ONCE and localize the
            # first diverging round (or flag a paper-understanding problem). Fully best-effort -
            # any failure (no source text, no LLM, sandbox error) just skips the hint.
            try:
                if "code" not in ref_cache:
                    text = self.session.get_metadata("pending_source_text")
                    ref_cache["code"] = self.generate_reference(text) if text else None
                if not ref_cache["code"]:
                    return None
                return self.reference_repair_hint(spec_dict, ref_cache["code"])
            except Exception:
                return None

        def problems_of(d):
            # Structural validation errors first; when the spec is structurally clean, a
            # test-vector mismatch (0/N) is ALSO a problem to repair - a valid-looking spec
            # can still be the wrong cipher (e.g. a missing add_round_key layer).
            probs = list(d.validation_errors)
            if probs:
                return probs
            kat = self._kat_problems(d.spec)
            # A genuine KAT MISMATCH (builds + runs but wrong output) is where a reference oracle
            # helps: append the first-divergence localization so repair fixes ONE round, not blind.
            if kat and any(("test vectors" in p or "does not match" in p) for p in kat):
                hint = _reference_hint(d.spec)
                if hint:
                    kat = kat + [hint]
            return kat

        problems = problems_of(draft)
        if not problems:
            return draft
        for attempt in range(1, max_attempts + 1):
            if self.is_cancelled():  # user pressed Stop - don't spend tokens on more rounds
                draft.repair_log.append({"attempt": attempt, "cancelled": True})
                break
            try:
                corrected = self.repair_cipher_spec(draft.spec, problems)
            except Exception as exc:  # unparseable/failed repair - stop, keep the draft
                draft.repair_log.append(
                    {"attempt": attempt, "problems_before": problems, "error": str(exc)}
                )
                break
            # Guardrail: reject a "fix" that gutted the algorithm (deleted a core layer,
            # edited the KATs, or changed word granularity) rather than actually repairing it.
            # Keep the pre-repair spec and re-ask with the violation as a hard constraint.
            violations = OCPAgent._repair_guardrail_violations(draft.spec, corrected)
            if violations:
                draft.repair_log.append({
                    "attempt": attempt,
                    "problems_before": problems,
                    "rejected_repair": violations,
                })
                problems = problems_of(draft) + [
                    f"HARD CONSTRAINT - your last fix violated this and was discarded: {m}"
                    for m in violations
                ]
                continue
            new_draft = CipherSpecDraft(spec=corrected)
            new_draft.repair_log = draft.repair_log
            new_draft.validate_spec()
            new_draft.warnings = draft.warnings
            new_draft.assumptions = draft.assumptions
            remaining = problems_of(new_draft)
            new_draft.repair_log.append({
                "attempt": attempt,
                "problems_before": problems,
                "problems_after": list(remaining),
                "resolved": [p for p in problems if p not in remaining],
            })
            draft = new_draft
            if not remaining:
                break
            if set(remaining) == set(problems):  # no progress - avoid a useless loop
                break
            problems = remaining
        return draft

    def _kat_problems(self, spec_dict: Dict[str, Any]) -> List[str]:
        """Preflight the spec exactly as confirm will: try to BUILD it and run its KATs, and
        return a repairable problem for EITHER failure mode. A build/codegen exception is NOT
        swallowed (the old behaviour let a spec that passed static validation but crashed the
        builder reach the user as 'no problems', then fail at confirm) - it is returned as a
        repair problem so the auto-repair loop and the user see it up front. Empty only when
        there are no test vectors or the vectors pass."""
        import io
        from contextlib import redirect_stdout
        from agent.skills.cipher_spec import CipherSpec
        from agent.skills.cipher_definition import (
            build_blockcipher_from_spec, build_permutation_from_spec,
            verify_cipher_test_vectors, _normalize_test_vectors, _effective_word_sizes,
            _effective_state_counts, _drop_cross_variant_vectors, _concise_traceback,
        )
        try:
            spec = CipherSpec.from_dict(spec_dict)
            _wb, _kwb = _effective_word_sizes(spec)
            spec.test_vectors = _normalize_test_vectors(
                spec.test_vectors, spec.cipher_type, _wb, _kwb)
            # Drop other-variant KATs here too (not only at confirm), so the repair loop is not
            # driven by a vector it can never satisfy and must not edit.
            _ns, _nk = _effective_state_counts(spec)
            spec.test_vectors, _ = _drop_cross_variant_vectors(
                spec.test_vectors, _ns, _nk, spec.cipher_type)
            if not spec.test_vectors:
                return []
            with redirect_stdout(io.StringIO()):
                cipher = (build_blockcipher_from_spec(spec) if spec.cipher_type == "blockcipher"
                          else build_permutation_from_spec(spec))
                res = verify_cipher_test_vectors(cipher, spec)
        except Exception as exc:
            tb = _concise_traceback()
            return [f"The definition passes static validation but FAILS to build/generate: "
                    f"{type(exc).__name__}: {exc}. The traceback below points at the failing "
                    f"OPERATOR/LAYER (the last frame's file/function names its type - e.g. "
                    f"AddConstantLayer -> an add_constant layer, MatrixLayer -> a matrix layer); "
                    f"fix THAT layer's parameters (commonly a matrix dimension != its index-group "
                    f"length, an index outside the state, or a round-indexed table shorter than "
                    f"nbr_rounds):\n{tb}"]
        if res.get("all_passed"):
            return []
        if not res.get("tested"):
            # codegen failure is a real, often-fixable problem (a table shorter than nbr_rounds,
            # an index the generator walks past) - surface it WITH the traceback so repair can
            # localize the failing layer, don't treat it as "no problem".
            if res.get("reason") == "codegen_failed":
                tb = res.get("traceback", "")
                return [f"The definition builds but code GENERATION fails "
                        f"({res.get('error', '')}), so its test vectors could not run. The "
                        f"traceback names the failing layer/operator - fix that layer (usually a "
                        f"round-indexed table shorter than nbr_rounds, or an index walked past the "
                        f"end):" + (f"\n{tb}" if tb else "")]
            return []
        passed, total = res.get("passed", 0), res.get("total", 0)
        fail = (res.get("failures") or [{}])[0]
        if fail.get("expected") is not None and fail.get("computed") is not None:
            detail = (f" First failing vector: expected {fail['expected']}, got {fail['computed']}."
                      " Check that EVERY key addition is present (an add_round_key layer XORing the"
                      " subkey each round), the layer order and round count match the spec, and any"
                      " round constants / whitening are included.")
        elif fail.get("error"):
            detail = f" First vector raised: {fail['error']}."
            if fail.get("traceback"):
                detail += (f" The traceback names the failing layer/operator - fix that layer:"
                           f"\n{fail['traceback']}")
        else:
            detail = ""
        return [f"The definition builds and validates, but only {passed}/{total} test vectors "
                f"pass - it does not match the intended cipher.{detail}"]

    def generate_reference(self, text: str) -> Optional[str]:
        """Tier-1b block 1/2: ask the LLM for a plain-Python STRAIGHT-LINE reference cipher (run by
        the sandbox's run_reference). LAZY - meant to be called only when the OCP KAT fails, as a
        SEPARATE focused call (0 tokens on the happy path). Returns the code, or None."""
        if self._core.llm is None:
            return None
        from agent.llm.prompt_templates import build_cipher_reference_prompt
        from agent.skills.cipher_text_input import CipherInput
        try:
            raw = self._core.llm.call_llm(build_cipher_reference_prompt(CipherInput(raw_text=text)))
        except Exception:
            return None
        if not raw:
            return None
        code = raw.strip()
        if code.startswith("```"):                       # strip a ```python ... ``` fence if present
            code = code.split("\n", 1)[-1]
            if code.rstrip().endswith("```"):
                code = code.rsplit("```", 1)[0]
        return code

    def reference_repair_hint(self, spec_dict: Dict[str, Any], reference_code: str) -> Optional[str]:
        """Tier-1b blocks 3/5/6 (deterministic): given a reference cipher, KAT-verify it, then EITHER
        return the first-divergence localization (reference passes but the OCP model is wrong -> an
        ENCODING problem, localized to a round) OR an 'understanding' warning (the reference ALSO
        fails the KAT -> the paper understanding is wrong, not the OCP encoding). None if unavailable.
        """
        if not reference_code:
            return None
        import io as _io
        from contextlib import redirect_stdout as _rs
        from agent.skills.cipher_spec import CipherSpec
        from agent.skills.cipher_definition import (
            build_blockcipher_from_spec, build_permutation_from_spec, verify_reference,
            localize_divergence, _normalize_test_vectors, _effective_word_sizes,
            _effective_state_counts, _drop_cross_variant_vectors,
        )
        try:
            spec = CipherSpec.from_dict(spec_dict)
            wb, kwb = _effective_word_sizes(spec)
            spec.test_vectors = _normalize_test_vectors(spec.test_vectors, spec.cipher_type, wb, kwb)
            ns, nk = _effective_state_counts(spec)
            spec.test_vectors, _ = _drop_cross_variant_vectors(spec.test_vectors, ns, nk, spec.cipher_type)
            if not spec.test_vectors:
                return None
            vr = verify_reference(reference_code, spec)
            if not vr["all_passed"]:
                f = (vr["failures"] or [{}])[0]
                return ("A plain-Python REFERENCE implementation written independently from the paper "
                        f"ALSO fails the KAT (expected {f.get('expected')}, got {f.get('computed')}"
                        f"{' / ' + f.get('error') if f.get('error') else ''}) - so the failure is in "
                        "UNDERSTANDING the cipher (its structure / constants / key schedule), NOT just "
                        "the OCP encoding. Re-check the extracted facts against the paper.")
            with _rs(_io.StringIO()):
                cipher = (build_blockcipher_from_spec(spec) if spec.cipher_type == "blockcipher"
                          else build_permutation_from_spec(spec))
            return localize_divergence(cipher, spec, reference_code)
        except Exception:
            return None

    @staticmethod
    def _repair_guardrail_violations(before: Dict[str, Any], after: Dict[str, Any]) -> List[str]:
        """Forbidden mutations an auto-repair must never make.

        The repair loop optimizes for "make validation pass", which tempts the LLM to silence
        a stubborn test-vector mismatch by gutting the algorithm instead of fixing it: deleting
        the layer it can't get right, editing the known-answer vectors to match a wrong output,
        or shrinking the word size so a cross-word rotation "fits". Each of those produces a
        cipher that builds but is WRONG. We detect them by diffing the corrected spec against
        the pre-repair spec and reject the correction, feeding the reason back as a hard
        constraint. Returns human-readable violation strings; empty when the fix is allowed.
        """
        v: List[str] = []

        # These guardrails protect ESTABLISHED values from destructive edits; they must NOT
        # fire when repair is FILLING IN a missing/degenerate value (word_bitsize 0 -> 4,
        # empty round_structure -> real layers, no vectors -> added). A degenerate draft (the
        # common bad extraction) needs the repair to build it up, not be frozen.

        # A. Test vectors are the paper's ground truth - repair must not EDIT existing ones.
        if before.get("test_vectors") and after.get("test_vectors") != before.get("test_vectors"):
            v.append(
                "You changed test_vectors. The known-answer vectors are ground truth from the "
                "paper and must stay byte-for-byte identical. Fix the ROUND STRUCTURE to match "
                "them; never edit the vectors to match a wrong structure.")

        # B. Don't drop confusion/diffusion layers (the 'MixColumn vanished -> zeros' failure).
        def crit_counts(spec: Dict[str, Any]) -> Dict[str, int]:
            counts: Dict[str, int] = {}
            for layer in spec.get("round_structure") or []:
                t = layer.get("type") if isinstance(layer, dict) else None
                if t in _CRITICAL_LAYER_TYPES:
                    counts[t] = counts.get(t, 0) + 1
            return counts

        cb, ca = crit_counts(before), crit_counts(after)
        dropped = sorted(t for t in cb if ca.get(t, 0) < cb[t])
        if dropped:
            v.append(
                f"You removed or reduced core layer(s) {dropped} from round_structure. S-box, "
                f"MixColumn/matrix, permutation, rotation/shift and nonlinear layers ARE the "
                f"algorithm - deleting one makes the cipher build but compute the wrong value. "
                f"Keep every one and fix the failing layer's PARAMETERS instead.")

        # C. Word/cell granularity is a fixed fact of the cipher, not a knob to pass validation
        #    (the FUTURE 'word_bitsize 4 -> 1' failure). A cross-word rotation belongs in a
        #    cell_layout / bit-sliced model, not a shrunken word size.
        for field in ("word_bitsize", "key_word_bitsize"):
            b, a = before.get(field), after.get(field)
            # Only guard an ESTABLISHED positive size; 0/None is an unset value the repair is
            # allowed to fill in (a degenerate extraction had word_bitsize 0, and blocking the
            # 0 -> 4 fill froze the whole repair loop).
            if isinstance(b, int) and b > 0 and a != b:
                v.append(
                    f"You changed {field} from {b} to {a}. The word/cell size is fixed by the "
                    f"cipher's definition; do not change operation granularity to silence an "
                    f"error. Model a cross-word rotation with cell_layout/bit-slicing instead.")
        return v

    def repair_cipher_spec(self, spec: Dict[str, Any], problems: List[str]) -> Dict[str, Any]:
        """Ask the LLM to fix a specific CipherSpec given concrete problems.

        A targeted correction (current spec + the exact validation/test-vector
        failures) instead of a full re-extraction. Returns the corrected spec dict.
        """
        if not isinstance(spec, dict):
            raise ValueError("spec must be a JSON object.")
        return self._core._repair_spec(spec, problems)

    def resolve_clarification(self, user_message: str) -> Optional[SkillResult]:
        """Apply the user's answer to an open build clarification (e.g. a missing S-box) and
        rebuild. Returns the rebuild SkillResult, or None if nothing is pending / the message is
        not a resolution. See AgentCore.resolve_pending_clarification."""
        return self._core.resolve_pending_clarification(user_message)

    def pending_clarification(self):
        """The currently-open clarification (dict) the agent is waiting on, or None."""
        return self.session.get_metadata("pending_clarification")

    def add_test_vectors_to_draft(self, tv_data: Any) -> CipherSpecDraft:
        """Inject test vectors (parsed JSON: per-version map or a plain list) into the
        pending text-first draft and re-validate, so Build can verify correctness."""
        from agent.skills.cipher_text_input import merge_test_vectors_into_spec

        draft = self.session.get_metadata("pending_cipher_spec_draft")
        if not isinstance(draft, CipherSpecDraft) or not draft.spec:
            raise ValueError("No pending cipher draft to add test vectors to.")
        merged = merge_test_vectors_into_spec(draft.spec, tv_data)
        return self.revise_cipher_spec_draft(merged)

    def revise_cipher_spec_draft(self, spec: Dict[str, Any]) -> CipherSpecDraft:
        """Replace the pending text-first draft with a manually edited CipherSpec payload."""

        if not isinstance(spec, dict):
            raise ValueError("Edited CipherSpec draft must be a JSON object.")
        draft = CipherSpecDraft(spec=spec)
        draft.validate_spec()
        self.session.set_metadata("pending_cipher_spec_draft", draft)
        self.session.set_metadata("pending_cipher_spec", draft.spec)
        job = update_job_record(
            self.session.get_metadata("pending_text_job"),
            draft=draft,
            manual_revision={"source": "user_spec_edit"},
        )
        if job:
            self.session.set_metadata("pending_text_job", job)
        return draft

    def confirm_cipher_spec(
        self,
        draft: Optional[Union[CipherSpecDraft, Dict[str, Any]]] = None,
        version: Any = None,
        rounds: Optional[int] = None,
    ) -> SkillResult:
        """Confirm and build a reviewed text-first CipherSpec draft.

        version/rounds let the user pick a family member and round count at build
        time; rounds=None builds the design's full rounds (the version default).
        """

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

        confirmed_draft = CipherSpecDraft(
            spec=draft.spec,
            validation_errors=list(draft.validation_errors),
            warnings=list(draft.warnings),
            assumptions=list(draft.assumptions),
            clarification_questions=list(draft.clarification_questions),
            requires_user_confirmation=False,
        )
        self.session.set_metadata("confirmed_cipher_spec", confirmed_draft.spec)
        result = self.define_custom_cipher(confirmed_draft.spec, version=version, rounds=rounds)
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

    def build_and_verify_cipher(self, spec: Union[CipherSpec, Dict[str, Any]], *, max_attempts: int = 3):
        """Build a cipher from `spec` and verify it against its test vectors, repairing on a
        KAT failure, via the AgentController harness.

        Runs a one-step plan [build -> KAT gate -> repair] through the generic controller: the
        cipher is built (define_custom_cipher, which also runs the KAT), the objective verdict
        is read, and on a mismatch the spec is handed to repair_cipher_spec (LLM) and the build
        retried, up to `max_attempts`. Without an LLM there is no repair, so a KAT failure fails
        the run with the mismatch reported. Honors the session cancel flag between attempts.

        This is the first end-to-end goal wired onto the agentic harness; later phases add
        analysis / report steps to the same engine. Returns a controller RunReport; on success
        the built cipher is on the session (session.get_cipher()).
        """
        from agent.controller import AgentController, Step, ActionResult, definition_verdict_gate

        spec_dict = spec.to_dict() if isinstance(spec, CipherSpec) else dict(spec)

        def build_action(ctx):
            result = self.define_custom_cipher(ctx["spec"])
            ctx["cipher"] = self.session.get_cipher()
            return ActionResult(ok=bool(result.success), data=result.data,
                                summary=result.summary, error=result.error)

        def repair(ctx, problems, attempt):
            if self._core.llm is None:
                return False                          # no repair capability without an LLM
            fixed = self.repair_cipher_spec(ctx["spec"], problems)
            if not fixed or fixed == ctx["spec"]:
                return False                          # no-progress: nothing changed
            ctx["spec"] = fixed
            return True

        step = Step("build", action=build_action, gate=definition_verdict_gate, repair=repair)
        controller = AgentController(
            session=self.session, is_cancelled=self.is_cancelled, max_attempts=max_attempts,
        )
        return controller.run("build a KAT-verified cipher", [step], ctx={"spec": spec_dict})

    def run_analysis_verified(
        self,
        goal: str,
        *,
        analysis: str = "differential",
        model_type: str = "milp",
        backend_fallback: bool = True,
        max_attempts: int = 2,
        **kwargs,
    ):
        """Run a cryptanalysis on the current cipher via the AgentController, falling back to
        another installed solver backend if the requested one errors.

        `analysis` selects the family ('differential' or 'linear'); `goal` / `model_type` /
        extra kwargs pass through to that analysis. On a solver-or-model error the step is
        repaired by swapping model_type to an installed alternate backend (milp <-> sat) not yet
        tried, up to `max_attempts` - the common "no MILP solver here, fall back to SAT" case. A
        run that REACHES a verdict passes the gate: finding no distinguisher (0 trails / UNSAT)
        is a valid result, not a failure; only a self-inconsistent trail set is rejected.

        Returns a controller RunReport; the analysis result data is on the passing step's
        outcome.data (and the final backend used is in the run's ctx).
        """
        from agent.controller import (
            AgentController, Step, ActionResult, analysis_verdict_gate, make_backend_fallback_repair,
        )

        family = (analysis or "differential").lower()
        runners = {
            "differential": self.differential_analysis,
            "linear": self.linear_analysis,
            "impossible": self.impossible_differential_analysis,
            "zero_correlation": self.zero_correlation_analysis,
        }
        if family not in runners:
            raise ValueError(f"Unknown analysis '{analysis}'. Use one of {sorted(runners)}.")
        run = runners[family]
        # impossible / zero-correlation fix their goal internally (IMPOSSIBLETRUNCATEDDIFF /
        # ZEROCORRELATIONTRUNCATEDLINEAR) and take no `goal` kwarg; only diff/linear accept it.
        takes_goal = family in ("differential", "linear")

        def analyze_action(ctx):
            if self.session.get_cipher() is None:
                return ActionResult(ok=False, error="no cipher loaded; build one first")
            call = dict(ctx["kwargs"])
            call["model_type"] = ctx["model_type"]
            if takes_goal:
                call["goal"] = ctx["goal"]
            result = run(**call)
            return ActionResult(ok=bool(result.success), data=result.data,
                                summary=result.summary, error=result.error)

        step = Step(
            f"{family}_analysis",
            action=analyze_action,
            gate=analysis_verdict_gate,
            repair=make_backend_fallback_repair() if backend_fallback else None,
        )
        controller = AgentController(
            session=self.session, is_cancelled=self.is_cancelled, max_attempts=max_attempts,
        )
        return controller.run(
            f"{family} analysis ({goal})", [step],
            ctx={"goal": goal, "model_type": model_type, "kwargs": kwargs},
        )

    def run_pipeline(self, requests, *, goal: str = "multi-step pipeline", max_attempts: int = 3):
        """Run a list of SkillRequests as a verified multi-step pipeline through the controller.

        Each request becomes a Step whose objective gate + repair come from the default skill
        registry (a build gets the KAT verdict gate, an analysis gets the verdict gate + solver
        backend fallback). State flows between steps via the session - e.g. a cipher a definition
        step builds is read from the session by a later analysis step. A required step that fails
        after its repair budget halts the pipeline. Returns a controller RunReport.

        `requests` items are SkillRequests, or {"skill": SkillName|str, "params": {...}} dicts.
        """
        from agent.controller import AgentController, plan_from_requests

        normalized = [self._as_skill_request(r) for r in requests]
        repair_spec = self.repair_cipher_spec if self._core.llm is not None else None
        plan = plan_from_requests(normalized, execute=self._core.execute_direct, repair_spec=repair_spec)
        controller = AgentController(
            session=self.session, is_cancelled=self.is_cancelled, max_attempts=max_attempts,
        )
        return controller.run(goal, plan, ctx={})

    def run_recipe(self, name: str, *, max_attempts: int = 3, **kwargs):
        """Run a named recipe (a canned SkillRequest pipeline) through the controller.

        e.g. run_recipe("build_and_analyze", spec=my_spec) builds the cipher then runs
        differential + linear trail search on it. See agent/recipes.py for available recipes.
        Extra kwargs pass through to the recipe. Returns a controller RunReport.
        """
        from agent.recipes import build_recipe
        return self.run_pipeline(build_recipe(name, **kwargs), goal=f"recipe: {name}",
                                 max_attempts=max_attempts)

    @staticmethod
    def _as_skill_request(item) -> SkillRequest:
        """Coerce a SkillRequest / dict / (skill, params) into a SkillRequest."""
        if isinstance(item, SkillRequest):
            return item
        if isinstance(item, dict):
            skill = item["skill"]
            skill = skill if isinstance(skill, SkillName) else SkillName(skill)
            return SkillRequest(skill=skill, params=item.get("params") or {})
        if isinstance(item, (tuple, list)) and len(item) == 2:
            skill, params = item
            skill = skill if isinstance(skill, SkillName) else SkillName(skill)
            return SkillRequest(skill=skill, params=params or {})
        raise ValueError(f"Cannot interpret {item!r} as a SkillRequest.")

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
