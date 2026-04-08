"""Programmatic API for the OCP agent."""

from typing import Any, Dict, List, Optional

from agent.core import AgentCore
from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills import SkillRegistry, create_default_registry
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
        output_dir: str = "files",
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
        output_dir: str = "files",
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
