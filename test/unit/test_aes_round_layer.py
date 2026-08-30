"""Build-side coverage for the fused `aes_round` layer_type.

A whole AES round (SubBytes+ShiftRows+MixColumns, no key) is placeable as one
AESround operator over 16-word (128-bit) state groups - the shape used by
AES-based designs like Rocca. These tests are hermetic (no solver / matplotlib):
they only exercise CipherSpec.validate() and the cipher_definition builder.
"""

import pytest

from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cipher_definition import build_permutation_from_spec


def _aes_round_spec(input_indices, output_indices, nbr_rounds=2):
    return CipherSpec(
        name="AESRtest",
        cipher_type="permutation",
        block_size=128,
        word_bitsize=8,
        nbr_words=16,
        nbr_rounds=nbr_rounds,
        round_structure=[
            LayerSpec("aes_round", {"input_indices": input_indices, "output_indices": output_indices})
        ],
    )


def _count_aesround(prim):
    return sum(
        c.__class__.__name__ == "AESround"
        for f in prim.functions.values()
        for rnd in getattr(f, "constraints", [])
        for layer in rnd
        for c in layer
    )


def test_aes_round_validates_clean():
    g = [list(range(16))]
    assert _aes_round_spec(g, g).validate() == []


def test_aes_round_builds_and_places_operator():
    g = [list(range(16))]
    prim = build_permutation_from_spec(_aes_round_spec(g, g, nbr_rounds=2))
    # one AESround per round
    assert _count_aesround(prim) == 2


def test_aes_round_missing_params_flagged_by_validate():
    spec = CipherSpec(
        name="Bad", cipher_type="permutation", block_size=128,
        word_bitsize=8, nbr_words=16, nbr_rounds=1,
        round_structure=[LayerSpec("aes_round", {})],
    )
    errors = spec.validate()
    assert any("aes_round" in e and "input_indices" in e for e in errors)


def test_aes_round_is_an_accepted_layer_type():
    # regression guard: 'aes_round' must be in the validate() whitelist (else drafts
    # using it are rejected as an invalid layer type before they ever reach the builder)
    g = [list(range(16))]
    errors = _aes_round_spec(g, g).validate()
    assert not any("invalid type 'aes_round'" in e for e in errors)


def test_aes_round_rejects_non_16_word_group_at_build():
    # AESround enforces exactly 16 input/output vars; a wrong group size must fail loudly.
    g = [list(range(8))]  # only 8 words, not a full AES state
    spec = _aes_round_spec(g, g, nbr_rounds=1)
    # word-index bounds are fine (0..7 < 16), so validate() passes; the 16-var contract
    # is enforced by the operator at build time.
    with pytest.raises(ValueError, match="16"):
        build_permutation_from_spec(spec)
