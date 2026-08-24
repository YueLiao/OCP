"""Midori - self-contained OCP primitive (no agent deps), version-parameterized like
the other block ciphers in this package (present.py, led.py, aes.py, ...).

    MIDORI_BLOCKCIPHER(version=64)   -> Midori64  (64-bit block, 128-bit key)
    MIDORI_BLOCKCIPHER(version=128)  -> Midori128 (128-bit block, 128-bit key)

Structure (Banik et al., ASIACRYPT 2015, Sec 3.3, MidoriCore(R)):
    S = X (+) WK ; for i=0..R-2: SubCell, ShuffleCell, MixColumn, S (+) RK_i ; SubCell ; Y = S (+) WK
  - Midori64 : R=16, 4-bit cells, Sb0; WK = K0 (+) K1, RK_i = K_(i mod 2) (+) alpha_i (key=K0||K1).
  - Midori128: R=20, 8-bit cells, four SSb S-boxes (SSb_(i mod 4)); WK = K, RK_i = K (+) beta_i.

Both are laid out as R+1 OCP rounds with exactly ONE key addition per round (key-add first):
R1 pre-whitening, the round function in the middle, then the final SubCell round and the
post-whitening round. Whitening / round keys are produced inside the SUBKEYS function
(Midori64 computes WK = K0 (+) K1 there; the K0/K1 alternation is a round-dependent
extraction). Round constants alpha_i/beta_i come from the fractional hex of pi. Verified
against the paper's Appendix A test vectors for both versions.
"""
from primitives.primitives import Block_cipher
from operators.Sbox import (
    Midori64_Sb0_Sbox,
    Midori128_SSb0_Sbox, Midori128_SSb1_Sbox, Midori128_SSb2_Sbox, Midori128_SSb3_Sbox,
)
from operators.boolean_operators import XOR
import variables.variables as var

# ShuffleCell / MixColumn are shared by both versions (MixColumn matrix is binary -> XOR).
_SC = [0, 10, 5, 15, 14, 4, 11, 1, 9, 3, 12, 6, 7, 13, 2, 8]
_M = [[0, 1, 1, 1], [1, 0, 1, 1], [1, 1, 0, 1], [1, 1, 1, 0]]
_COL = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]
# alpha_i / beta_i as 4-hex rows from the fractional hex of pi = 3.243f6a8885a308d3...
_BETA_HEX = [
    [0x2, 0x4, 0x3, 0xf], [0x6, 0xa, 0x8, 0x8], [0x8, 0x5, 0xa, 0x3], [0x0, 0x8, 0xd, 0x3],
    [0x1, 0x3, 0x1, 0x9], [0x8, 0xa, 0x2, 0xe], [0x0, 0x3, 0x7, 0x0], [0x7, 0x3, 0x4, 0x4],
    [0xa, 0x4, 0x0, 0x9], [0x3, 0x8, 0x2, 0x2], [0x2, 0x9, 0x9, 0xf], [0x3, 0x1, 0xd, 0x0],
    [0x0, 0x8, 0x2, 0xe], [0xf, 0xa, 0x9, 0x8], [0xe, 0xc, 0x4, 0xe], [0x6, 0xc, 0x8, 0x9],
    [0x4, 0x5, 0x2, 0x8], [0x2, 0x1, 0xe, 0x6], [0x3, 0x8, 0xd, 0x0],
]
_SSB = [Midori128_SSb0_Sbox, Midori128_SSb1_Sbox, Midori128_SSb2_Sbox, Midori128_SSb3_Sbox]


