"""Deterministic fixes for two recurring extraction defects:
  - a cell-level cipher whose cell_layout got nested inside `layout` (FUTURE);
  - cross-variant test vectors (a LEA-192 key vector left in a LEA-128 build).
Both are decided purely from declared sizes/keys, so they run before the LLM repair.
"""
from agent.skills.cipher_text_input import apply_deterministic_fixes


class TestLayoutDeconfusion:
    def test_nested_cell_layout_is_hoisted(self):
        spec = {
            "cipher_type": "blockcipher",
            "layout": {"cell_layout": {"cell_bits": 4, "nbr_cells": 16}},
            "round_structure": [{"layer_type": "subcell_sbox", "params": {"sbox_name": "S"}}],
        }
        out, notes = apply_deterministic_fixes(spec)
        assert out.get("cell_layout") == {"cell_bits": 4, "nbr_cells": 16}
        assert "layout" not in out
        assert any("cell_layout" in n for n in notes)

    def test_cell_keys_directly_under_layout_hoisted(self):
        spec = {
            "cipher_type": "blockcipher",
            "layout": {"cell_bits": 4, "nbr_cells": 16},
            "round_structure": [{"layer_type": "mixcolumn", "params": {}}],
        }
        out, _ = apply_deterministic_fixes(spec)
        assert out.get("cell_layout") == {"cell_bits": 4, "nbr_cells": 16}
        assert "layout" not in out

    def test_real_bitsliced_layout_untouched(self):
        # A genuine bit-sliced layout (rows/cols, no cell keys, no cell ops) must be left alone.
        spec = {
            "cipher_type": "permutation",
            "layout": {"rows": 4, "cols": 64},
            "round_structure": [{"layer_type": "sbox", "params": {"sbox_name": "S"}}],
        }
        out, notes = apply_deterministic_fixes(spec)
        assert out.get("layout") == {"rows": 4, "cols": 64}
        assert "cell_layout" not in out
        assert not any("cell_layout" in n for n in notes)


class TestGenericToCellNativeConversion:
    """cell_layout present but the round uses generic word layers (the FUTURE-class defect):
    a per-cell `sbox`, a GF(2^cell_bits) `matrix` and a cell `permutation` must be rewritten to
    subcell_sbox / mixcolumn / cell_shiftrow, which are the only layers expand_cell_sliced lowers.
    """

    def _future_round(self):
        return [
            {"layer_type": "sbox",
             "params": {"sbox_name": "S", "index": [[i] for i in range(16)]}},
            {"layer_type": "matrix",
             "params": {"indices": [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]],
                        "matrix": [[8, 9, 1, 8], [3, 2, 9, 9], [2, 3, 8, 9], [9, 9, 8, 1]],
                        "polynomial": "0x3"}},
            {"layer_type": "permutation",
             "params": {"table": [0, 13, 10, 7, 4, 1, 14, 11, 8, 5, 2, 15, 12, 9, 6, 3]}},
            {"layer_type": "add_round_key", "params": {"operator": "xor", "mask": [1] * 64}},
        ]

    def test_generic_layers_converted_to_cell_native(self):
        spec = {
            "cipher_type": "blockcipher",
            "cell_layout": {"cell_bits": 4, "nbr_cells": 16},
            "sbox_tables": {"S": [1, 3, 0, 2, 7, 14, 4, 13, 9, 10, 12, 6, 15, 5, 8, 11]},
            "round_structure": self._future_round(),
        }
        out, notes = apply_deterministic_fixes(spec)
        types = [l["layer_type"] for l in out["round_structure"]]
        assert types == ["subcell_sbox", "mixcolumn", "cell_shiftrow", "add_round_key"]
        # mixcolumn keeps the integer GF matrix and gains `columns` (from `indices`).
        mc = out["round_structure"][1]["params"]
        assert mc["matrix"] == [[8, 9, 1, 8], [3, 2, 9, 9], [2, 3, 8, 9], [9, 9, 8, 1]]
        assert mc["columns"] == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]
        assert mc["polynomial"] == "0x3"
        assert out["round_structure"][2]["params"]["table"][:3] == [0, 13, 10]
        assert any("cell-native" in n for n in notes)

    def test_no_cell_layout_is_noop(self):
        # Word-level Midori (no cell_layout): generic sbox/matrix/permutation stay generic.
        spec = {
            "cipher_type": "blockcipher",
            "word_bitsize": 4, "nbr_words": 16,
            "sbox_tables": {"S": list(range(16))},
            "round_structure": self._future_round(),
        }
        out, notes = apply_deterministic_fixes(spec)
        assert [l["layer_type"] for l in out["round_structure"]][0] == "sbox"
        assert not any("cell-native" in n for n in notes)

    def test_real_bit_permutation_untouched(self):
        # A genuine bit permutation (nc*cb = 64 wide) must NOT be read as a cell permutation.
        spec = {
            "cipher_type": "blockcipher",
            "cell_layout": {"cell_bits": 4, "nbr_cells": 16},
            "sbox_tables": {},
            "round_structure": [
                {"layer_type": "permutation", "params": {"table": list(range(64))}},
            ],
        }
        out, notes = apply_deterministic_fixes(spec)
        assert out["round_structure"][0]["layer_type"] == "permutation"
        assert not any("cell-native" in n for n in notes)


