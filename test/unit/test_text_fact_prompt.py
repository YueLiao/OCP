from agent.llm.prompt_templates import build_cipher_facts_extraction_prompt
from agent.llm.prompt_templates import build_parse_prompt
from agent.skills.cipher_text_input import (
    CipherInput,
    CipherFacts,
    validate_cipher_facts,
)


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


def test_empty_operations_with_tables_gives_table_aware_error():
    # The recurring "ingredients without a recipe" failure (real Midori job): tables extracted,
    # `operations` left empty. The error must name the extracted tables + the SPN order so the
    # repair loop and user know exactly what to add - not the generic one-liner.
    facts = CipherFacts.from_dict({
        "name": "Midori", "primitive_type": "blockcipher",
        "cell_layout": {"cell_bits": 4, "nbr_cells": 16},
        "operations": [],
        "tables": {
            "sbox_tables": {"Sb0": list(range(16)), "Sb1": list(range(16))},
            "permutation_tables": {"ShuffleCell": list(range(16))},
            "matrix_tables": {"M": [[0, 1, 1, 1], [1, 0, 1, 1], [1, 1, 0, 1], [1, 1, 1, 0]]},
        },
        "versions": {"Midori64": {"nbr_rounds": 16}, "Midori128": {"nbr_rounds": 20}},
    })
    errors, _ = validate_cipher_facts(facts)
    op_err = next(e for e in errors if "operations" in e)
    assert "Sb0" in op_err and "ShuffleCell" in op_err and "M" in op_err
    assert "canonical order" in op_err
    assert "do NOT leave it empty" in op_err  # versioned-skeleton nudge


def test_empty_operations_without_tables_keeps_generic_error():
    facts = CipherFacts.from_dict({
        "name": "X", "primitive_type": "blockcipher", "operations": [], "tables": {},
        "state": {"block_size": 64, "word_bitsize": 4, "nbr_words": 16},
        "rounds": {"nbr_rounds": 10},
    })
    errors, _ = validate_cipher_facts(facts)
    assert "At least one round operation is required." in errors


def test_parse_prompt_marks_file_extraction_as_experimental():
    prompt = build_parse_prompt(
        "extract this PDF",
        available_skills=[],
        session_context={},
    )

    assert "Experimental File Import" in prompt
    assert '"auto_build": false' in prompt
    assert "Do not set auto_build=true for PDF/image imports." in prompt
