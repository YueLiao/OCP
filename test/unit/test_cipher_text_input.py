from agent.skills.cipher_text_input import CipherInput, CipherSpecDraft, normalize_cipher_text


def test_normalize_cipher_text_preserves_lines_and_rewrites_latex_tokens():
    raw = "x \\leftarrow a \\oplus b\r\n\r\n\r\n y \\gets x \\boxplus k "

    normalized = normalize_cipher_text(raw)

    assert normalized == "x  <-  a  XOR  b\n\n y  <-  x  MODADD  k"


def test_cipher_input_exposes_normalized_text():
    cipher_input = CipherInput(raw_text="A \\rightarrow B", format_hint="latex")

    assert cipher_input.normalized_text == "A  ->  B"


def test_cipher_spec_draft_validity_tracks_validation_errors():
    assert CipherSpecDraft(validation_errors=[]).is_valid
    assert not CipherSpecDraft(validation_errors=["missing rounds"]).is_valid