class TestVariantVectorFiltering:
    def _lea128(self, vectors):
        return {
            "cipher_type": "blockcipher",
            "block_size": 128, "word_bitsize": 32, "nbr_words": 4,
            "key_size": 128, "key_word_bitsize": 32, "key_nbr_words": 4,
            "round_structure": [{"layer_type": "add_round_key", "params": {}}],
            "test_vectors": vectors,
        }

    def test_drops_lea192_key_vector_from_lea128(self):
        spec = self._lea128([
            {"plaintext": [0, 0, 0, 0], "key": [0, 0, 0, 0], "output": [1, 2, 3, 4]},
            {"plaintext": [0, 0, 0, 0], "key": [0, 0, 0, 0, 0, 0], "output": [5, 6, 7, 8]},  # 6-word key = LEA-192
        ])
        out, notes = apply_deterministic_fixes(spec)
        assert len(out["test_vectors"]) == 1
        assert out["test_vectors"][0]["key"] == [0, 0, 0, 0]
        assert any("different variant" in n or "Dropped" in n for n in notes)

    def test_drops_by_hex_length(self):
        spec = self._lea128([
            {"plaintext": "0x00000000000000000000000000000000", "key": "0x00000000000000000000000000000000", "output": "0x0"*1},
            # 192-bit key hex (48 nibbles) -> 6 words -> dropped
            {"plaintext": "0x00000000000000000000000000000000",
             "key": "0x" + "0" * 48,
             "output": "0x00000000000000000000000000000000"},
        ])
        # give the first a valid output hex too
        spec["test_vectors"][0]["output"] = "0x00000000000000000000000000000000"
        out, _ = apply_deterministic_fixes(spec)
        assert len(out["test_vectors"]) == 1

    def test_keeps_all_when_none_match_declared_size(self):
        # If NO vector matches the declared size, the SIZE is likely wrong - surface it, don't
        # silently discard every vector.
        spec = self._lea128([
            {"plaintext": [0] * 6, "key": [0] * 6, "output": [0] * 6},
            {"plaintext": [0] * 6, "key": [0] * 6, "output": [0] * 6},
        ])
        out, notes = apply_deterministic_fixes(spec)
        assert len(out["test_vectors"]) == 2
        assert not any("Dropped" in n for n in notes)

    def test_all_matching_vectors_untouched(self):
        spec = self._lea128([
            {"plaintext": [0, 0, 0, 0], "key": [0, 0, 0, 0], "output": [1, 2, 3, 4]},
            {"plaintext": [1, 1, 1, 1], "key": [2, 2, 2, 2], "output": [5, 6, 7, 8]},
        ])
        out, notes = apply_deterministic_fixes(spec)
        assert len(out["test_vectors"]) == 2
        assert not any("Dropped" in n for n in notes)


