"""Unit tests for build_tianyan.py — home_side() and SLOT_OF mapping."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_tianyan


class TestHomeSide:
    def _make_rd(self, p1_uid, p2_uid):
        return {
            "p1": {"publicData": {"uid": p1_uid}},
            "p2": {"publicData": {"uid": p2_uid}},
        }

    def test_owner_is_p2(self):
        rd = self._make_rd("alice", "bob")
        assert build_tianyan.home_side(rd, "bob") == "p2"

    def test_owner_is_p1(self):
        rd = self._make_rd("alice", "bob")
        assert build_tianyan.home_side(rd, "alice") == "p1"

    def test_owner_not_found(self):
        rd = self._make_rd("alice", "bob")
        assert build_tianyan.home_side(rd, "charlie") is None


class TestSlotOf:
    def test_strategy_3(self):
        assert build_tianyan.SLOT_OF[3] == 0

    def test_strategy_6(self):
        assert build_tianyan.SLOT_OF[6] == 1

    def test_strategy_9(self):
        assert build_tianyan.SLOT_OF[9] == 2

    def test_only_three_slots(self):
        assert len(build_tianyan.SLOT_OF) == 3

    def test_unknown_strategy(self):
        assert build_tianyan.SLOT_OF.get(1) is None
        assert build_tianyan.SLOT_OF.get(12) is None


class TestConfig:
    def test_min_thresholds(self):
        assert build_tianyan.MIN_HELD == 8
        assert build_tianyan.MIN_DRAFT == 8

    def test_scores(self):
        assert build_tianyan.MIN_SCORE == 4000
        assert build_tianyan.HI_SCORE == 6000

    def test_seasons(self):
        assert build_tianyan.SEASONS == [9]
        assert build_tianyan.SEASON_IDX == {9: 0}
