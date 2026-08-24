"""Declarative key_schedule "bit_rotation": rotate the (bit-level) key register - or a
sub-range of it - by a bit amount, generated into a permutation instead of the LLM hand-writing
a 128-entry table. FUTURE-64's key schedule is exactly two of these.
"""
import io
import json
from contextlib import redirect_stdout

from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cell_sliced import bit_rotation_perm
from agent.skills.cipher_definition import (
    build_blockcipher_from_spec, verify_cipher_test_vectors, _normalize_test_vectors,
)
from tools.paths import get_files_dir


def _mk(key_schedule, kwb=1, knw=8):
    return CipherSpec(
        name="BR", cipher_type="blockcipher", block_size=8, word_bitsize=1, nbr_words=8,
        nbr_rounds=2, key_size=knw, key_word_bitsize=kwb, key_nbr_words=knw,
        key_schedule=[LayerSpec(l["layer_type"], l["params"]) for l in key_schedule],
        round_structure=[LayerSpec("xor", {"input_indices": [[0, 1]], "output_indices": [1]})],
    )


class TestExpandKeyBitRotation:
    def test_whole_register_rotation(self):
        spec = _mk([{"layer_type": "bit_rotation", "params": {"amount": 3, "direction": "l"}}], knw=8)
        ex = spec.expand_key_bit_rotations()
        assert ex.key_schedule[0].layer_type == "permutation"
        assert ex.key_schedule[0].params["table"] == bit_rotation_perm(8, 3, "l")

    def test_sub_range_rotation_leaves_rest(self):
        # rotate bits [0,4) by 1 (left), leave [4,8) identity
        spec = _mk([{"layer_type": "bit_rotation",
                     "params": {"amount": 1, "direction": "l", "start": 0, "width": 4}}], knw=8)
        ex = spec.expand_key_bit_rotations()
        assert ex.key_schedule[0].params["table"] == [1, 2, 3, 0, 4, 5, 6, 7]

    def test_right_direction(self):
        spec = _mk([{"layer_type": "bit_rotation", "params": {"amount": 1, "direction": "r"}}], knw=4)
        ex = spec.expand_key_bit_rotations()
        assert ex.key_schedule[0].params["table"] == bit_rotation_perm(4, 1, "r")

    def test_not_applied_when_key_not_bit_level(self):
        # key_word_bitsize != 1: leave the bit_rotation as-is (validate will flag the size)
        spec = _mk([{"layer_type": "bit_rotation", "params": {"amount": 3}}], kwb=4, knw=8)
        ex = spec.expand_key_bit_rotations()
        assert ex.key_schedule[0].layer_type == "bit_rotation"


def test_future_via_declarative_bit_rotation_verifies():
    """FUTURE-64's real key schedule (swap halves by 64, rotate low half by 5) expressed with the
    declarative form builds and verifies against the 5 designer KATs - identical to the
    hand-written-permutation spec."""
    d = json.loads((get_files_dir() / "FUTURE_correct_spec.json").read_text())
    d["name"] = "FUTUREBitRotKAT"   # unique name: avoid the cached files/FUTURE.py from other tests
    d["key_schedule"] = [
        {"layer_type": "bit_rotation", "params": {"amount": 64, "direction": "l"}},
        {"layer_type": "bit_rotation", "params": {"amount": 5, "direction": "l",
                                                  "start": 0, "width": 64},
         "except_rounds": [1]},   # FUTURE's low-half rotation skips round 1 (declarative preserves it)
    ]
    cs = CipherSpec.from_dict(d)
    cs.test_vectors = _normalize_test_vectors(cs.test_vectors, cs.cipher_type,
                                              cs.word_bitsize, cs.key_word_bitsize)
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(cs)
        res = verify_cipher_test_vectors(cipher, cs)
    assert res["all_passed"] and res["passed"] == 5, res
