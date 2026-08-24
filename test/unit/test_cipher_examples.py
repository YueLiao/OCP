"""Regression: the few-shot example specs must build and pass their test vectors,
so they stay a trustworthy on-prompt format reference."""

import io
from contextlib import redirect_stdout

from agent.skills.cipher_spec import CipherSpec
from agent.skills.cipher_definition import (
    build_permutation_from_spec,
    build_blockcipher_from_spec,
    verify_cipher_test_vectors,
    _normalize_test_vectors,
)
from agent.skills.cipher_examples import (
    EXAMPLE_SPECS,
    few_shot_facts_text,
    select_examples,
)
from agent.skills.cipher_readback import spec_readback


def _verify(spec_dict):
    spec = CipherSpec.from_dict(spec_dict)
    if spec.layout:  # bit-sliced layout -> concrete word_bitsize=1 spec
        spec = spec.expand_bitsliced()
    spec.test_vectors = _normalize_test_vectors(spec.test_vectors, spec.cipher_type)
    assert spec.validate() == []
    build = (
        build_blockcipher_from_spec
        if spec.cipher_type == "blockcipher"
        else build_permutation_from_spec
    )
    cipher = build(spec)
    with redirect_stdout(io.StringIO()):
        return verify_cipher_test_vectors(cipher, spec)


def test_example_specs_build_and_pass_test_vectors():
    for name, spec in EXAMPLE_SPECS.items():
        result = _verify(spec)
        assert result["tested"] and result["all_passed"], f"{name}: {result}"


def test_select_examples_by_family():
    assert "speck32" in select_examples("rotate word 0 right by 7, modular add words 0 and 1")
    assert "mini_spn" in select_examples("apply a 4-bit s-box to each word then permute")
    block = select_examples("s-box each word, then add the round key; key schedule permutes key words")
    assert "mini_block" in block and len(block) <= 2
    assert select_examples("") == ["speck32", "mini_spn"]


def test_few_shot_is_dynamic_and_has_anti_copy():
    text = few_shot_facts_text("rotate and modular add")
    assert "do not copy" in text
    # dynamic selection must not dump all four examples
    assert not all(name in text for name in ("SPECK32", "SIMON32", "MiniSPN", "MiniBlock"))


def test_readback_covers_examples():
    for spec in EXAMPLE_SPECS.values():
        text = spec_readback(spec)
        assert "Each round:" in text and "unknown" not in text.lower()
