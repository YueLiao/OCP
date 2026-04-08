"""OCP Agent Framework - Automated cryptanalysis through natural language or programmatic API.

Usage (Direct API, no LLM):
    from agent import OCPAgent
    agent = OCPAgent()
    agent.instantiate_cipher("speck", "blockcipher", version=[32, 64])
    agent.generate_code(language="python")
    agent.differential_analysis(goal="DIFFERENTIALPATH_PROB", model_type="milp")

Usage (Chat with LLM):
    from agent import OCPAgent
    from my_llm import MyLLMProvider
    agent = OCPAgent(llm_provider=MyLLMProvider())
    response = agent.chat("Analyze SPECK32 with differential and linear cryptanalysis")

Usage (CLI):
    from agent import run_cli
    from my_llm import MyLLMProvider
    run_cli(MyLLMProvider())
"""

from agent.types import SkillName, SkillRequest, SkillResult, UserIntent
from agent.session import Session
from agent.core import AgentCore
from agent.skills import SkillRegistry, create_default_registry
from agent.skills.base import BaseSkill
from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.llm.provider import LLMProvider
from agent.interfaces.api import OCPAgent
from agent.interfaces.cli import run_cli

__all__ = [
    "OCPAgent",
    "AgentCore",
    "Session",
    "LLMProvider",
    "SkillName",
    "SkillRequest",
    "SkillResult",
    "UserIntent",
    "SkillRegistry",
    "BaseSkill",
    "CipherSpec",
    "LayerSpec",
    "create_default_registry",
    "run_cli",
]
