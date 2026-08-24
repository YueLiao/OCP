"""CipherSpec.compile() is the ONE canonical lowering chain (code params -> ARX / archetype /
linear_diffusion / cell layout / whitening). build_permutation, build_blockcipher, the primitive
exporter (both paths) and derive_permutation all call it, so the expansion order can't drift
between them. Each step is a no-op when not applicable, so one order serves permutations and
block ciphers. (The rest of the opinion - an immutable NormalizedCipherSpec + dry-build graph +
folding validate into the same entry - is a larger refactor left for later.)
"""
from agent.skills.cipher_spec import CipherSpec, LayerSpec


def test_compile_lowers_a_declarative_cell_layout_to_concrete_bit_layers():
    spec = CipherSpec(
        name="C", cipher_type="blockcipher", nbr_rounds=2,
        cell_layout={"cell_bits": 4, "nbr_cells": 4},
        key_size=16, key_word_bitsize=1, key_nbr_words=16, key_extract_indices=list(range(16)),
        sbox_tables={"S": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
        round_structure=[LayerSpec("subcell_sbox", {"sbox_name": "S"}),
                         LayerSpec("add_round_key", {"operator": "xor", "mask": [1] * 16})])
    concrete = spec.compile()
    # the cell layout is lowered to a word_bitsize=1 bit-level spec with concrete layer types
    assert concrete.word_bitsize == 1 and concrete.cell_layout is None
    assert all(l.layer_type in ("sbox", "matrix", "permutation", "add_round_key", "add_constant",
                                "n_xor", "xor")
               for l in concrete.round_structure)


def test_compile_is_a_noop_for_an_already_concrete_spec():
    spec = CipherSpec(name="P", cipher_type="permutation", block_size=8, word_bitsize=4,
                      nbr_words=2, nbr_rounds=1,
                      round_structure=[LayerSpec("xor", {"input_indices": [[0, 1]],
                                                         "output_indices": [1]})])
    concrete = spec.compile()
    assert [l.layer_type for l in concrete.round_structure] == ["xor"]
    assert concrete.word_bitsize == 4 and concrete.nbr_words == 2
