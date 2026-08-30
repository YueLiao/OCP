"""End-to-end coverage for the `tweakey_lfsr` key archetype (SKINNY/Deoxys tweakey).

The archetype lowers a compact declaration (branches, per-branch cell permutation,
per-branch LFSR matrices, subkey cell count) into an EVOLVING key_schedule +
key_extract_indices, leaving the data-path round_structure (its mid-round add_round_key
included) untouched. The KAT tests prove correctness by rebuilding real SKINNY-64 from
the archetype and checking it reproduces the built-in cipher's test vectors across all
three tweakey sizes (TK1 / TK1+TK2 / TK1+TK2+TK3), which exercises the no-LFSR,
single-LFSR + 2-share XOR, and dual-LFSR + 3-share N_XOR combine paths.

Hermetic: only builds a Python implementation and evaluates it (no solver / matplotlib).
"""

import pytest

from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cipher_definition import build_blockcipher_from_spec, verify_cipher_test_vectors

# --- SKINNY-64 constants (from primitives/skinny.py, the KAT oracle) ---
SKINNY_4BIT_SBOX = [12, 6, 9, 0, 1, 10, 2, 11, 3, 8, 5, 13, 4, 14, 7, 15]
SKINNY_P_T = [9, 15, 8, 13, 10, 14, 12, 11, 0, 1, 2, 3, 4, 5, 6, 7]
MAT1 = [[0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1], [1, 1, 0, 0]]   # TK2 LFSR (4-bit)
MAT2 = [[1, 0, 0, 1], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]   # TK3 LFSR (4-bit)
_RC = [0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3E, 0x3D, 0x3B, 0x37, 0x2F, 0x1E, 0x3C, 0x39, 0x33,
       0x27, 0x0E, 0x1D, 0x3A, 0x35, 0x2B, 0x16, 0x2C, 0x18, 0x30, 0x21, 0x02, 0x05, 0x0B,
       0x17, 0x2E, 0x1C, 0x38, 0x31, 0x23, 0x06, 0x0D, 0x1B, 0x36, 0x2D, 0x1A, 0x34, 0x29,
       0x12, 0x24, 0x08, 0x11, 0x22, 0x04, 0x09, 0x13, 0x26, 0x0c, 0x19, 0x32, 0x25, 0x0a,
       0x15, 0x2a, 0x14, 0x28, 0x10, 0x20]


def _const_table(nbr_rounds):
    return [[rc & 0xF, rc >> 4, 0x2] for rc in _RC[:nbr_rounds]]


def _skinny64_spec(key_size, branches, lfsr_matrices, nbr_rounds, test_vectors):
    """A SKINNY-64 block-cipher spec whose tweakey schedule comes from the archetype."""
    return CipherSpec(
        name=f"SkinnyArch64_{key_size}",
        cipher_type="blockcipher",
        block_size=64, word_bitsize=4, nbr_words=16, nbr_rounds=nbr_rounds,
        key_size=key_size, key_word_bitsize=4, key_nbr_words=branches * 16,
        sbox_tables={"skinny4": SKINNY_4BIT_SBOX},
        key_archetype={
            "type": "tweakey_lfsr",
            "branches": branches,
            "cells_per_branch": 16,
            "subkey_cells": 8,
            "permutation": SKINNY_P_T,
            "lfsr_matrices": lfsr_matrices,
        },
        round_structure=[
            LayerSpec("sbox", {"sbox_name": "skinny4", "index": [[i] for i in range(16)]}),
            LayerSpec("add_constant", {"add_type": "xor",
                                       "constant_mask": [True, None, None, None, True, None, None, None, True],
                                       "constant_table": _const_table(nbr_rounds)}),
            LayerSpec("add_round_key", {"operator": "xor", "mask": [1] * 8}),
            LayerSpec("permutation", {"table": [0, 1, 2, 3, 7, 4, 5, 6, 10, 11, 8, 9, 13, 14, 15, 12]}),
            LayerSpec("matrix", {"matrix": [[1, 0, 1, 1], [1, 0, 0, 0], [0, 1, 1, 0], [1, 0, 1, 0]],
                                 "indices": [[0, 4, 8, 12], [1, 5, 9, 13], [2, 6, 10, 14], [3, 7, 11, 15]]}),
        ],
        test_vectors=test_vectors,
    )


