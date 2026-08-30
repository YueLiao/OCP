"""A combined subkey may XOR N shares, not just 2. key_extract_indices entry
{"xor": [s0, s1, ..., s_{n-1}]} extracts all n shares into SUBKEYS and reduces them (XOR for
n=2, N_XOR for n>=3) to the subkey. This is the 3-way tweakey gap the audit flagged: it lets
the agent build SKINNY-128-384, whose subtweakey is TK1^TK2^TK3, end to end. n=2 (Midori WK =
K0^K1) is unchanged and covered by test_midori_kat.
"""
import io
import random
from contextlib import redirect_stdout

import implementations.implementations as imp
from tools.paths import get_files_dir

from agent.skills.cipher_spec import CipherSpec, LayerSpec
from agent.skills.cipher_definition import build_blockcipher_from_spec, _spec_needs_unroll
from agent.skills.cipher_primitive_export import generate_primitive_source


def test_three_way_xor_extraction_matches_independent_reference():
    # 4 words x 4 bits; key = 3 shares of 4 words; one round ARK; subkey = s0^s1^s2.
    spec = CipherSpec(
        name="Xor3", cipher_type="blockcipher",
        block_size=16, word_bitsize=4, nbr_words=4, nbr_rounds=1,
        key_size=48, key_word_bitsize=4, key_nbr_words=12,
        key_extract_indices=[{"xor": [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]]}],
        round_structure=[LayerSpec("add_round_key", {"operator": "xor", "mask": [1, 1, 1, 1]})])
    assert spec.validate() == []
    random.seed(0)
    P = [random.randint(0, 15) for _ in range(4)]
    K = [random.randint(0, 15) for _ in range(12)]
    ref = [P[j] ^ K[j] ^ K[4 + j] ^ K[8 + j] for j in range(4)]
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
        got = imp.evaluate_python(cipher, [P, K], output_len=None)
    assert got == ref
    # the exporter emits an N_XOR reduce over 3 shares, not a 2-input XOR
    with redirect_stdout(io.StringIO()):
        _, src, _, _ = generate_primitive_source(spec)
    assert "N_XOR" in src and "* 3" in src


# --- SKINNY-128-384: the real 3-way-tweakey cipher, built entirely through the agent path ---
_SB8 = [101, 76, 106, 66, 75, 99, 67, 107, 85, 117, 90, 122, 83, 115, 91, 123, 53, 140, 58, 129,
        137, 51, 128, 59, 149, 37, 152, 42, 144, 35, 153, 43, 229, 204, 232, 193, 201, 224, 192,
        233, 213, 245, 216, 248, 208, 240, 217, 249, 165, 28, 168, 18, 27, 160, 19, 169, 5, 181,
        10, 184, 3, 176, 11, 185, 50, 136, 60, 133, 141, 52, 132, 61, 145, 34, 156, 44, 148, 36,
        157, 45, 98, 74, 108, 69, 77, 100, 68, 109, 82, 114, 92, 124, 84, 116, 93, 125, 161, 26,
        172, 21, 29, 164, 20, 173, 2, 177, 12, 188, 4, 180, 13, 189, 225, 200, 236, 197, 205, 228,
        196, 237, 209, 241, 220, 252, 212, 244, 221, 253, 54, 142, 56, 130, 139, 48, 131, 57, 150,
        38, 154, 40, 147, 32, 155, 41, 102, 78, 104, 65, 73, 96, 64, 105, 86, 118, 88, 120, 80,
        112, 89, 121, 166, 30, 170, 17, 25, 163, 16, 171, 6, 182, 8, 186, 0, 179, 9, 187, 230, 206,
        234, 194, 203, 227, 195, 235, 214, 246, 218, 250, 211, 243, 219, 251, 49, 138, 62, 134,
        143, 55, 135, 63, 146, 33, 158, 46, 151, 39, 159, 47, 97, 72, 110, 70, 79, 103, 71, 111,
        81, 113, 94, 126, 87, 119, 95, 127, 162, 24, 174, 22, 31, 167, 23, 175, 1, 178, 14, 190, 7,
        183, 15, 191, 226, 202, 238, 198, 207, 231, 199, 239, 210, 242, 222, 254, 215, 247, 223, 255]
_MAT1 = [[0, 1, 0, 0, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0, 0, 0], [0, 0, 0, 1, 0, 0, 0, 0],
         [0, 0, 0, 0, 1, 0, 0, 0], [0, 0, 0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0, 1, 0],
         [0, 0, 0, 0, 0, 0, 0, 1], [1, 0, 1, 0, 0, 0, 0, 0]]
