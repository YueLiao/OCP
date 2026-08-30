"""PRESENT-80 rebuilt from a CipherSpec using the post_whitening ABSTRACTION (nbr_rounds=31
plus post_whitening=True), verified against the designer KATs. This shows the whitening
abstraction is correct on a REAL cipher - equivalent to the built-in 'extra 32nd round for
the final AddRoundKey' - and that the bit-sliced key schedule (rotate 61 + S-box + 5-bit
round counter) plus the automatic K_32 subkey all work end to end.
"""
import io
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cipher_definition import build_blockcipher_from_spec, _spec_needs_unroll

PRESENT_SBOX = [12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2]
PERM = [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60,
        1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57, 61,
        2, 6, 10, 14, 18, 22, 26, 30, 34, 38, 42, 46, 50, 54, 58, 62,
        3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51, 55, 59, 63]
PERM_KS = [(61 + i) % 80 for i in range(80)]
SBOX_IDX = [[4 * k + j for j in range(4)] for k in range(16)]

# designer KATs (PRESENT-80), from primitives/present.py (CHES 2007)
KATS = [
    ([0]*64, [0]*80,
     [0,1,0,1,0,1,0,1,0,1,1,1,1,0,0,1,1,1,0,0,0,0,0,1,0,0,1,1,1,0,0,0,0,1,1,1,1,0,1,1,0,0,1,0,0,0,1,0,1,0,0,0,0,1,0,0,0,1,0,0,0,1,0,1]),
    ([0]*64, [1]*80,
     [1,1,1,0,0,1,1,1,0,0,1,0,1,1,0,0,0,1,0,0,0,1,1,0,1,1,0,0,0,0,0,0,1,1,1,1,0,1,0,1,1,0,0,1,0,1,0,0,0,1,0,1,0,0,0,0,0,1,0,0,1,0,0,1]),
    ([1]*64, [0]*80,
     [1,0,1,0,0,0,0,1,0,0,0,1,0,0,1,0,1,1,1,1,1,1,1,1,1,1,0,0,0,1,1,1,0,0,1,0,1,1,1,1,0,1,1,0,1,0,0,0,0,1,0,0,0,0,0,1,0,1,1,1,1,0,1,1]),
    ([1]*64, [1]*80,
     [0,0,1,1,0,0,1,1,0,0,1,1,0,0,1,1,1,1,0,1,1,1,0,0,1,1,0,1,0,0,1,1,0,0,1,0,0,0,0,1,0,0,1,1,0,0,1,0,0,0,0,1,0,0,0,0,1,1,0,1,0,0,1,0]),
]


def _present80_spec():
    constant_table = [[(i >> j) & 1 for j in reversed(range(5))] for i in range(1, 32)]
    return CipherSpec(
        name="PRESENT80w", cipher_type="blockcipher",
        block_size=64, word_bitsize=1, nbr_words=64, nbr_rounds=31,
        key_size=80, key_word_bitsize=1, key_nbr_words=80,
        key_extract_indices=list(range(64)),
        post_whitening=True,
        sbox_tables={"S": PRESENT_SBOX},
        key_schedule=[
            LayerSpec("permutation", {"table": PERM_KS}),
            LayerSpec("sbox", {"sbox_name": "S", "index": [[0, 1, 2, 3]], "mask": [1]}),
            LayerSpec("add_constant", {"add_type": "xor",
                                       "constant_mask": [None] * 60 + [True] * 5,
                                       "constant_table": constant_table}),
        ],
        round_structure=[
            LayerSpec("add_round_key", {"operator": "xor", "mask": [1] * 64}),
            LayerSpec("sbox", {"sbox_name": "S", "index": SBOX_IDX}),
            LayerSpec("permutation", {"table": PERM}),
        ],
    )


def test_present80_post_whitening_matches_designer_kats():
    spec = _present80_spec()
    assert spec.validate() == []
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)
        fd = get_files_dir(); fd.mkdir(parents=True, exist_ok=True)
        imp.generate_implementation(cipher, fd / f"{cipher.name}.py", "python",
                                    _spec_needs_unroll(spec))
    for P, K, C in KATS:
        with redirect_stdout(io.StringIO()):
            out = imp.evaluate_python(cipher, [P, K], output_len=64)
        assert out == C, f"PRESENT-80 KAT mismatch for P={P[:8]}.. K={K[:8]}.."
