from agent.llm.prompt_templates import build_cipher_facts_extraction_prompt
from agent.llm.prompt_templates import build_parse_prompt
from agent.skills.cipher_text_input import CipherInput


def test_build_cipher_facts_extraction_prompt_uses_normalized_text_and_schema():
    cipher_input = CipherInput(
        raw_text=r"x_0 \leftarrow x_0 \oplus k",
        source_type="direct_text",
        format_hint="latex",
        language_hint="mixed",
    )

    prompt = build_cipher_facts_extraction_prompt(cipher_input)

    assert "Return ONLY valid JSON" in prompt
    assert '"cipher_facts"' in prompt
    assert "source_type: direct_text" in prompt
    assert "x_0  <-  x_0  XOR  k" in prompt
    assert r"\oplus" not in prompt


def test_parse_prompt_marks_file_extraction_as_experimental():
    prompt = build_parse_prompt(
        "extract this PDF",
        available_skills=[],
        session_context={},
    )

    assert "Experimental File Import" in prompt
    assert '"auto_build": false' in prompt
    assert "Do not set auto_build=true for PDF/image imports." in prompt
