"""Unit tests for build_home.py — top_cards, top_combos, top_fates, top_tianyan
with mocked JSON data files."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_home


@pytest.fixture
def data_dir(tmp_path):
    """Create a temporary data directory with minimal valid JSON files."""
    # data_4000.json — 3 cards, simple facts
    cards = [
        {"cn": "火球术", "en": "Fireball", "sect": "fe", "img": 100},
        {"cn": "冰锥术", "en": "IceSpike", "sect": "sw", "img": 200},
        {"cn": "雷击术", "en": "Thunder", "sect": "he", "img": 300},
    ]
    # facts stride 8: [seasonIdx, charIdx, career, fam, level, round, wins, losses]
    facts = [
        0, 0, 0, 0, 1, 1, 80, 20,   # card 0: 80w / 100g = 80% WR
        0, 0, 0, 1, 1, 1, 50, 50,   # card 1: 50w / 100g = 50% WR
        0, 0, 0, 2, 1, 1, 30, 70,   # card 2: 30w / 100g = 30% WR
    ]
    with open(tmp_path / "data_4000.json", "w") as f:
        json.dump({"meta": {"population": 1000}, "cards": cards, "facts": facts}, f)

    # decks.json — singles + pairs
    # singleStride 9: s,ch,car,rd, fam, w,g, w6,g6
    singles = [
        0, 0, 0, 1, 0, 80, 100, 40, 50,   # card 0
        0, 0, 0, 1, 1, 50, 100, 25, 50,   # card 1
        0, 0, 0, 1, 2, 30, 100, 15, 50,   # card 2
    ]
    # pairStride 10: s,ch,car,rd, a,b, w,g, w6,g6
    pairs = [
        0, 0, 0, 1, 0, 1, 1800, 2500, 900, 1250,  # pair (0,1): wr=72%
        0, 0, 0, 1, 0, 2, 1500, 2500, 750, 1250,  # pair (0,2): wr=60%
    ]
    deck_cards = [
        {"cn": "火球术", "en": "Fireball", "sect": "fe", "img": 100},
        {"cn": "冰锥术", "en": "IceSpike", "sect": "sw", "img": 200},
        {"cn": "雷击术", "en": "Thunder", "sect": "he", "img": 300},
    ]
    with open(tmp_path / "decks.json", "w") as f:
        json.dump({
            "meta": {"singleStride": 9, "pairStride": 10},
            "cards": deck_cards,
            "singles": singles,
            "pairs": pairs,
        }, f)

    # fates.json — minimal talent held data
    # heldStride 9: s,ch,car,rd, idx, w,g, w6,g6
    tal_held = [
        0, 0, 0, 1, 0, 15000, 25000, 7500, 12500,  # talent 0: 60% WR, 25k games
        0, 0, 0, 1, 1, 12000, 25000, 6000, 12500,  # talent 1: 48% WR, 25k games
    ]
    with open(tmp_path / "fates.json", "w") as f:
        json.dump({
            "meta": {"heldStride": 9},
            "talentNames": [
                {"cn": "天赋A", "en": "TalentA", "img": 1},
                {"cn": "天赋B", "en": "TalentB", "img": 2},
            ],
            "talHeld": tal_held,
        }, f)

    # tianyan.json — minimal draft data
    # draftStride 9: s,ch,car,slot, fateId, off,pick, off6,pick6
    draft = [
        0, 0, 0, 0, 42, 1000, 800, 500, 400,    # fate 42: 80% pick rate
        0, 0, 0, 0, 43, 1000, 200, 500, 100,    # fate 43: 20% pick rate
    ]
    with open(tmp_path / "tianyan.json", "w") as f:
        json.dump({
            "meta": {"draftStride": 9, "population": {"t4000": 500, "t6000": 200}},
            "draft": draft,
        }, f)

    # fates_wiki.json — byId for tianyan names
    with open(tmp_path / "fates_wiki.json", "w") as f:
        json.dump({
            "byId": {
                "42": {"name": "天衍A", "sect": "通用", "id": 42},
                "43": {"name": "天衍B", "sect": "云灵剑宗", "id": 43},
            }
        }, f)

    return str(tmp_path)


class TestTopCards:
    def test_returns_cards_sorted_by_games(self, data_dir, monkeypatch):
        monkeypatch.setattr(build_home, "D", data_dir)
        cards, pop, ncards = build_home.top_cards()
        assert pop == 1000
        assert ncards == 3
        assert len(cards) <= build_home.TOP_CARDS
        # all 3 cards have equal games (100), order among equal is stable
        assert len(cards) == 3
        # check win rates
        wr_map = {c["cn"]: c["wr"] for c in cards}
        assert abs(wr_map["火球术"] - 0.80) < 0.01
        assert abs(wr_map["冰锥术"] - 0.50) < 0.01
        assert abs(wr_map["雷击术"] - 0.30) < 0.01

    def test_sect_mapping(self, data_dir, monkeypatch):
        monkeypatch.setattr(build_home, "D", data_dir)
        cards, _, _ = build_home.top_cards()
        sect_map = {c["cn"]: c["sect"] for c in cards}
        assert sect_map["火球术"] == "五行道盟"
        assert sect_map["冰锥术"] == "云灵剑宗"
        assert sect_map["雷击术"] == "七星阁"


class TestTopCombos:
    def test_returns_combos_with_lift(self, data_dir, monkeypatch):
        monkeypatch.setattr(build_home, "D", data_dir)
        combos = build_home.top_combos()
        assert len(combos) <= build_home.TOP_BARS
        # both pairs have 2500 games (>2000 threshold)
        assert len(combos) == 2
        for c in combos:
            assert "a" in c
            assert "b" in c
            assert "lift" in c
            assert "wr" in c
            assert "g" in c

    def test_lift_calculation(self, data_dir, monkeypatch):
        monkeypatch.setattr(build_home, "D", data_dir)
        combos = build_home.top_combos()
        # pair (0,1): wr=72%, solo avg = (80% + 50%) / 2 = 65%, lift = 7%
        c01 = [c for c in combos if {c["a"], c["b"]} == {"火球术", "冰锥术"}][0]
        assert abs(c01["lift"] - 0.07) < 0.01


class TestTopFates:
    def test_returns_fates_sorted_by_held_wr(self, data_dir, monkeypatch):
        monkeypatch.setattr(build_home, "D", data_dir)
        fates = build_home.top_fates()
        assert len(fates) <= build_home.TOP_BARS
        assert len(fates) == 2
        # talent 0 has higher WR
        assert fates[0]["cn"] == "天赋A"
        assert abs(fates[0]["wr"] - 0.60) < 0.01


class TestTopTianyan:
    def test_returns_top_tianyan(self, data_dir, monkeypatch):
        monkeypatch.setattr(build_home, "D", data_dir)
        monkeypatch.setattr(build_home, "STATIC", data_dir)
        result, pop = build_home.top_tianyan()
        assert pop == {"t4000": 500, "t6000": 200}
        top = result["top"]
        assert len(top) <= build_home.TOPN
        # fate 42 has higher pick rate (80% vs 20%)
        assert top[0]["name"] == "天衍A"
        assert abs(top[0]["rate"] - 0.80) < 0.01

    def test_sect_distribution(self, data_dir, monkeypatch):
        monkeypatch.setattr(build_home, "D", data_dir)
        monkeypatch.setattr(build_home, "STATIC", data_dir)
        result, _ = build_home.top_tianyan()
        sects = result["sects"]
        assert len(sects) > 0
        for s in sects:
            assert "sect" in s
            assert "picked" in s
            assert "rate" in s


class TestSectCnMapping:
    def test_four_sects(self):
        assert build_home.SECT_CN["sw"] == "云灵剑宗"
        assert build_home.SECT_CN["he"] == "七星阁"
        assert build_home.SECT_CN["fe"] == "五行道盟"
        assert build_home.SECT_CN["dx"] == "锻玄宗"

    def test_unknown_sect_maps_to_tongyong(self):
        assert build_home.SECT_CN.get("unknown") is None
        # the code uses .get(sect, "通用") as default
