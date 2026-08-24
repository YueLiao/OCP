"""Draft self-repair: when a generated CipherSpec draft has validation problems and an LLM
is connected, the API iteratively feeds the problems back to the model and re-validates,
recording each round in draft.repair_log - instead of leaving the user to fix them."""
from agent.interfaces.api import OCPAgent
from agent.skills.cipher_text_input import CipherSpecDraft


def _bad_spec():
    # add_round_key mask has 4 ones but the subkey (key_extract_indices) has 2 words
    return {
        "name": "X", "cipher_type": "blockcipher",
        "block_size": 8, "word_bitsize": 4, "nbr_words": 2, "nbr_rounds": 2,
        "key_size": 8, "key_word_bitsize": 4, "key_nbr_words": 2,
        "key_extract_indices": [0, 1],
        "key_schedule": [{"layer_type": "permutation", "params": {"table": [1, 0]}}],
        "sbox_tables": {"S": list(range(16))},
        "round_structure": [
            {"layer_type": "add_round_key", "params": {"operator": "xor", "mask": [1, 1, 1, 1]}},
            {"layer_type": "sbox", "params": {"sbox_name": "S", "index": [[0], [1]]}},
        ],
    }


def _fixed_spec():
    s = _bad_spec()
    s["round_structure"][0]["params"]["mask"] = [1, 1]   # now 2 ones == 2 subkey words
    return s


class _Stub:
    """Minimal stand-in exposing just what _auto_repair_draft touches."""
    def __init__(self, corrected, cancel_after=None, kat_problems=None):
        self._core = type("C", (), {"llm": object()})()  # non-None LLM
        self._corrected = corrected
        self.calls = 0
        self.cancel_after = cancel_after  # report cancelled once calls >= this
        self._kat = kat_problems or (lambda spec: [])  # KAT check hook (default: none)

    def repair_cipher_spec(self, spec, problems):
        self.calls += 1
        return self._corrected

    def is_cancelled(self):
        return self.cancel_after is not None and self.calls >= self.cancel_after

    def _kat_problems(self, spec):
        return self._kat(spec)


def test_auto_repair_fixes_and_logs():
    draft = CipherSpecDraft(spec=_bad_spec())
    draft.validate_spec()
    assert draft.validation_errors  # starts broken

    stub = _Stub(_fixed_spec())
    result = OCPAgent._auto_repair_draft(stub, draft)

    assert result.is_valid, result.validation_errors
    assert stub.calls == 1                      # one repair round was enough
    assert result.repair_log and result.repair_log[0]["resolved"]
    assert not result.repair_log[0]["problems_after"]


def test_auto_repair_stops_without_progress():
    # LLM returns the same broken spec -> loop must stop, not spin to max_attempts.
    draft = CipherSpecDraft(spec=_bad_spec())
    draft.validate_spec()
    stub = _Stub(_bad_spec())
    result = OCPAgent._auto_repair_draft(stub, draft, max_attempts=3)
    assert stub.calls == 1                       # stopped after no progress
    assert not result.is_valid                   # still broken, honestly reported


def test_auto_repair_noop_when_clean():
    draft = CipherSpecDraft(spec=_fixed_spec())
    draft.validate_spec()
    assert draft.is_valid
    stub = _Stub(_fixed_spec())
    result = OCPAgent._auto_repair_draft(stub, draft)
    assert stub.calls == 0 and result.repair_log == []


def test_auto_repair_stops_on_cancel():
    # User pressed Stop before the first repair round -> no LLM call, loop exits, logged.
    draft = CipherSpecDraft(spec=_bad_spec())
    draft.validate_spec()
    stub = _Stub(_fixed_spec(), cancel_after=0)
    result = OCPAgent._auto_repair_draft(stub, draft)
    assert stub.calls == 0
    assert any(r.get("cancelled") for r in result.repair_log)


# --- Deterministic (no-LLM) fixes ---
from agent.skills.cipher_text_input import apply_deterministic_fixes, build_cipher_spec_draft


def test_deterministic_fix_block_size():
    spec, notes = apply_deterministic_fixes({"word_bitsize": 4, "nbr_words": 4, "block_size": 99})
    assert spec["block_size"] == 16 and notes


def test_deterministic_fix_mask_when_subkey_covers_state():
    spec, notes = apply_deterministic_fixes({
        "cipher_type": "blockcipher", "nbr_words": 4, "key_extract_indices": [0, 1, 2, 3],
        "round_structure": [{"layer_type": "add_round_key", "params": {"mask": [1, 1, 1, 1, 1, 1]}}],
    })
    assert spec["round_structure"][0]["params"]["mask"] == [1, 1, 1, 1] and notes


def test_deterministic_fix_leaves_partial_subkey_mask():
    # subkey (2) < state (4): no unique mask, must NOT be auto-changed
    spec, notes = apply_deterministic_fixes({
        "cipher_type": "blockcipher", "nbr_words": 4, "key_extract_indices": [0, 1],
        "round_structure": [{"layer_type": "add_round_key", "params": {"mask": [1, 1, 1, 1]}}],
    })
    assert spec["round_structure"][0]["params"]["mask"] == [1, 1, 1, 1]
    assert not any("mask" in n for n in notes)


