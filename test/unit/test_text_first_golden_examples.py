import json
from pathlib import Path

from agent.skills.cipher_text_input import (
    CipherFacts,
    CipherInput,
    build_cipher_spec_draft,
)


FIXTURE_DIR = Path("test/fixtures/text_first")


def test_text_first_golden_examples_validate_as_cipher_spec_drafts():
    fixture_paths = sorted(FIXTURE_DIR.glob("*.json"))

    assert {path.name for path in fixture_paths} == {
        "arx_tiny.json",
        "sbox_permutation_tiny.json",
        "spn_tiny.json",
    }

    for path in fixture_paths:
        fixture = json.loads(path.read_text(encoding="utf-8"))
        cipher_input = CipherInput(raw_text=fixture["text"], source_name=path.name)
        facts = CipherFacts.from_dict(fixture["facts"])
        draft = build_cipher_spec_draft(facts)

        assert cipher_input.validate() == []
        assert cipher_input.normalized_text
        assert cipher_input.source_line_spans
        assert draft.is_valid, f"{path.name}: {draft.validation_errors}"
        assert draft.spec["name"] == fixture["facts"]["name"]