class Midori_block_cipher(Block_cipher):
    def __init__(self, name, version, p_input, k_input, c_output, nbr_rounds=None):
        if version not in (64, 128):
            raise ValueError(f"Midori supports version 64 or 128, got {version}")
        self.version = version
        R = 16 if version == 64 else 20
        if nbr_rounds is None: nbr_rounds = R + 1
        w = 4 if version == 64 else 8

        if version == 64:
            s_config, k_config, sk_config = [5, 16, 0, 4], [1, 32, 0, 4], [2, 16, 16, 4]
        else:
            s_config, k_config, sk_config = [8, 16, 0, 8], [1, 16, 0, 8], [1, 16, 0, 8]
        super().__init__(name, p_input, k_input, c_output, nbr_rounds, 1, s_config, k_config, sk_config)
        S  = self.functions["PERMUTATION"]
        KS = self.functions["KEY_SCHEDULE"]
        SK = self.functions["SUBKEYS"]
        constant_table = self.gen_rounds_constant_table(15 if version == 64 else 19)
        KS.AddIdentityLayer("K_ID", 1, 0)   # key is static

        def is_wk(r): return r == 1 or r == nbr_rounds

        for r in range(1, nbr_rounds + 1):
            self._build_subkey(SK, KS, r, is_wk(r))
            S.AddRoundKeyLayer("ARK", r, 0, XOR, SK, mask=[1] * 16)
            if is_wk(r): S.AddIdentityLayer("AC_ID", r, 1)
            else:        S.AddConstantLayer("AC", r, 1, "xor", [1] * 16, constant_table)
            self._build_subcell(S, r, r <= nbr_rounds - 1)
            base = 2 if version == 64 else 5   # index of the LAST SubCell layer (v64: 1 layer, v128: 4)
            if r <= nbr_rounds - 2: S.PermutationLayer("SC", r, base + 1, _SC)
            else:                   S.AddIdentityLayer("SC_ID", r, base + 1)
            if r <= nbr_rounds - 2: S.MatrixLayer("MC", r, base + 2, _M, _COL, polynomial='0x0')
            else:                   S.AddIdentityLayer("MC_ID", r, base + 2)

        self.test_vectors = self.gen_test_vectors(version)

    def _build_subkey(self, SK, KS, r, wk):
        if self.version == 64:
            if wk:  # WK = K0 (+) K1, computed inside SUBKEYS
                SK.ExtractionLayer("SK_EX", r, 0, list(range(32)), KS.vars[1][0])
                SK.SingleOperatorLayer("SK_WK", r, 1, XOR, [[j, 16 + j] for j in range(16)], list(range(16)))
            else:   # even round -> K0 (0..15), odd round -> K1 (16..31)
                b = 0 if r % 2 == 0 else 16
                SK.ExtractionLayer("SK_EX", r, 0, list(range(b, b + 16)) * 2, KS.vars[1][0])
                SK.AddIdentityLayer("SK_ID", r, 1)
        else:       # Midori128: WK = K and RK_i = K (+) beta_i, so the subkey is always K
            SK.ExtractionLayer("SK_EX", r, 0, list(range(16)), KS.vars[1][0])

    def _build_subcell(self, S, r, active):
        if self.version == 64:
            if active: S.SboxLayer("SB", r, 2, Midori64_Sb0_Sbox, mask=None, index=[[j] for j in range(16)])
            else:      S.AddIdentityLayer("SB_ID", r, 2)
        else:           # SSb_(i mod 4): four masked S-box layers (identity on the other cells)
            for k in range(4):
                if active: S.SboxLayer(f"SSB{k}", r, 2 + k, _SSB[k],
                                       mask=[1 if j % 4 == k else 0 for j in range(16)], index=None)
                else:      S.AddIdentityLayer(f"SSB{k}_ID", r, 2 + k)

    def gen_rounds_constant_table(self, n_beta):
        # alpha_i/beta_i: 4x4 binary matrices from the fractional hex of pi, added to the
        # LSB of each cell. Row j is a hex digit; bit (msb=col0) at (row j, col) hits cell 4*col+j.
        table = [[0] * 16 for _ in range(self.nbr_rounds)]   # indexed by crt_round-1
        for i in range(n_beta):                              # beta_i is used by round i+2 -> row i+1
            cells = [0] * 16
            for row in range(4):
                v = _BETA_HEX[i][row]
                for col in range(4):
                    cells[4 * col + row] = (v >> (3 - col)) & 1
            table[i + 1] = cells
        return table

    def gen_test_vectors(self, version=64):
        if version == 64:   # Midori64 paper, Appendix A
            return [
                {'plaintext': [0] * 16, 'key': [0] * 32,
                 'output': [0x3, 0xc, 0x9, 0xc, 0xc, 0xe, 0xd, 0xa, 0x2, 0xb, 0xb, 0xd, 0x4, 0x4, 0x9, 0xa]},
                {'plaintext': [0x4, 0x2, 0xc, 0x2, 0x0, 0xf, 0xd, 0x3, 0xb, 0x5, 0x8, 0x6, 0x8, 0x7, 0x9, 0xe],
                 'key': [0x6, 0x8, 0x7, 0xd, 0xe, 0xd, 0x3, 0xb, 0x3, 0xc, 0x8, 0x5, 0xb, 0x3, 0xf, 0x3,
                         0x5, 0xb, 0x1, 0x0, 0x0, 0x9, 0x8, 0x6, 0x3, 0xe, 0x2, 0xa, 0x8, 0xc, 0xb, 0xf],
                 'output': [0x6, 0x6, 0xb, 0xc, 0xd, 0xc, 0x6, 0x2, 0x7, 0x0, 0xd, 0x9, 0x0, 0x1, 0xc, 0xd]},
            ]
        # Midori128 paper, Appendix A (16 bytes per value)
        return [
            {'plaintext': [0] * 16, 'key': [0] * 16,
             'output': [0xc0, 0x55, 0xcb, 0xb9, 0x59, 0x96, 0xd1, 0x49,
                        0x02, 0xb6, 0x05, 0x74, 0xd5, 0xe7, 0x28, 0xd6]},
            {'plaintext': [0x51, 0x08, 0x4c, 0xe6, 0xe7, 0x3a, 0x5c, 0xa2,
                           0xec, 0x87, 0xd7, 0xba, 0xbc, 0x29, 0x75, 0x43],
             'key': [0x68, 0x7d, 0xed, 0x3b, 0x3c, 0x85, 0xb3, 0xf3,
                     0x5b, 0x10, 0x09, 0x86, 0x3e, 0x2a, 0x8c, 0xbf],
             'output': [0x1e, 0x0a, 0xc4, 0xfd, 0xdf, 0xf7, 0x1b, 0x4c,
                        0x18, 0x01, 0xb7, 0x3e, 0xe4, 0xaf, 0xc8, 0x3d]},
        ]


def MIDORI_BLOCKCIPHER(r=None, version=None, copy_operator=False):
    if version is None: version = 64
    if version == 64:
        w, nk = 4, 32
    elif version == 128:
        w, nk = 8, 16
    else:
        raise ValueError(f"Midori supports version 64 or 128, got {version}")
    p = [var.Variable(w, ID="p" + str(i)) for i in range(16)]
    k = [var.Variable(w, ID="k" + str(i)) for i in range(nk)]
    c = [var.Variable(w, ID="c" + str(i)) for i in range(16)]
    cipher = Midori_block_cipher("Midori" + str(version), version, p, k, c, nbr_rounds=r)
    cipher.post_initialization(copy_operator=copy_operator)
    return cipher