def test_deterministic_fix_skips_layout_family():
    # versioned/layout families derive block_size; do not touch it
    spec, notes = apply_deterministic_fixes({"word_bitsize": 4, "nbr_words": 4,
                                             "block_size": 99, "layout": {"rows": 4, "cols": 4}})
    assert spec["block_size"] == 99 and not notes


def test_deterministic_fix_derives_cell_layout_from_cell_ops():
    # LLM used cell ops (subcell_sbox/mixcolumn/cell_shiftrow) but forgot cell_layout;
    # it is fully determined by word_bitsize x nbr_words, so derive it.
    spec, notes = apply_deterministic_fixes({
        "cipher_type": "blockcipher", "word_bitsize": 4, "nbr_words": 16, "block_size": 64,
        "round_structure": [
            {"layer_type": "subcell_sbox", "params": {"sbox_name": "S"}},
            {"layer_type": "mixcolumn", "params": {}},
        ],
    })
    assert spec.get("cell_layout") == {"cell_bits": 4, "nbr_cells": 16}
    assert "word_bitsize" not in spec and "nbr_words" not in spec  # derived, dropped
    assert any("cell_layout" in n for n in notes)


# --- KAT-driven repair: a structurally-valid spec that fails its test vectors is repaired ---

def test_auto_repair_fixes_kat_failure_when_structurally_valid():
    # No validation errors, but the test vectors fail -> the loop must STILL repair (a
    # valid-looking spec can be the wrong cipher, e.g. a missing add_round_key layer).
    draft = CipherSpecDraft(spec=_fixed_spec())
    draft.validate_spec()
    assert draft.is_valid                                  # structurally clean
    calls = {"n": 0}

    def kat(_spec):                                        # fails once, then passes after repair
        calls["n"] += 1
        return ["only 0/1 test vectors pass - wrong cipher"] if calls["n"] == 1 else []

    stub = _Stub(_fixed_spec(), kat_problems=kat)
    result = OCPAgent._auto_repair_draft(stub, draft)
    assert stub.calls == 1                                 # one KAT-driven repair round happened
    assert result.repair_log and result.repair_log[-1]["resolved"]
    assert not result.repair_log[-1]["problems_after"]


_MIDORI_DATA = {
    "sbox_tables": {"Sb0": [12, 10, 13, 3, 14, 11, 15, 7, 8, 9, 1, 5, 0, 2, 4, 6]},
    "sc": [0, 10, 5, 15, 14, 4, 11, 1, 9, 3, 12, 6, 7, 13, 2, 8],
    "m": [[0, 1, 1, 1], [1, 0, 1, 1], [1, 1, 0, 1], [1, 1, 1, 0]],
    "col": [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]],
    "tv": [{"plaintext": [0] * 16, "key": [0] * 32,
            "output": [3, 12, 9, 12, 12, 14, 13, 10, 2, 11, 11, 13, 4, 4, 9, 10]}],
}


def _midori_data_path_layers():
    d = _MIDORI_DATA
    return [
        {"layer_type": "sbox", "params": {"sbox_name": "Sb0", "index": [[j] for j in range(16)]}},
        {"layer_type": "permutation", "params": {"table": d["sc"]}},
        {"layer_type": "matrix", "params": {"matrix": d["m"], "indices": d["col"], "polynomial": "0x0"}},
    ]


def test_kat_problems_flags_structurally_valid_but_wrong_cipher():
    # Midori data path with a subkey extracted but NO add_round_key -> builds + validates,
    # but never mixes the key in, so it fails the KAT. _kat_problems must report it.
    d = _MIDORI_DATA
    spec = {
        "name": "MidoriNoARK", "cipher_type": "blockcipher",
        "block_size": 64, "word_bitsize": 4, "nbr_words": 16, "nbr_rounds": 16,
        "key_size": 128, "key_word_bitsize": 4, "key_nbr_words": 32,
        "key_extract_indices": [list(range(16)), list(range(16, 32))],
        "sbox_tables": d["sbox_tables"], "round_structure": _midori_data_path_layers(),
        "test_vectors": d["tv"],
    }
    problems = OCPAgent._kat_problems(object(), spec)      # _kat_problems does not use self
    assert problems and "test vectors" in problems[0].lower()


def test_kat_problems_silent_for_a_correct_cipher():
    # The same data path but WITH a key_archetype (adds the key + constants + whitening) is
    # correct Midori64, so _kat_problems reports nothing.
    d = _MIDORI_DATA
    spec = {
        "name": "MidoriOK", "cipher_type": "blockcipher",
        "block_size": 64, "word_bitsize": 4, "nbr_words": 16, "nbr_rounds": 16,
        "key_size": 128, "key_word_bitsize": 4, "key_nbr_words": 32,
        "sbox_tables": d["sbox_tables"], "round_structure": _midori_data_path_layers(),
        "key_archetype": {"type": "static_alternating", "shares": 2, "whitening": "xor_shares",
                          "round_constants": {"source": "pi_hex", "count": 15}},
        "test_vectors": d["tv"],
    }
    assert OCPAgent._kat_problems(object(), spec) == []