class TestArchetypeConflictStripping:
    def _spec(self, **over):
        s = {
            "cipher_type": "blockcipher",
            "key_archetype": {"type": "static_alternating", "shares": 2,
                              "whitening": "xor_shares",
                              "round_constants": {"source": "pi_hex", "count": 15}},
            "key_extract_indices": [[0, 1], [2, 3]],
            "key_schedule": [{"layer_type": "permutation", "params": {"table": [1, 0]}}],
            "round_structure": [
                {"layer_type": "subcell_sbox", "params": {"sbox_name": "S"}},
                {"layer_type": "cell_shiftrow", "params": {"table": [0, 1]}},
                {"layer_type": "add_round_key", "params": {"operator": "xor"}},
                {"layer_type": "add_constant", "params": {}},
            ],
        }
        s.update(over)
        return s

    def test_strips_all_archetype_generated_fields(self):
        from agent.skills.cipher_text_input import apply_deterministic_fixes
        out, notes = apply_deterministic_fixes(self._spec())
        assert "key_extract_indices" not in out
        assert out["key_schedule"] == []
        types = [l["layer_type"] for l in out["round_structure"]]
        assert types == ["subcell_sbox", "cell_shiftrow"]  # data path only
        assert len(notes) >= 3

    def test_keeps_add_constant_when_archetype_has_no_round_constants(self):
        from agent.skills.cipher_text_input import apply_deterministic_fixes
        arch = {"type": "static_alternating", "shares": 1, "whitening": "none"}  # no round_constants
        out, _ = apply_deterministic_fixes(self._spec(key_archetype=arch))
        types = [l["layer_type"] for l in out["round_structure"]]
        assert "add_constant" in types      # LED supplies its own constants this way
        assert "add_round_key" not in types  # still stripped

    def test_no_archetype_is_noop(self):
        from agent.skills.cipher_text_input import apply_deterministic_fixes
        s = self._spec(key_archetype=None)
        del s["key_archetype"]
        out, _ = apply_deterministic_fixes(s)
        assert "key_extract_indices" in out
        assert any(l["layer_type"] == "add_round_key" for l in out["round_structure"])


class TestArchetypeWhiteningDedup:
    def test_pre_post_whitening_cleared_when_archetype_whitens(self):
        from agent.skills.cipher_text_input import apply_deterministic_fixes
        spec = {
            "cipher_type": "blockcipher",
            "key_archetype": {"type": "static_alternating", "shares": 2,
                              "whitening": "xor_shares"},
            "pre_whitening": True, "post_whitening": True,
            "round_structure": [{"layer_type": "sbox", "params": {"sbox_name": "S"}}],
        }
        out, notes = apply_deterministic_fixes(spec)
        assert out["pre_whitening"] is False and out["post_whitening"] is False
        assert any("twice" in n for n in notes)

    def test_archetype_without_whitening_leaves_pre_whitening(self):
        from agent.skills.cipher_text_input import apply_deterministic_fixes
        spec = {
            "cipher_type": "blockcipher",
            "key_archetype": {"type": "static_alternating", "shares": 1, "whitening": "none"},
            "pre_whitening": True,
            "round_structure": [{"layer_type": "sbox", "params": {"sbox_name": "S"}}],
        }
        out, _ = apply_deterministic_fixes(spec)
        assert out["pre_whitening"] is True   # no archetype whitening -> keep it


