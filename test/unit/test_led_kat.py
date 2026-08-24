"""LED-64 and LED-128 built through the static_alternating key_archetype with key_period=4:
the round key is added only once per 4-round step (rounds 1,5,9,...) plus a trailing key-only
round, and the share alternates per key-add EVENT (LED-128 alternates K0/K1). Verified against
the LED paper's designer KATs. This exercises the archetype's key_period gap (ARK every N
rounds) - contrast Midori, which adds a key every round (key_period defaults to 1).
"""
import io
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cipher_definition import build_blockcipher_from_spec, _spec_needs_unroll
from primitives.led import gen_rounds_constant_table

_PRESENT = [12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2]
_SR = [0, 5, 10, 15, 4, 9, 14, 3, 8, 13, 2, 7, 12, 1, 6, 11]
_MC = [[4, 1, 2, 2], [8, 6, 5, 6], [11, 14, 10, 9], [2, 2, 15, 11]]
_MCI = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]

# LED paper KATs (https://eprint.iacr.org/2012/600.pdf), as 16-cell nibble lists.
_KATS = {
    64: (32, [
        ([0] * 16, [0] * 16,
         [0x3, 0x4, 0x0, 0xC, 0x9, 0x0, 0x3, 0x7, 0xC, 0x1, 0xA, 0x9, 0x2, 0x0, 0x0, 0x8]),
        ([0, 4, 8, 0xC, 1, 5, 9, 0xD, 2, 6, 0xA, 0xE, 3, 7, 0xB, 0xF],
         [0, 4, 8, 0xC, 1, 5, 9, 0xD, 2, 6, 0xA, 0xE, 3, 7, 0xB, 0xF],
         [0xA, 0x5, 0x3, 0xF, 0x0, 0x5, 0x8, 0xC, 0x0, 0x1, 0x9, 0x5, 0x3, 0xE, 0x3, 0x8]),
    ]),
    128: (48, [
        ([0] * 16, [0] * 32,
         [0x3, 0xB, 0x8, 0xD, 0xD, 0x2, 0x5, 0xB, 0xE, 0xA, 0x0, 0xA, 0xC, 0x0, 0xC, 0x1]),
        ([0, 4, 8, 0xC, 1, 5, 9, 0xD, 2, 6, 0xA, 0xE, 3, 7, 0xB, 0xF],
         [0, 4, 8, 0xC, 1, 5, 9, 0xD, 2, 6, 0xA, 0xE, 3, 7, 0xB, 0xF] * 2,
         [0xD, 0x2, 0x7, 0x4, 0x6, 0x4, 0xF, 0xF, 0xB, 0x5, 0x0, 0xC, 0x8, 0x8, 0x1, 0x2]),
    ]),
}


def _led_spec(kbits, R):
    knw = 16 if kbits == 64 else 32
    ct = gen_rounds_constant_table(R, key_size=kbits)
    return CipherSpec(
        name=f"LED{kbits}arch", cipher_type="blockcipher",
        block_size=64, word_bitsize=4, nbr_words=16, nbr_rounds=R,
        key_size=kbits, key_word_bitsize=4, key_nbr_words=knw,
        key_archetype={"type": "static_alternating", "shares": 1 if kbits == 64 else 2,
                       "whitening": "none", "key_period": 4},
        sbox_tables={"S": _PRESENT},
        round_structure=[
            LayerSpec("add_constant", {"add_type": "xor",
                                       "constant_mask": [1] * 8 + [None] * 8,
                                       "constant_table": ct}),
            LayerSpec("sbox", {"sbox_name": "S", "index": [[j] for j in range(16)]}),
            LayerSpec("permutation", {"table": _SR}),
            LayerSpec("matrix", {"matrix": _MC, "indices": _MCI, "polynomial": "0x3"}),
        ])


def _run(kbits):
    R, kats = _KATS[kbits]
    spec = _led_spec(kbits, R)
    assert spec.validate() == []
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python",
                                    _spec_needs_unroll(spec))
        for P, K, C in kats:
            assert imp.evaluate(cipher, [P, K], output_len=None) == C


def test_led_64_matches_designer_kats():
    _run(64)


def test_led_128_matches_designer_kats():
    _run(128)
