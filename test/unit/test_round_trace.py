"""Tier-1b prerequisite B: extract the concrete per-round DATA state of a built OCP cipher, so a
later step can compare it round-by-round against a reference and localize the first divergence.
"""
import io
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir
from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cipher_definition import (
    build_permutation_from_spec, build_blockcipher_from_spec, extract_ocp_round_states,
)


def test_permutation_round_states_match_hand_computation():
    # identity S-box + rotate word0 left by 1, 2 rounds. Input [5, 3] (4-bit words).
    # R1: rot(5,1,4)=1010=10 -> [10,3];  R2: rot(10,1,4)=0101=5 -> [5,3].
    spec = CipherSpec(name="TrPerm", cipher_type="permutation", block_size=8, word_bitsize=4,
                      nbr_words=2, nbr_rounds=2, sbox_tables={"S": list(range(16))},
                      round_structure=[LayerSpec("sbox", {"sbox_name": "S", "index": [[0], [1]]}),
                                       LayerSpec("rotation", {"direction": "l", "amount": 1, "word_index": 0})])
    with redirect_stdout(io.StringIO()):
        c = build_permutation_from_spec(spec)
    res = extract_ocp_round_states(c, [[5, 3]])
    assert res.get("error") is None
    assert res["states"] == [[10, 3], [5, 3]]


def test_block_cipher_final_state_equals_evaluate():
    _SC = [0, 10, 5, 15, 14, 4, 11, 1, 9, 3, 12, 6, 7, 13, 2, 8]
    _M = [[0, 1, 1, 1], [1, 0, 1, 1], [1, 1, 0, 1], [1, 1, 1, 0]]
    _COL = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]
    _SB0 = [12, 10, 13, 3, 14, 11, 15, 7, 8, 9, 1, 5, 0, 2, 4, 6]
    cs = CipherSpec(name="TrMid", cipher_type="blockcipher", block_size=64, word_bitsize=4,
                    nbr_words=16, nbr_rounds=16, key_size=128, key_word_bitsize=4, key_nbr_words=32,
                    key_archetype={"type": "static_alternating", "shares": 2, "whitening": "xor_shares",
                                   "round_constants": {"source": "pi_hex"}},
                    sbox_tables={"Sb0": _SB0},
                    round_structure=[LayerSpec("sbox", {"sbox_name": "Sb0", "index": [[j] for j in range(16)]}),
                                     LayerSpec("permutation", {"table": _SC}),
                                     LayerSpec("matrix", {"matrix": _M, "indices": _COL, "polynomial": "0x0"})])
    with redirect_stdout(io.StringIO()):
        c = build_blockcipher_from_spec(cs)
        imp.generate_implementation(c, get_files_dir() / (c.name + ".py"), "python", True)
        ev = imp.evaluate_python(c, [[0] * 16, [0] * 32], output_len=None)
    res = extract_ocp_round_states(c, [[0] * 16, [0] * 32])
    assert res.get("error") is None
    assert len(res["states"]) >= 16
    assert res["states"][-1] == ev            # the traced final state matches the real output
    assert res["states"][-1] == [3, 12, 9, 12, 12, 14, 13, 10, 2, 11, 11, 13, 4, 4, 9, 10]


def test_run_reference_straight_line_with_trace():
    """Tier-1b prerequisite A: a straight-line reference reads plaintext/key, uses the sandbox
    helpers, and exposes result = {output, trace} - its per-round trace must ALIGN with the OCP
    extractor's states (so divergence localization compares like-for-like)."""
    from agent.skills.cipher_spec import run_reference
    ref = (
        "S = [i for i in range(16)]\n"
        "state = [plaintext[0], plaintext[1]]\n"
        "trace = []\n"
        "for r in range(2):\n"
        "    state = [S[state[0]], S[state[1]]]\n"
        "    state = [rol(state[0], 1, 4), state[1]]\n"
        "    trace.append([state[0], state[1]])\n"
        "result = {\"output\": state, \"trace\": trace}\n"
    )
    out, trace = run_reference(ref, [5, 3])
    assert out == [5, 3]
    assert trace == [[10, 3], [5, 3]]     # identical to the extractor's per-round states