class TestMidoriFamilyAutoArchetype:
    def _explicit_midori(self, **over):
        s = {
            "cipher_type": "blockcipher", "word_bitsize": 4, "nbr_words": 16, "nbr_rounds": 16,
            "key_word_bitsize": 4, "key_nbr_words": 32,
            "key_extract_indices": [list(range(16)), list(range(16, 32))],
            "pre_whitening": True, "post_whitening": True,
            "round_structure": [
                {"layer_type": "sbox", "params": {"sbox_name": "Sb0", "index": [[i] for i in range(16)]}},
                {"layer_type": "permutation", "params": {"table": list(range(16))}},
                {"layer_type": "matrix", "params": {"matrix": [[1]], "indices": [[0]]}},
                {"layer_type": "add_round_key", "params": {"operator": "xor"}},
            ],
        }
        s.update(over)
        return s

    def test_converts_explicit_static_alternating_to_archetype(self):
        from agent.skills.cipher_text_input import apply_deterministic_fixes
        out, notes = apply_deterministic_fixes(self._explicit_midori())
        arch = out.get("key_archetype")
        assert arch and arch["type"] == "static_alternating" and arch["shares"] == 2
        assert arch["whitening"] == "xor_shares"
        assert arch["round_constants"] == {"source": "pi_hex"}
        # the manual fields it supersedes are stripped
        assert "key_extract_indices" not in out
        assert out["pre_whitening"] is False and out["post_whitening"] is False
        assert [l["layer_type"] for l in out["round_structure"]] == ["sbox", "permutation", "matrix"]

    def test_no_conversion_when_constants_present(self):
        # A spec that already has round constants is not the broken shape - leave it alone.
        from agent.skills.cipher_text_input import apply_deterministic_fixes
        spec = self._explicit_midori()
        spec["round_structure"].append({"layer_type": "add_constant", "params": {}})
        out, _ = apply_deterministic_fixes(spec)
        assert out.get("key_archetype") is None

    def test_no_conversion_without_whitening(self):
        from agent.skills.cipher_text_input import apply_deterministic_fixes
        out, _ = apply_deterministic_fixes(self._explicit_midori(pre_whitening=False, post_whitening=False))
        assert out.get("key_archetype") is None

    def test_no_conversion_when_key_not_equal_shares(self):
        # key_extract_indices that don't partition into equal shares -> not this family.
        from agent.skills.cipher_text_input import apply_deterministic_fixes
        out, _ = apply_deterministic_fixes(self._explicit_midori(
            key_extract_indices=[list(range(16)), list(range(16, 24))]))  # unequal
        assert out.get("key_archetype") is None


class TestEvolvingKeyVsStaticArchetype:
    def _future_like(self):
        return {
            "cipher_type": "blockcipher", "key_word_bitsize": 1, "key_nbr_words": 128,
            "key_archetype": {"type": "static_alternating", "shares": 2, "whitening": "xor_shares"},
            "key_schedule": [{"layer_type": "bit_rotation", "params": {"amount": 64, "direction": "l"}}],
            "round_structure": [{"layer_type": "subcell_sbox", "params": {"sbox_name": "S"}}],
        }

    def test_fix_removes_static_archetype_when_key_evolves(self):
        from agent.skills.cipher_text_input import apply_deterministic_fixes
        out, notes = apply_deterministic_fixes(self._future_like())
        assert out.get("key_archetype") is None          # archetype removed
        assert out.get("key_schedule")                    # evolving schedule kept
        assert any("EVOLVES" in n for n in notes)

    def test_validate_rejects_static_archetype_with_evolving_schedule(self):
        from agent.skills.cipher_spec import CipherSpec
        errs = CipherSpec.from_dict(self._future_like()).validate()
        assert any("EVOLVING key_schedule" in e and "REMOVING the key_archetype" in e for e in errs)

    def test_static_key_schedule_still_stripped_not_archetype(self):
        # A non-update key_schedule (add_identity) is the redundant static case: keep the archetype,
        # clear the schedule (Midori behavior unchanged).
        from agent.skills.cipher_text_input import apply_deterministic_fixes
        spec = {"cipher_type": "blockcipher", "key_word_bitsize": 4, "key_nbr_words": 32,
                "key_archetype": {"type": "static_alternating", "shares": 2, "whitening": "xor_shares"},
                "key_schedule": [{"layer_type": "add_identity", "params": {}}],
                "round_structure": [{"layer_type": "sbox", "params": {"sbox_name": "S"}}]}
        out, _ = apply_deterministic_fixes(spec)
        assert out.get("key_archetype") is not None and out["key_schedule"] == []
