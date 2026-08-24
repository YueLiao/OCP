"""Auto-repair guardrails: a "fix" must never gut the algorithm to pass validation.

These pin the three forbidden mutations we saw the repair loop make on Midori/FUTURE:
deleting a core layer, editing the known-answer vectors, or shrinking the word size.
"""
from agent.interfaces.api import OCPAgent


def _spec(**over):
    base = {
        "word_bitsize": 4,
        "key_word_bitsize": 4,
        "test_vectors": [[[[0] * 16, [0] * 32], [3, 12, 9, 12]]],
        "round_structure": [
            {"type": "sbox", "params": {"sbox_name": "S"}},
            {"type": "matrix", "params": {"matrix": [[1]], "indices": [[0]]}},
            {"type": "add_round_key", "params": {}},
        ],
    }
    base.update(over)
    return base


class TestRepairGuardrails:
    def test_identical_spec_is_allowed(self):
        assert OCPAgent._repair_guardrail_violations(_spec(), _spec()) == []

    def test_editing_test_vectors_is_forbidden(self):
        after = _spec(test_vectors=[[[[0] * 16, [0] * 32], [0, 0, 0, 0]]])
        v = OCPAgent._repair_guardrail_violations(_spec(), after)
        assert any("test_vectors" in m for m in v)

    def test_dropping_matrix_layer_is_forbidden(self):
        after = _spec(round_structure=[
            {"type": "sbox", "params": {"sbox_name": "S"}},
            {"type": "add_round_key", "params": {}},
        ])
        v = OCPAgent._repair_guardrail_violations(_spec(), after)
        assert any("matrix" in m for m in v)

    def test_dropping_sbox_layer_is_forbidden(self):
        after = _spec(round_structure=[
            {"type": "matrix", "params": {"matrix": [[1]], "indices": [[0]]}},
            {"type": "add_round_key", "params": {}},
        ])
        v = OCPAgent._repair_guardrail_violations(_spec(), after)
        assert any("sbox" in m for m in v)

    def test_shrinking_word_bitsize_is_forbidden(self):
        after = _spec(word_bitsize=1)
        v = OCPAgent._repair_guardrail_violations(_spec(), after)
        assert any("word_bitsize" in m for m in v)

    def test_changing_key_word_bitsize_is_forbidden(self):
        after = _spec(key_word_bitsize=8)
        v = OCPAgent._repair_guardrail_violations(_spec(), after)
        assert any("key_word_bitsize" in m for m in v)

    def test_removing_redundant_add_round_key_is_allowed(self):
        # De-duplicating a key/constant addition is a legitimate repair, not a violation.
        after = _spec(round_structure=[
            {"type": "sbox", "params": {"sbox_name": "S"}},
            {"type": "matrix", "params": {"matrix": [[1]], "indices": [[0]]}},
        ])
        assert OCPAgent._repair_guardrail_violations(_spec(), after) == []

    def test_adding_a_layer_is_allowed(self):
        # Adding a missing key addition (the common real fix) must not trip the guardrail.
        after = _spec(round_structure=_spec()["round_structure"] + [
            {"type": "add_constant", "params": {}},
        ])
        assert OCPAgent._repair_guardrail_violations(_spec(), after) == []

    def test_fixing_layer_params_is_allowed(self):
        # Same layers, corrected parameters - exactly what repair SHOULD do.
        after = _spec(round_structure=[
            {"type": "sbox", "params": {"sbox_name": "S", "index": [[0], [1]]}},
            {"type": "matrix", "params": {"matrix": [[1, 1], [1, 1]], "indices": [[0, 1]]}},
            {"type": "add_round_key", "params": {"mask": [1, 0]}},
        ])
        assert OCPAgent._repair_guardrail_violations(_spec(), after) == []

    def test_multiple_violations_reported_together(self):
        after = _spec(word_bitsize=1, test_vectors=[[[[0]], [1]]], round_structure=[
            {"type": "add_round_key", "params": {}},
        ])
        v = OCPAgent._repair_guardrail_violations(_spec(), after)
        assert len(v) >= 3