# (version, branches, lfsr_matrices) covering TK1 / TK1+TK2 / TK1+TK2+TK3
_KAT_CASES = [
    ([64, 64], 1, [None]),
    ([64, 128], 2, [None, MAT1]),
    ([64, 192], 3, [None, MAT1, MAT2]),
]


@pytest.mark.parametrize("version,branches,lfsr_matrices", _KAT_CASES,
                         ids=["TK1", "TK1+TK2", "TK1+TK2+TK3"])
def test_tweakey_lfsr_reproduces_skinny64(version, branches, lfsr_matrices):
    from primitives.skinny import SKINNY_BLOCKCIPHER
    ref = SKINNY_BLOCKCIPHER(r=None, version=version)   # the KAT oracle
    spec = _skinny64_spec(version[1], branches, lfsr_matrices, ref.nbr_rounds, ref.test_vectors)
    assert spec.validate() == []
    result = verify_cipher_test_vectors(build_blockcipher_from_spec(spec), spec)
    assert result.get("all_passed"), result


def test_tweakey_lfsr_expands_to_expected_schedule():
    spec = _skinny64_spec(128, 2, [None, MAT1], nbr_rounds=4, test_vectors=None)
    expanded = spec.expand_key_archetype()
    # key_schedule = one full-state permutation, then a gf2_linear LFSR on TK2's top 8 cells
    assert [l.layer_type for l in expanded.key_schedule] == ["permutation", "gf2_linear"]
    perm = expanded.key_schedule[0].params["table"]
    assert perm[:16] == SKINNY_P_T                       # TK1 block
    assert perm[16:] == [16 + p for p in SKINNY_P_T]     # TK2 block, offset by 16
    lfsr = expanded.key_schedule[1].params
    assert lfsr["index_in"] == list(range(16, 24)) and lfsr["matrix"] == MAT1
    # subkey = XOR of each branch's top-8 cells; archetype/schedule are consumed
    assert expanded.key_extract_indices == [{"xor": [list(range(0, 8)), list(range(16, 24))]}]
    assert expanded.key_archetype is None


def test_single_branch_extract_is_plain_not_xor():
    spec = _skinny64_spec(64, 1, [None], nbr_rounds=4, test_vectors=None)
    expanded = spec.expand_key_archetype()
    assert expanded.key_extract_indices == list(range(8))   # flat top-8, no xor-combine
    assert [l.layer_type for l in expanded.key_schedule] == ["permutation"]  # TK1 has no LFSR


def test_tweakey_lfsr_requires_add_round_key_in_round_structure():
    spec = _skinny64_spec(64, 1, [None], nbr_rounds=4, test_vectors=None)
    spec.round_structure = [l for l in spec.round_structure if l.layer_type != "add_round_key"]
    errors = spec.validate()
    assert any("add_round_key" in e for e in errors)


def test_tweakey_lfsr_rejects_hand_written_key_schedule():
    spec = _skinny64_spec(64, 1, [None], nbr_rounds=4, test_vectors=None)
    spec.key_schedule = [LayerSpec("permutation", {"table": list(range(16))})]
    errors = spec.validate()
    assert any("key_schedule" in e for e in errors)


def test_tweakey_lfsr_branch_cell_mismatch_errors():
    # branches*cells_per_branch must equal the key word count
    spec = _skinny64_spec(64, 2, [None, MAT1], nbr_rounds=4, test_vectors=None)
    spec.key_nbr_words = 16   # says 16 key words but branches*cells = 32
    errors = spec.validate()
    assert any("cells_per_branch" in e or "key word" in e for e in errors)


def test_unknown_archetype_type_is_rejected():
    spec = _skinny64_spec(64, 1, [None], nbr_rounds=4, test_vectors=None)
    spec.key_archetype = {"type": "nonsense"}
    errors = spec.validate()
    assert any("unknown type" in e or "Key-archetype expansion failed" in e for e in errors)
