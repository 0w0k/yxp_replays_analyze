"""Unit tests for build_fates.py — fam(), tbase(), and home_side()."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_fates


class TestFam:
    def test_strips_level(self):
        assert build_fates.fam(10020001) == 10000001

    def test_level_zero(self):
        assert build_fates.fam(10000001) == 10000001


class TestTbase:
    def test_strips_to_base(self):
        # tbase = tid % 10000
        assert build_fates.tbase(10001) == 1
        assert build_fates.tbase(20042) == 42

    def test_already_base(self):
        assert build_fates.tbase(42) == 42

    def test_zero(self):
        assert build_fates.tbase(0) == 0

    def test_exact_10000(self):
        assert build_fates.tbase(10000) == 0

    def test_large_id(self):
        assert build_fates.tbase(30099) == 99


class TestHomeSide:
    def _make_rd(self, p1_uid, p2_uid):
        return {
            "p1": {"publicData": {"uid": p1_uid}},
            "p2": {"publicData": {"uid": p2_uid}},
        }

    def test_owner_is_p2(self):
        rd = self._make_rd("alice", "bob")
        assert build_fates.home_side(rd, "bob") == "p2"

    def test_owner_is_p1(self):
        rd = self._make_rd("alice", "bob")
        assert build_fates.home_side(rd, "alice") == "p1"

    def test_owner_not_found(self):
        rd = self._make_rd("alice", "bob")
        assert build_fates.home_side(rd, "charlie") is None

    def test_p2_checked_first(self):
        # if both p1 and p2 have the same uid, p2 is returned (per code order)
        rd = self._make_rd("same", "same")
        assert build_fates.home_side(rd, "same") == "p2"

    def test_numeric_uid(self):
        rd = self._make_rd(123, 456)
        assert build_fates.home_side(rd, 456) == "p2"
        assert build_fates.home_side(rd, 123) == "p1"
        assert build_fates.home_side(rd, 789) is None

    def test_config(self):
        assert build_fates.MIN_HELD == 8
        assert build_fates.MIN_DRAFT == 8
        assert build_fates.SEASONS == [9]
