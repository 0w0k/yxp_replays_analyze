"""Unit tests for build_combos.py — fam(), pack/unpack, and config constants."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_combos


class TestFam:
    def test_strips_level(self):
        assert build_combos.fam(10020001) == 10000001

    def test_level_zero(self):
        assert build_combos.fam(10000001) == 10000001

    def test_zero(self):
        assert build_combos.fam(0) == 0


class TestPackUnpack:
    """Combos use a simpler dim key (no round for 3+ card combos):
    dim = (s * PCHAR + ch) * PCAR + car
    """

    def _pack(self, s, ch, car):
        return (s * build_combos.PCHAR + ch) * build_combos.PCAR + car

    def _unpack(self, dim):
        car = dim % build_combos.PCAR
        b = dim // build_combos.PCAR
        ch = b % build_combos.PCHAR
        s = b // build_combos.PCHAR
        return s, ch, car

    def test_roundtrip(self):
        for s, ch, car in [(0, 0, 0), (0, 5, 3), (0, 23, 7)]:
            dim = self._pack(s, ch, car)
            assert self._unpack(dim) == (s, ch, car)

    def test_different_inputs_different_keys(self):
        k1 = self._pack(0, 1, 2)
        k2 = self._pack(0, 2, 1)
        assert k1 != k2


class TestConfig:
    def test_combo_sizes(self):
        assert build_combos.MIN_K == 3
        assert build_combos.MAX_K == 6

    def test_min_sup_keys(self):
        for k in range(2, 7):
            assert k in build_combos.MIN_SUP

    def test_min_row_keys(self):
        for k in range(2, 7):
            assert k in build_combos.MIN_ROW

    def test_lean_cap_keys(self):
        for k in range(3, 7):
            assert k in build_combos.LEAN_CAP

    def test_stride_constants(self):
        assert build_combos.PCHAR == 32
        assert build_combos.PCAR == 8

    def test_season_config(self):
        assert build_combos.SEASONS == [9]
        assert build_combos.SEASON_IDX == {9: 0}
        assert build_combos.MIN_SCORE == 4000
        assert build_combos.HI_SCORE == 6000
