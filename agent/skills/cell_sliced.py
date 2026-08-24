"""Numeric expansion helpers that turn a CELL-sliced SPN description (a cipher whose
state is n-bit cells with a GF(2^n) diffusion matrix, a cell permutation, and a key
schedule that cyclically rotates whole key halves by a bit amount) into the concrete
word_bitsize=1 layers OCP needs.

Why this exists: some ciphers (e.g. FUTURE) mix two incompatible granularities - a 4-bit
cell data path (4-bit S-box + GF(2^4) MixColumn) AND a key schedule that rotates a whole
64-bit key half by 5 bits (5 is not a multiple of the 4-bit cell, so no word rotation can
express it). OCP's AddRoundKey needs the subkey and state to share a word width, so the
ONLY faithful modeling is fully bit-sliced (word_bitsize=1). Hand-writing the resulting
bit-level MixColumn matrix, cell permutation, and key-rotation permutation is exactly what
an LLM gets wrong; these helpers derive them deterministically instead.

Bit-order convention (matches the FUTURE paper and its reference implementation): the state
is bits b0..b_{N-1} with b0 the MOST significant. Cell i is bits b_{c*i}..b_{c*i+c-1} where
c is the cell bit width, and b_{c*i} is that cell's MSB. As a GF(2^c) integer the cell value
is sum_j bit(b_{c*i+j}) * 2^(c-1-j). So within a cell, word offset p (0-based, MSB first)
corresponds to GF-integer bit (c-1-p).
"""
from typing import List


def gf_mul(a: int, b: int, poly: int, bits: int) -> int:
    """Multiply a*b in GF(2^bits) modulo the reduction polynomial `poly`.

    `poly` is the FULL polynomial including its top term (GF(2^4) x^4+x+1 -> 0x13,
    GF(2^8) AES -> 0x11B).
    """
    result = 0
    for _ in range(bits):
        if b & 1:
            result ^= a
        b >>= 1
        high = a & (1 << (bits - 1))
        a <<= 1
        if high:
            a ^= poly
        a &= (1 << bits) - 1
    return result


def gf_const_bit_matrix(c: int, poly: int, bits: int, msb_first: bool = True) -> List[List[int]]:
    """The bits x bits GF(2) matrix of "multiply by the constant c in GF(2^bits)".

    Column j is the bit expansion of c * (basis element for input bit j). With
    msb_first the row/column index p maps to GF-integer bit (bits-1-p), matching the
    MSB-first word order described in the module docstring; otherwise index p == bit p.
    """
    def to_bit(val, p):
        return (val >> (bits - 1 - p if msb_first else p)) & 1

    mat = [[0] * bits for _ in range(bits)]
    for in_p in range(bits):
        in_bit = bits - 1 - in_p if msb_first else in_p
        prod = gf_mul(c, 1 << in_bit, poly, bits)
        for out_p in range(bits):
            mat[out_p][in_p] = to_bit(prod, out_p)
    return mat


def gf_matrix_to_bit_matrix(int_matrix: List[List[int]], poly: int, bits: int,
                            msb_first: bool = True) -> List[List[int]]:
    """Expand an m x m GF(2^bits) matrix (integer coefficients) into the
    (m*bits) x (m*bits) GF(2) matrix acting on the flattened bit vector.

    Cell k occupies bit positions [k*bits, k*bits+bits) in the flattened vector, in the
    same MSB-first order as the state words.
    """
    m = len(int_matrix)
    n = m * bits
    big = [[0] * n for _ in range(n)]
    for r in range(m):
        for k in range(m):
            block = gf_const_bit_matrix(int_matrix[r][k], poly, bits, msb_first)
            for i in range(bits):
                for j in range(bits):
                    big[r * bits + i][k * bits + j] ^= block[i][j]
    return big


def cell_perm_to_bit_perm(cell_table: List[int], bits: int) -> List[int]:
    """Turn a cell permutation (new cell j takes old cell cell_table[j]) into the
    equivalent bit permutation over cells of `bits` bits each. Each cell's bits move
    together, preserving their in-cell order."""
    table = []
    for new_cell in cell_table:
        for b in range(bits):
            table.append(new_cell * bits + b)
    return table


def bit_rotation_perm(width: int, amount: int, direction: str = "l") -> List[int]:
    """Permutation table for a cyclic rotation of a `width`-bit register by `amount`
    bits. Bit index 0 is the MSB. A LEFT rotation moves higher-significance bits toward
    the MSB, i.e. new[i] = old[(i + amount) mod width]; right is the inverse."""
    amount %= width
    if direction == "l":
        return [(i + amount) % width for i in range(width)]
    return [(i - amount) % width for i in range(width)]


if __name__ == "__main__":
    # GF(2^4) mod x^4+x+1 (0x13) sanity: x * x^3 = x^4 = x+1 -> gf_mul(2,8)=3.
    assert gf_mul(2, 8, 0x13, 4) == 3, gf_mul(2, 8, 0x13, 4)
    assert gf_mul(1, 9, 0x13, 4) == 9
    assert gf_mul(3, 3, 0x13, 4) == gf_mul(3, 3, 0x13, 4)  # associativity smoke

    # Multiply-by-1 must be the identity matrix in either bit order.
    for msb in (True, False):
        idm = gf_const_bit_matrix(1, 0x13, 4, msb)
        assert idm == [[1 if i == j else 0 for j in range(4)] for i in range(4)], (msb, idm)

    # A GF-matrix expansion of a permutation-like scalar matrix must be invertible over
    # GF(2). Use FUTURE's MixColumn M (MDS -> its bit expansion is invertible).
    M = [[8, 9, 1, 8], [3, 2, 9, 9], [2, 3, 8, 9], [9, 9, 8, 1]]
    BM = gf_matrix_to_bit_matrix(M, 0x13, 4)
    assert len(BM) == 16 and len(BM[0]) == 16

    # GF(2) rank of BM must be full (16) since M is MDS/invertible.
    def gf2_rank(rows):
        rows = [r[:] for r in rows]
        n = len(rows[0]); rank = 0
        for col in range(n):
            piv = next((r for r in range(rank, len(rows)) if rows[r][col]), None)
            if piv is None:
                continue
            rows[rank], rows[piv] = rows[piv], rows[rank]
            for r in range(len(rows)):
                if r != rank and rows[r][col]:
                    rows[r] = [a ^ b for a, b in zip(rows[r], rows[rank])]
            rank += 1
        return rank
    assert gf2_rank(BM) == 16, gf2_rank(BM)

    # cell perm -> bit perm: FUTURE ShiftRow, 4-bit cells.
    sr = cell_perm_to_bit_perm([0, 13, 10, 7, 4, 1, 14, 11, 8, 5, 2, 15, 12, 9, 6, 3], 4)
    assert len(sr) == 64 and sorted(sr) == list(range(64))
    assert sr[:8] == [0, 1, 2, 3, 52, 53, 54, 55]  # cell0 stays, cell1 <- old cell13 (52..55)

    # bit rotation: left by 5 over 64 bits, MSB=bit0.
    rot = bit_rotation_perm(64, 5, "l")
    assert rot[0] == 5 and rot[59] == 0 and sorted(rot) == list(range(64))
    print("cell_sliced self-tests passed")
