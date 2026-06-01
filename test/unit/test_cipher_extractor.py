from agent.session import Session
from agent.skills.cipher_extractor import (
    EXPERIMENTAL_FILE_EXTRACTION_NOTE,
    CipherExtractorSkill,
    parse_page_range,
)
from agent.skills.cipher_file_reader import detect_file_type, read_cipher_file
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


def test_cipher_extractor_rejects_invalid_page_ranges(tmp_path):
    file_path = tmp_path / "cipher.pdf"
    file_path.write_bytes(b"%PDF-1.4\n")
    skill = CipherExtractorSkill()
    request = SkillRequest(skill=skill.name, params={"file_path": str(file_path), "pages": "3-1"})

    result = skill.execute(request, Session())

    assert not result.success
    assert result.error.startswith("Invalid page range")


def test_parse_page_range_rejects_empty_and_non_positive_segments():
    assert parse_page_range("1-3,5") == {1, 2, 3, 5}

    for pages in ("1,,2", "0", "2-0", "a", "1-b"):
        try:
            parse_page_range(pages)
        except ValueError as exc:
            assert str(exc)
        else:
            raise AssertionError(f"Expected invalid page range {pages!r} to fail")


def test_cipher_file_reader_supports_text_and_tex(tmp_path):
    file_path = tmp_path / "cipher.tex"
    file_path.write_text(r"x_0 \\leftarrow x_1", encoding="utf-8")

    file_type = detect_file_type(str(file_path))
    content = read_cipher_file(str(file_path), file_type)

    assert file_type == "text"
    assert content.full_text == r"x_0 \\leftarrow x_1"
