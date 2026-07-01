"""Unit tests for build_decks.py — fam() and pack/unpack logic."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_decks


class TestFam:
    def test_strips_level(self):
        assert build_decks.fam(10020001) == 10000001

    def test_docstring(self):
        assert build_decks.fam.__doc__ is not None


class TestPackUnpack:
    """Test the single-key packing used in build_decks.

    singles key: base * PFAM + a,  where base = ((s * PCHAR + ch) * PCAR + car) * PRD + rn
    pairs key:   (base * PFAM + a) * PFAM + b
    """

    def _base(self, s, ch, car, rn):
        return ((s * build_decks.PCHAR + ch) * build_decks.PCAR + car) * build_decks.PRD + rn

    def _unpack_base(self, k):
        PFAM = build_decks.PFAM
        PRD = build_decks.PRD
        PCAR = build_decks.PCAR
        PCHAR = build_decks.PCHAR
        b = k // PFAM
        rd = b % PRD
        b //= PRD
        car = b % PCAR
        b //= PCAR
        ch = b % PCHAR
        s = b // PCHAR
        return s, ch, car, rd

    def test_single_roundtrip(self):
        s, ch, car, rn, a = 0, 3, 2, 5, 10
        base = self._base(s, ch, car, rn)
        key = base * build_decks.PFAM + a
        s2, ch2, car2, rn2 = self._unpack_base(key)
        a2 = key % build_decks.PFAM
        assert (s2, ch2, car2, rn2, a2) == (s, ch, car, rn, a)

    def test_pair_roundtrip(self):
        s, ch, car, rn, a, b = 0, 3, 2, 5, 10, 20
        base = self._base(s, ch, car, rn)
        key = (base * build_decks.PFAM + a) * build_decks.PFAM + b
        b2 = key % build_decks.PFAM
        s2, ch2, car2, rn2 = self._unpack_base(key // build_decks.PFAM)
        a2 = (key // build_decks.PFAM) % build_decks.PFAM
        assert (s2, ch2, car2, rn2, a2, b2) == (s, ch, car, rn, a, b)

    def test_different_pairs_different_keys(self):
        base = self._base(0, 0, 0, 0)
        k1 = (base * build_decks.PFAM + 1) * build_decks.PFAM + 2
        k2 = (base * build_decks.PFAM + 2) * build_decks.PFAM + 1
        assert k1 != k2

    def test_stride_constants(self):
        assert build_decks.PCHAR == 32
        assert build_decks.PCAR == 8
        assert build_decks.PRD == 32
        assert build_decks.PFAM == 512

    def test_season_config(self):
        assert build_decks.SEASONS == [9]
        assert build_decks.MIN_SCORE_4000 == 4000
        assert build_decks.MIN_SCORE_6000 == 6000
