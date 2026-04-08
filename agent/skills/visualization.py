from pathlib import Path
from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.base import BaseSkill


class VisualizationSkill(BaseSkill):

    @property
    def name(self) -> SkillName:
        return SkillName.VISUALIZATION

    @property
    def description(self) -> str:
        return "Generate a visualization figure (PDF) of the current cipher's structure."

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "output_dir": {
                "type": "string",
                "required": False,
                "default": "files",
                "description": "Output directory for the figure",
            },
            "filename": {
                "type": "string",
                "required": False,
                "description": "Custom filename (default: {cipher_name}.pdf)",
            },
        }

    def execute(self, request: SkillRequest, session: Session) -> SkillResult:
        import visualisations.visualisations as vis

        cipher = session.get_cipher()
        if cipher is None:
            return SkillResult(
                success=False,
                skill=self.name,
                error="No cipher loaded. Use cipher_instantiation first.",
            )

        params = request.params
        output_dir = Path(params.get("output_dir", "files"))
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = params.get("filename", f"{cipher.name}.pdf")
        filepath = output_dir / filename

        try:
            vis.generate_figure(cipher, filepath)
            return SkillResult(
                success=True,
                skill=self.name,
                data={"filename": str(filepath)},
                summary=f"Generated visualization: {filepath}",
            )
        except Exception as e:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Visualization failed: {e}",
            )
