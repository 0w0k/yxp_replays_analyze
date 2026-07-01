"""Unit tests for build_cards.py — fam(), level_of(), and pack/unpack logic."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_cards


class TestFam:
    def test_strips_level(self):
        assert build_cards.fam(10020001) == 10000001

    def test_level_zero(self):
        assert build_cards.fam(10000001) == 10000001

    def test_zero(self):
        assert build_cards.fam(0) == 0

    def test_consistency_across_levels(self):
        base = 50000099
        results = {build_cards.fam(base + lv * 10000) for lv in range(5)}
        assert len(results) == 1
        assert results.pop() == base


class TestLevelOf:
    def test_level_zero(self):
        assert build_cards.level_of(10000001) == 1  # (0 % 100) + 1

    def test_level_one(self):
        assert build_cards.level_of(10010001) == 2  # (1 % 100) + 1

    def test_level_two(self):
        assert build_cards.level_of(10020001) == 3  # (2 % 100) + 1

    def test_level_three(self):
        assert build_cards.level_of(10030001) == 4

    def test_fam_level_roundtrip(self):
        cid = 10020001
        f = build_cards.fam(cid)
        lv = build_cards.level_of(cid)
        assert lv == 3
        assert f == 10000001


class TestPackUnpack:
    """Test the key packing/unpacking used in the main aggregation loop.

    Key = ((((s * PCHAR + ch) * PCAR + car) * PLVL + lv) * PRD + rn) * PFAM + fi
    """

    def _pack(self, s, ch, car, lv, rn, fi):
        PCHAR = build_cards.PCHAR
        PCAR = build_cards.PCAR
        PLVL = build_cards.PLVL
        PRD = build_cards.PRD
        PFAM = build_cards.PFAM
        return (((((s * PCHAR + ch) * PCAR + car) * PLVL + lv) * PRD + rn) * PFAM + fi)

    def test_roundtrip(self):
        s, ch, car, lv, rn, fi = 0, 5, 3, 2, 10, 42
        key = self._pack(s, ch, car, lv, rn, fi)
        # unpack is defined inside main(), replicate it here
        PFAM = build_cards.PFAM
        PRD = build_cards.PRD
        PLVL = build_cards.PLVL
        PCAR = build_cards.PCAR
        PCHAR = build_cards.PCHAR

        fi2 = key % PFAM
        b = key // PFAM
        rn2 = b % PRD
        b //= PRD
        lv2 = b % PLVL
        b //= PLVL
        car2 = b % PCAR
        b //= PCAR
        ch2 = b % PCHAR
        s2 = b // PCHAR

        assert (s2, ch2, car2, lv2, rn2, fi2) == (s, ch, car, lv, rn, fi)

    def test_different_keys_for_different_inputs(self):
        k1 = self._pack(0, 1, 2, 3, 4, 5)
        k2 = self._pack(0, 1, 2, 3, 4, 6)
        k3 = self._pack(0, 1, 2, 3, 5, 5)
        assert k1 != k2
        assert k1 != k3

    def test_zero_key(self):
        assert self._pack(0, 0, 0, 0, 0, 0) == 0

    def test_max_dimensions(self):
        # verify no overflow for max typical values
        s, ch, car, lv, rn, fi = 0, 23, 7, 7, 27, 500
        key = self._pack(s, ch, car, lv, rn, fi)
        assert key > 0  # no overflow

    def test_season_idx_mapping(self):
        assert build_cards.SEASON_IDX == {9: 0}
        assert build_cards.SEASONS == [9]
