"""Unit tests for tools/sbox_division_trails.py - the bit-based two-subset division-trail
kernel used by operators/Sbox.py for INTEGRAL_TWOSUBSET S-box modeling. Pure functions;
the exact cases (Mobius transform, identity-S-box ANF, 1-bit trails) are hand-verified.
"""
from tools import sbox_division_trails as sbd

import pytest


def test_mobius_transform_of_singleton_indicator_is_all_ones():
    table = [1, 0, 0, 0]           # indicator of input 0
    sbd._mobius_transform_in_place(table, 2)
    assert table == [1, 1, 1, 1]   # ANF of that indicator: (1+x0)(1+x1) = 1 + x0 + x1 + x0*x1


def test_anf_support_terms_of_identity_sbox():
    # identity S-box: output-mask m's ANF is the single monomial m
    assert sbd.anf_support_terms([0, 1], 1) == [[], [1]]
    assert sbd.anf_support_terms([0, 1, 2, 3], 2) == [[], [1], [2], [3]]


def test_trails_to_truthtable_sets_indexed_bits():
    assert sbd.trails_to_truthtable([[0, 0], [1, 1]], 2) == "1001"   # indices 0 and 3
    assert sbd.trails_to_truthtable([[0, 1, 0]], 3) == "00100000"    # index 2


def test_trails_to_truthtable_rejects_width_mismatch():
    with pytest.raises(ValueError, match="does not match expected width"):
        sbd.trails_to_truthtable([[0, 1]], 3)


def test_division_trails_of_1bit_identity():
    # input 0 -> all-zero trail; input 1 -> output 1
    assert sbd.sbox_two_subset_division_trails([0, 1], 1) == [[0, 0], [1, 1]]


def test_two_subset_truthtable_1bit_identity_is_hand_value():
    assert sbd.two_subset_sbox_truthtable([0, 1], 1) == "1001"


def test_two_subset_truthtable_structural_invariants_on_present_sbox():
    present = [0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD, 0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2]
    tt = sbd.two_subset_sbox_truthtable(present, 4)

    assert len(tt) == 2 ** 8 and set(tt) <= {"0", "1"}
    assert tt[0] == "1"  # the all-zero division trail is always present
    # composition consistency: the public helper == trails_to_truthtable o division_trails
    trails = sbd.sbox_two_subset_division_trails(present, 4)
    assert trails[0] == [0] * 8 and all(len(t) == 8 for t in trails)
    assert tt == sbd.trails_to_truthtable(trails, 8)


def test_present_sbox_has_exact_known_division_trail_count():
    # Exact count guarding the minimal-antichain logic (which the identity/structural cases
    # never exercise). 47 = all-zero trail + the minimal output masks over all 15 nonzero
    # inputs; cross-checked against an independent two-pass antichain computation of the same
    # ANF-based propagation, and equal to the number of set bits in the trail truth table.
    present = [0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD, 0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2]
    trails = sbd.sbox_two_subset_division_trails(present, 4)

    assert len(trails) == 47
    assert len({tuple(t) for t in trails}) == 47  # no duplicate trails
    assert sbd.two_subset_sbox_truthtable(present, 4).count("1") == 47
