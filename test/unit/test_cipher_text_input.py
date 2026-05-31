from agent.skills.cipher_text_input import (
    CipherFacts,
    CipherInput,
    CipherSpecDraft,
    build_cipher_spec_draft,
    normalize_cipher_text,
    normalize_cipher_text_with_spans,
    parse_cipher_facts_response,
    validate_cipher_facts,
)


def test_normalize_cipher_text_preserves_lines_and_rewrites_latex_tokens():
    raw = "x \\leftarrow a \\oplus b\r\n\r\n\r\n y \\gets x \\boxplus k "

    normalized = normalize_cipher_text(raw)

    assert normalized == "x  <-  a  XOR  b\n\n y  <-  x  MODADD  k"


def test_normalize_cipher_text_returns_line_spans_for_non_empty_lines():
    raw = "  x \\leftarrow a\r\n\r\n\r\n y \\gets x "

    normalized, spans = normalize_cipher_text_with_spans(raw)

    assert normalized == "x  <-  a\n\n y  <-  x"
    assert spans == [
        {
            "line_start": 1,
            "line_end": 1,
            "column_start": 3,
            "column_end": 16,
            "text": "  x  <-  a",
        },
        {
            "line_start": 4,
            "line_end": 4,
            "column_start": 2,
            "column_end": 10,
            "text": " y  <-  x",
        },
    ]


def test_cipher_input_exposes_normalized_text():
    cipher_input = CipherInput(raw_text="A \\rightarrow B", format_hint="latex")

    assert cipher_input.normalized_text == "A  ->  B"
    assert cipher_input.source_line_spans == [
        {
            "line_start": 1,
            "line_end": 1,
            "column_start": 1,
            "column_end": 15,
            "text": "A  ->  B",
        }
    ]


def test_cipher_spec_draft_validity_tracks_validation_errors():
    assert CipherSpecDraft(validation_errors=[]).is_valid
    assert not CipherSpecDraft(validation_errors=["missing rounds"]).is_valid


def test_cipher_input_validation_rejects_empty_or_unknown_metadata():
    cipher_input = CipherInput(raw_text="", source_type="pdf", format_hint="scan", language_hint="fr")

    errors = cipher_input.validate()

    assert "Cipher input text is required." in errors
    assert "Unsupported source_type" in errors[1]
    assert "Unsupported format_hint" in errors[2]
    assert "Unsupported language_hint" in errors[3]


def test_validate_cipher_facts_accepts_complete_arx_facts():
    facts = CipherFacts(
        name="TinyARX",
        primitive_type="permutation",
        state={"block_size": 32, "word_bitsize": 16, "nbr_words": 2},
        rounds={"nbr_rounds": 4},
        operations=[
            {"type": "rotation", "params": {"direction": "r", "amount": 7, "word_index": 0}},
            {"type": "modadd", "params": {"input_indices": [[0, 1]], "output_indices": [0]}},
            {"type": "xor", "params": {"input_indices": [[0, 1]], "output_indices": [1]}},
        ],
    )

    errors, warnings = validate_cipher_facts(facts)

    assert errors == []
    assert warnings == []


def test_validate_cipher_facts_reports_blocking_schema_errors():
    facts = CipherFacts(
        name=None,
        primitive_type="stream",
        state={"block_size": 31, "word_bitsize": 16, "nbr_words": 2},
        rounds={"nbr_rounds": 0},
        operations=[{"type": "unknown"}],
        tables={"sbox_tables": {"S": [0, "x", 2]}},
    )

    errors, _ = validate_cipher_facts(facts)

    assert "Cipher name is missing." in errors
    assert "primitive_type must be 'permutation' or 'blockcipher'." in errors
    assert "State size must equal word_bitsize * nbr_words." in errors
    assert "Round count nbr_rounds/num_rounds must be a positive integer." in errors
    assert "Operation 0 has unsupported type 'unknown'." in errors
    assert "S-box table 'S' length must be a power of two." in errors
    assert "S-box table 'S' must contain non-negative integers." in errors


def test_build_cipher_spec_draft_maps_facts_to_cipher_spec_payload():
    facts = CipherFacts(
        name="TinyARX",
        primitive_type="permutation",
        state={"state_size_bits": 32, "unit_size_bits": 16, "num_units": 2},
        rounds={"num_rounds": 4},
        operations=[
            {
                "type": "rotation",
                "params": {"direction": "r", "amount": 7, "word_index": 0},
                "assumption": "right rotation uses the paper's word ordering",
            }
        ],
        ambiguities=["bit numbering is not explicit"],
    )

    draft = build_cipher_spec_draft(facts)

    assert draft.is_valid
    assert draft.requires_user_confirmation is True
    assert draft.spec["name"] == "TinyARX"
    assert draft.spec["block_size"] == 32
    assert draft.spec["round_structure"] == [
        {
            "layer_type": "rotation",
            "params": {"direction": "r", "amount": 7, "word_index": 0},
        }
    ]
    assert draft.assumptions == ["right rotation uses the paper's word ordering"]
    assert draft.warnings == [
        "Operation 0 depends on assumption: right rotation uses the paper's word ordering.",
        "Ambiguity: bit numbering is not explicit",
    ]
    assert draft.clarification_questions == ["Please resolve the listed ambiguities before building the cipher."]


def test_cipher_spec_draft_validate_spec_refreshes_errors():
    draft = CipherSpecDraft(spec={"name": "Broken", "round_structure": []})

    errors = draft.validate_spec()

    assert "round_structure must have at least one layer." in errors
    assert draft.validation_errors == errors


def test_parse_cipher_facts_response_handles_wrapped_llm_json():
    raw = """```json
    {
      "cipher_facts": {
        "name": "TinyARX",
        "primitive_type": "permutation",
        "state": {"block_size": 32, "word_bitsize": 16, "nbr_words": 2},
        "rounds": {"nbr_rounds": 4},
        "operations": [{"type": "xor", "params": {"input_indices": [[0, 1]], "output_indices": [1]}}],
        "ambiguities": ["word ordering is implied"],
      },
    }
    ```"""

    facts = parse_cipher_facts_response(raw)

    assert facts is not None
    assert facts.name == "TinyARX"
    assert facts.operations[0]["type"] == "xor"
    assert facts.ambiguities == ["word ordering is implied"]
