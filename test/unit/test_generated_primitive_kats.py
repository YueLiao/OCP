"""Every agent-generated primitive under primitives/ must ship real, independently-checked
KATs in a class `gen_test_vectors`, not `pass` and not a factory-side assignment. This guards
the class of bug KNOT-512 exposed: a generated cipher that runs but was never verified. The
KNOT widths are covered by test_knot_kat.py; here we pin FUTURE and TinyARX.
"""
import io
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from primitives.future import FUTURE_BLOCKCIPHER


def _build_and_run_stored(factory):
    with redirect_stdout(io.StringIO()):
        cipher = factory()
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        results = [(imp.evaluate_python(cipher, tv[0], output_len=len(tv[1])), tv[1])
                   for tv in cipher.test_vectors]
    return cipher.test_vectors, results


def test_future_ships_designer_kats():
    # AFRICACRYPT 2022 appendix-A vectors (P, K, C), the independent ground truth.
    designer = {
        (0xffffffffffffffff, 0x000102030405060708090a0b0c0d0e0f): 0x68e030733fe73b8a,
        (0xffffffffffffffff, 0xffffffffffffffffffffffffffffffff): 0x333ba4b7646e09f2,
        (0x5353414d414e5441, 0x05192832010913645029387763948871): 0x5ce1b8d8d01a9310,
        (0x6162636465666768, 0x00000000000000000000000000000000): 0xcc5ba5e52038b6df,
        (0x0000000000000000, 0x00000000000000000000000000000000): 0x298650c13199cdec,
    }
    vectors, results = _build_and_run_stored(FUTURE_BLOCKCIPHER)
    assert len(vectors) == 5
    for got, want in results:
        assert got == want
    # the stored vectors ARE the designer KATs (bit-encoded), not self-generated ones
    shipped = set()
    for v in vectors:
        pk, kk, ck = v[0][0], v[0][1], v[1]
        P = int("".join(map(str, pk)), 2)
        K = int("".join(map(str, kk)), 2)
        C = int("".join(map(str, ck)), 2)
        assert designer.get((P, K)) == C
        shipped.add((P, K))
    assert shipped == set(designer)


def test_tinyarx_fixture_yields_passing_kats():
    # primitives/tinyarx.py is a demo primitive that several tests regenerate from the
    # arx_tiny.json fixture, so we assert on the AUTHORITATIVE fixture (not the mutable file):
    # its facts must carry test vectors that flow into the spec and pass, cross-checked against
    # an independent reference of the ARX round.
    import json
    from pathlib import Path
    from agent.skills.cipher_text_input import CipherFacts, cipher_spec_payload_from_facts
    from agent.skills.cipher_spec import CipherSpec
    from agent.skills.cipher_definition import build_permutation_from_spec

    fixture = json.loads((Path(__file__).parent.parent / "fixtures" / "text_first"
                          / "arx_tiny.json").read_text())
    facts = CipherFacts.from_dict(fixture["facts"])
    spec = CipherSpec.from_dict(cipher_spec_payload_from_facts(facts))
    assert spec.test_vectors, "arx_tiny.json must ship test vectors for the demo primitive"

    m = (1 << 16) - 1
    rotr = lambda v, n: ((v >> n) | (v << (16 - n))) & m
    rotl = lambda v, n: ((v << n) | (v >> (16 - n))) & m

    def ref(x0, x1):
        for _ in range(spec.nbr_rounds):
            x0 = rotr(x0, 7); x0 = (x0 + x1) & m; x1 = rotl(x1, 2); x1 = (x0 ^ x1) & m
        return [x0, x1]

    with redirect_stdout(io.StringIO()):
        cipher = build_permutation_from_spec(spec)
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        for tv in spec.test_vectors:
            (x0, x1), out = tv[0][0], tv[1]
            assert ref(x0, x1) == out                        # vectors are independently correct
            assert imp.evaluate_python(cipher, tv[0], output_len=len(out)) == out
