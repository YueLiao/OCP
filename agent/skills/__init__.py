from typing import Dict, List, Optional

from agent.types import SkillName
from agent.skills.base import BaseSkill


class SkillRegistry:
    """Registry of available skills."""

    def __init__(self):
        self._skills = {}  # type: Dict[SkillName, BaseSkill]

    def register(self, skill: BaseSkill):
        self._skills[skill.name] = skill

    def get(self, name: SkillName) -> Optional[BaseSkill]:
        return self._skills.get(name)

    def list_descriptors(self) -> List[dict]:
        return [skill.to_descriptor() for skill in self._skills.values()]

    def list_skills(self) -> List[BaseSkill]:
        return list(self._skills.values())


def create_default_registry() -> SkillRegistry:
    from agent.skills.cipher_instantiation import CipherInstantiationSkill
    from agent.skills.code_generation import CodeGenerationSkill
    from agent.skills.visualization import VisualizationSkill
    from agent.skills.differential_analysis import DifferentialAnalysisSkill
    from agent.skills.linear_analysis import LinearAnalysisSkill
    from agent.skills.integral_analysis import IntegralAnalysisSkill
    from agent.skills.impossible_differential_analysis import ImpossibleDifferentialAnalysisSkill
    from agent.skills.zero_correlation_analysis import ZeroCorrelationAnalysisSkill
    from agent.skills.two_stage_analysis import TwoStageTrailSearchSkill
    from agent.skills.cipher_definition import CipherDefinitionSkill
    from agent.skills.cipher_dialogue import CipherDialogueSkill
    from agent.skills.cipher_extractor import CipherExtractorSkill
    from agent.skills.operator_capabilities_skill import OperatorCapabilitiesSkill

    registry = SkillRegistry()
    registry.register(CipherInstantiationSkill())
    registry.register(CodeGenerationSkill())
    registry.register(VisualizationSkill())
    registry.register(DifferentialAnalysisSkill())
    registry.register(LinearAnalysisSkill())
    registry.register(IntegralAnalysisSkill())
    registry.register(ImpossibleDifferentialAnalysisSkill())
    registry.register(ZeroCorrelationAnalysisSkill())
    registry.register(TwoStageTrailSearchSkill())
    registry.register(CipherDefinitionSkill())
    registry.register(CipherDialogueSkill())
    registry.register(CipherExtractorSkill())
    registry.register(OperatorCapabilitiesSkill())
    return registry
