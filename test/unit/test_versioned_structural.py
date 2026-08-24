"""Structural per-version overrides: a family whose versions differ in STRUCTURE (not just
scalars) - like Midori64 (1 S-box layer, xor_shares whitening) vs Midori128 (4 position S-box
layers, whole_key whitening) - can carry its own round_structure / key_archetype / sbox_tables
per version. instantiate() uses them, and verify_all_versions KAT-checks every version so a
family is persisted only when ALL versions pass.
"""
from agent.skills.cipher_spec import CipherSpec
from agent.skills.cipher_definition import verify_all_versions, _diagnose_unbuilt_version


def _family(out_a=(2, 6), out_b=(1, 2, 3, 4)):
    return {
        "name": "TwoVer", "cipher_type": "blockcipher", "sbox_tables": {"S": list(range(16))},
        "versions": {
            "A": {"block_size": 8, "word_bitsize": 4, "nbr_words": 2, "nbr_rounds": 1,
                  "key_size": 8, "key_word_bitsize": 4, "key_nbr_words": 2,
                  "key_extract_indices": [0, 1],
                  "round_structure": [{"layer_type": "add_round_key",
                                       "params": {"operator": "xor", "mask": [1, 1]}}],
                  "test_vectors": [{"plaintext": [1, 2], "key": [3, 4], "output": list(out_a)}]},
            "B": {"block_size": 16, "word_bitsize": 4, "nbr_words": 4, "nbr_rounds": 2,
                  "key_size": 16, "key_word_bitsize": 4, "key_nbr_words": 4,
                  "key_extract_indices": [0, 1, 2, 3],
                  "round_structure": [
                      {"layer_type": "add_round_key", "params": {"operator": "xor", "mask": [1, 1, 1, 1]}},
                      {"layer_type": "sbox", "params": {"sbox_name": "S", "index": [[0], [1], [2], [3]]}}],
                  "test_vectors": [{"plaintext": [1, 2, 3, 4], "key": [5, 6, 7, 8], "output": list(out_b)}]},
        },
        "default_version": "A",
    }


def test_instantiate_uses_per_version_structure():
    cs = CipherSpec.from_dict(_family())
    a, b = cs.instantiate("A"), cs.instantiate("B")
    assert [l.layer_type for l in a.round_structure] == ["add_round_key"]
    assert a.nbr_words == 2 and a.nbr_rounds == 1
    assert [l.layer_type for l in b.round_structure] == ["add_round_key", "sbox"]
    assert b.nbr_words == 4 and b.nbr_rounds == 2


def test_verify_all_versions_all_pass():
    res = verify_all_versions(CipherSpec.from_dict(_family()))
    assert set(res) == {"A", "B"}
    assert all(r["tested"] and r["all_passed"] for r in res.values())


def test_verify_all_versions_flags_one_wrong():
    # Version B has a wrong expected output -> B fails, so the family is not all-verified.
    res = verify_all_versions(CipherSpec.from_dict(_family(out_b=(0, 0, 0, 0))))
    assert res["A"]["all_passed"] is True
    assert res["B"]["all_passed"] is False
    assert not all(r["tested"] and r["all_passed"] for r in res.values())


def test_sbox_tables_merge_across_base_and_version():
    spec = _family()
    spec["sbox_tables"] = {"BASE": list(range(16))}          # base holds a shared table
    spec["versions"]["B"]["sbox_tables"] = {"S": list(range(16))}  # version adds its own
    b = CipherSpec.from_dict(spec).instantiate("B")
    assert "BASE" in b.sbox_tables and "S" in b.sbox_tables    # merged, not replaced


def test_diagnose_unbuilt_version_reports_wrong_size_sbox():
    # A version whose bigger cell reuses the small default S-box (Midori128-class): the diagnosis
    # must name the size gap and tell the user to supply the version's own table - not "?".
    spec = {
        "name": "SizeFam", "cipher_type": "blockcipher", "sbox_tables": {"S4": list(range(16))},
        "default_version": "small",
        "versions": {
            "small": {"block_size": 8, "word_bitsize": 4, "nbr_words": 2, "nbr_rounds": 1,
                      "key_size": 8, "key_word_bitsize": 4, "key_nbr_words": 2,
                      "round_structure": [{"layer_type": "sbox",
                                           "params": {"sbox_name": "S4", "index": [[0], [1]]}}]},
            "big": {"block_size": 16, "word_bitsize": 8, "nbr_words": 2, "nbr_rounds": 1,
                    "key_size": 16, "key_word_bitsize": 8, "key_nbr_words": 2,
                    "round_structure": [{"layer_type": "sbox",
                                         "params": {"sbox_name": "S4", "index": [[0], [1]]}}]},
        },
    }
    hint = _diagnose_unbuilt_version(CipherSpec.from_dict(spec), "big")
    assert "8-bit cells" in hint and "16 entries" in hint and "256-entry" in hint


def test_diagnose_unbuilt_version_reports_missing_named_sbox():
    # The version's params name an S-box (Midori128's 'SSb') the tables never define.
    spec = {
        "name": "NameFam", "cipher_type": "blockcipher", "sbox_tables": {"Sb0": list(range(16))},
        "default_version": "v64",
        "versions": {
            "v64": {"block_size": 8, "word_bitsize": 4, "nbr_words": 2, "nbr_rounds": 1,
                    "key_size": 8, "key_word_bitsize": 4, "key_nbr_words": 2,
                    "params": {"sbox_name": "Sb0"},
                    "round_structure": [{"layer_type": "sbox",
                                         "params": {"sbox_name": "Sb0", "index": [[0], [1]]}}]},
            "v128": {"block_size": 8, "word_bitsize": 4, "nbr_words": 2, "nbr_rounds": 1,
                     "key_size": 8, "key_word_bitsize": 4, "key_nbr_words": 2,
                     "params": {"sbox_name": "SSb"},
                     "round_structure": [{"layer_type": "sbox",
                                          "params": {"sbox_name": "Sb0", "index": [[0], [1]]}}]},
        },
    }
    hint = _diagnose_unbuilt_version(CipherSpec.from_dict(spec), "v128")
    assert "SSb" in hint and "Provide" in hint


def test_non_versioned_spec_has_no_version_results():
    spec = {"name": "Solo", "cipher_type": "permutation", "block_size": 8, "word_bitsize": 4,
            "nbr_words": 2, "nbr_rounds": 1,
            "round_structure": [{"layer_type": "xor",
                                 "params": {"input_indices": [[0, 1]], "output_indices": [1]}}]}
    assert verify_all_versions(CipherSpec.from_dict(spec)) == {}