_MAT2 = [[0, 1, 0, 0, 0, 0, 0, 1], [1, 0, 0, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0, 0, 0],
         [0, 0, 1, 0, 0, 0, 0, 0], [0, 0, 0, 1, 0, 0, 0, 0], [0, 0, 0, 0, 1, 0, 0, 0],
         [0, 0, 0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 0, 0, 1, 0]]
_RC = [0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3E, 0x3D, 0x3B, 0x37, 0x2F, 0x1E, 0x3C, 0x39, 0x33, 0x27,
       0x0E, 0x1D, 0x3A, 0x35, 0x2B, 0x16, 0x2C, 0x18, 0x30, 0x21, 0x02, 0x05, 0x0B, 0x17, 0x2E,
       0x1C, 0x38, 0x31, 0x23, 0x06, 0x0D, 0x1B, 0x36, 0x2D, 0x1A, 0x34, 0x29, 0x12, 0x24, 0x08,
       0x11, 0x22, 0x04, 0x09, 0x13, 0x26, 0x0c, 0x19, 0x32, 0x25, 0x0a]


def _skinny_128_384_spec():
    k_perm = [i + 16 * j for j in range(3) for i in [9, 15, 8, 13, 10, 14, 12, 11, 0, 1, 2, 3, 4, 5, 6, 7]]
    rc_table = [[rc & 0xF, rc >> 4, 0x2] for rc in _RC]
    return CipherSpec(
        name="SKINNY128384", cipher_type="blockcipher",
        block_size=128, word_bitsize=8, nbr_words=16, nbr_rounds=56,
        key_size=384, key_word_bitsize=8, key_nbr_words=48,
        # subtweakey = top half of (TK1 ^ TK2 ^ TK3); KS evolves the 3 tweakeys each round
        key_extract_indices=[{"xor": [list(range(8)), list(range(16, 24)), list(range(32, 40))]}],
        sbox_tables={"S": _SB8},
        key_schedule=[
            LayerSpec("permutation", {"table": k_perm}),
            LayerSpec("gf2_linear", {"matrix": _MAT1, "index_in": list(range(16, 24)),
                                     "index_out": list(range(16, 24))}),
            LayerSpec("gf2_linear", {"matrix": _MAT2, "index_in": list(range(32, 40)),
                                     "index_out": list(range(32, 40))}),
        ],
        round_structure=[
            LayerSpec("sbox", {"sbox_name": "S", "index": [[j] for j in range(16)]}),
            LayerSpec("add_constant", {"add_type": "xor",
                                       "constant_mask": [True, None, None, None, True, None, None,
                                                         None, True, None, None, None, None, None,
                                                         None, None],
                                       "constant_table": rc_table}),
            LayerSpec("add_round_key", {"operator": "xor", "mask": [1] * 8 + [0] * 8}),
            LayerSpec("permutation", {"table": [0, 1, 2, 3, 7, 4, 5, 6, 10, 11, 8, 9, 13, 14, 15, 12]}),
            LayerSpec("matrix", {"matrix": [[1, 0, 1, 1], [1, 0, 0, 0], [0, 1, 1, 0], [1, 0, 1, 0]],
                                 "indices": [[0, 4, 8, 12], [1, 5, 9, 13], [2, 6, 10, 14], [3, 7, 11, 15]]}),
        ])


def test_skinny_128_384_matches_designer_kat():
    spec = _skinny_128_384_spec()
    assert spec.validate() == []
    P = [0xa3, 0x99, 0x4b, 0x66, 0xad, 0x85, 0xa3, 0x45, 0x9f, 0x44, 0xe9, 0x2b, 0x08, 0xf5, 0x50, 0xcb]
    K = [0xdf, 0x88, 0x95, 0x48, 0xcf, 0xc7, 0xea, 0x52, 0xd2, 0x96, 0x33, 0x93, 0x01, 0x79, 0x74, 0x49,
         0xab, 0x58, 0x8a, 0x34, 0xa4, 0x7f, 0x1a, 0xb2, 0xdf, 0xe9, 0xc8, 0x29, 0x3f, 0xbe, 0xa9, 0xa5,
         0xab, 0x1a, 0xfa, 0xc2, 0x61, 0x10, 0x12, 0xcd, 0x8c, 0xef, 0x95, 0x26, 0x18, 0xc3, 0xeb, 0xe8]
    C = [0x94, 0xec, 0xf5, 0x89, 0xe2, 0x1, 0x7c, 0x60, 0x1b, 0x38, 0xc6, 0x34, 0x6a, 0x10, 0xdc, 0xfa]
    with redirect_stdout(io.StringIO()):
        cipher = build_blockcipher_from_spec(spec)
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python",
                                    _spec_needs_unroll(spec))
        got = imp.evaluate_python(cipher, [P, K], output_len=None)
    assert got == C
