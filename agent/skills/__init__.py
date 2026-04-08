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
    from agent.skills.cipher_definition import CipherDefinitionSkill
    from agent.skills.cipher_dialogue import CipherDialogueSkill

    registry = SkillRegistry()
    registry.register(CipherInstantiationSkill())
    registry.register(CodeGenerationSkill())
    registry.register(VisualizationSkill())
    registry.register(DifferentialAnalysisSkill())
    registry.register(LinearAnalysisSkill())
    registry.register(CipherDefinitionSkill())
    registry.register(CipherDialogueSkill())
    return registry
