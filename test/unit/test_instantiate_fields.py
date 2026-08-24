"""CipherSpec.instantiate() resolves a versioned family into one concrete member by DEEP-COPYING
the whole spec and applying the version's overrides - so every field is carried, not just the
handful a hand-rebuilt CipherSpec used to copy. Regression for a latent bug: instantiate dropped
cell_layout / arx / key_archetype / pre_whitening / post_whitening / key_nbr_rounds and each
layer's only_rounds / except_rounds / phase_params (it was only ever exercised by KNOT, which
uses `layout` - the one field that WAS copied - so nothing caught it).
"""
from agent.skills.cipher_spec import CipherSpec, LayerSpec


def _versioned():
    return CipherSpec(
        name="Fam", cipher_type="blockcipher", nbr_rounds=0,
        cell_layout={"cell_bits": 4, "nbr_cells": 16},
        pre_whitening=True, post_whitening=True, key_nbr_rounds=29,
        key_archetype={"type": "static_alternating", "shares": 2},
        round_structure=[LayerSpec("sbox", {"sbox_name": "S"}, except_rounds=[-1]),
                         LayerSpec("rotation", {"direction": "l", "amount": 1, "word_index": 0},
                                   phase_params=[{"amount": 1}, {"amount": 2}])],
        key_schedule=[LayerSpec("permutation", {"table": [0, 1]}, only_rounds=[1])],
        versions={"A": {"nbr_rounds": 16, "key_size": 128}}, default_version="A")


def test_instantiate_preserves_every_field():
    c = _versioned().instantiate("A")
    assert c.cell_layout == {"cell_bits": 4, "nbr_cells": 16}
    assert c.pre_whitening is True and c.post_whitening is True
    assert c.key_nbr_rounds == 29
    assert c.key_archetype == {"type": "static_alternating", "shares": 2}
    assert c.round_structure[0].except_rounds == [-1]
    assert c.round_structure[1].phase_params == [{"amount": 1}, {"amount": 2}]
    assert c.key_schedule[0].only_rounds == [1]
    # overrides applied, family markers cleared
    assert c.nbr_rounds == 16 and c.key_size == 128
    assert c.versions is None and c.default_version is None


def test_instantiate_reads_scalars_from_params_too():
    # an LLM may place scalars inside "params" instead of the version top level; accept either
    spec = CipherSpec(name="Fam2", cipher_type="blockcipher", nbr_rounds=0,
                      round_structure=[LayerSpec("sbox", {"sbox_name": "S"})],
                      versions={"A": {"params": {"nbr_rounds": 20, "key_size": 64}}},
                      default_version="A")
    c = spec.instantiate("A")
    assert c.nbr_rounds == 20 and c.key_size == 64
