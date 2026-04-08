from abc import ABC, abstractmethod
from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session


class BaseSkill(ABC):

    @property
    @abstractmethod
    def name(self) -> SkillName:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def param_schema(self) -> Dict[str, Any]:
        """Return a dict describing expected parameters and their types."""
        ...

    @abstractmethod
    def execute(self, request: SkillRequest, session: Session) -> SkillResult:
        ...

    def to_descriptor(self) -> dict:
        return {
            "name": self.name.value,
            "description": self.description,
            "params": self.param_schema,
        }
