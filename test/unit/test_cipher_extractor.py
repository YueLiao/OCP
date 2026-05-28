from agent.session import Session
from agent.skills.cipher_extractor import (
    EXPERIMENTAL_FILE_EXTRACTION_NOTE,
    CipherExtractorSkill,
)
from agent.types import SkillRequest


def test_cipher_extractor_is_marked_experimental(tmp_path):
    file_path = tmp_path / "cipher.md"
    file_path.write_text("x <- y", encoding="utf-8")
    skill = CipherExtractorSkill()
    request = SkillRequest(skill=skill.name, params={"file_path": str(file_path)})

    result = skill.execute(request, Session())

    assert result.success
    assert result.data["experimental"] is True
    assert result.data["auto_build"] is False
    assert EXPERIMENTAL_FILE_EXTRACTION_NOTE in result.summary
    assert "experimental" in skill.description.lower()