def test_sandbox_helpers():
    from agent.skills.cipher_spec import safe_eval_program
    assert safe_eval_program("result = rol(5, 1, 4)") == 10
    assert safe_eval_program("result = ror(10, 1, 4)") == 5
    assert safe_eval_program("result = gf_mul(2, 8, 0x13, 4)") == 3   # x*x^3 = x+1 in GF(2^4)


def test_run_reference_failure_returns_none():
    from agent.skills.cipher_spec import run_reference
    assert run_reference("result = 42", [1]) == (None, None)         # no usable output
    assert run_reference("x = 1", [1]) == (None, None)               # no result at all


# --- Blocks 3/5/6: divergence localization ---
from agent.skills.cipher_definition import first_divergence, verify_reference, localize_divergence


def test_first_divergence_index_and_length():
    assert first_divergence([[1], [2], [3]], [[1], [9], [3]])["round"] == 2
    assert first_divergence([[1], [2]], [[1], [2]])["round"] is None
    r = first_divergence([[1], [2], [3]], [[1], [2]])   # OCP longer -> mismatch, agrees on prefix
    assert r["round"] is None and r["length_mismatch"] and r["ocp_rounds"] == 3 and r["ref_rounds"] == 2


_CORRECT_REF = (
    "S=[i for i in range(16)]\n"
    "state=[plaintext[0],plaintext[1]]\n"
    "trace=[]\n"
    "for r in range(2):\n"
    "    state=[S[state[0]],S[state[1]]]\n"
    "    state=[rol(state[0],1,4),state[1]]\n"
    "    trace.append([state[0],state[1]])\n"
    "result={\"output\":state,\"trace\":trace}\n"
)


def _wrong_rot_spec():
    return CipherSpec(name="Wr", cipher_type="permutation", block_size=8, word_bitsize=4,
                      nbr_words=2, nbr_rounds=2, sbox_tables={"S": list(range(16))},
                      round_structure=[LayerSpec("sbox", {"sbox_name": "S", "index": [[0], [1]]}),
                                       LayerSpec("rotation", {"direction": "l", "amount": 2, "word_index": 0})],
                      test_vectors=[[[[1, 3]], [4, 3]]])   # correct output is [4,3]; cipher rotates by 2


def test_verify_reference_pass_and_fail():
    spec = _wrong_rot_spec()
    assert verify_reference(_CORRECT_REF, spec)["all_passed"] is True
    bad = 'result = {"output": [plaintext[0], plaintext[1]], "trace": [[plaintext[0], plaintext[1]]]}'
    assert verify_reference(bad, spec)["all_passed"] is False


def test_localize_divergence_points_at_round():
    spec = _wrong_rot_spec()
    with redirect_stdout(io.StringIO()):
        c = build_permutation_from_spec(spec)
    msg = localize_divergence(c, spec, _CORRECT_REF)
    assert msg and "round 1" in msg and "do NOT touch earlier rounds" in msg


def test_reference_repair_hint_understanding_vs_encoding():
    import agent.interfaces.api as apimod, inspect
    API = next(o for n in dir(apimod)
               if inspect.isclass(o := getattr(apimod, n)) and hasattr(o, "reference_repair_hint"))
    inst = API.__new__(API)
    spec = {"name": "W", "cipher_type": "permutation", "block_size": 8, "word_bitsize": 4,
            "nbr_words": 2, "nbr_rounds": 2, "sbox_tables": {"S": list(range(16))},
            "round_structure": [{"layer_type": "sbox", "params": {"sbox_name": "S", "index": [[0], [1]]}},
                                {"layer_type": "rotation", "params": {"direction": "l", "amount": 2, "word_index": 0}}],
            "test_vectors": [{"input": [1, 3], "output": [4, 3]}]}
    assert "divergence" in inst.reference_repair_hint(spec, _CORRECT_REF)
    bad = 'result = {"output": [plaintext[0], plaintext[1]], "trace": [[plaintext[0], plaintext[1]]]}'
    assert "UNDERSTANDING" in inst.reference_repair_hint(spec, bad)
