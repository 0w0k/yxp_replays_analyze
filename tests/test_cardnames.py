"""Unit tests for cardnames.py — fam() and load_resolver()."""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cardnames


class TestFam:
    def test_strips_level_digits(self):
        # level = (id // 10000) % 100; fam strips that component
        # id = 10020001 -> level part = (10020001 // 10000) % 100 = 1002 % 100 = 2
        # fam = 10020001 - 2 * 10000 = 10020001 - 20000 = 10000001
        assert cardnames.fam(10020001) == 10000001

    def test_level_zero(self):
        # level = 0 -> fam(c) == c
        assert cardnames.fam(10000001) == 10000001

    def test_level_one(self):
        # id with level 1: (id // 10000) % 100 = 1 -> strip 10000
        assert cardnames.fam(10010001) == 10000001

    def test_multiple_levels_same_family(self):
        # levels 0, 1, 2, 3 all map to the same family
        base = 50000099
        for lv in range(4):
            assert cardnames.fam(base + lv * 10000) == base

    def test_zero_input(self):
        assert cardnames.fam(0) == 0

    def test_small_id(self):
        # id = 10001, level = (10001//10000)%100 = 1%100 = 1
        assert cardnames.fam(10001) == 1


class TestLoadResolver:
    def _make_ref(self, tmp, cards):
        path = os.path.join(tmp, "ref.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"cards": cards}, f)
        return path

    def _make_wiki(self, tmp, cards_dict):
        path = os.path.join(tmp, "wiki.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"cards": cards_dict}, f)
        return path

    def test_resolve_from_wiki(self, monkeypatch, tmp_path):
        wiki_cards = {"100": {"cn": "火球术", "en": "Fireball", "sect": "fe"}}
        wiki_path = self._make_wiki(str(tmp_path), wiki_cards)
        ref_path = self._make_ref(str(tmp_path), [])
        monkeypatch.setattr(cardnames, "WIKI_DATA", wiki_path)
        monkeypatch.setattr(cardnames, "CARD_ID_MAP", str(tmp_path / "nonexistent.json"))
        resolve = cardnames.load_resolver(ref_path)
        result = resolve(100)
        assert result["cn"] == "火球术"
        assert result["en"] == "Fireball"
        assert result["sect"] == "fe"

    def test_resolve_from_old_catalog(self, monkeypatch, tmp_path):
        ref_path = self._make_ref(str(tmp_path), [
            {"img": 200, "cn": "冰锥术", "en": "Ice Spike", "sect": "sw"}
        ])
        wiki_path = self._make_wiki(str(tmp_path), {})
        monkeypatch.setattr(cardnames, "WIKI_DATA", wiki_path)
        monkeypatch.setattr(cardnames, "CARD_ID_MAP", str(tmp_path / "nonexistent.json"))
        resolve = cardnames.load_resolver(ref_path)
        result = resolve(200)
        assert result["cn"] == "冰锥术"
        assert result["en"] == "Ice Spike"
        assert result["sect"] == "sw"

    def test_wiki_takes_precedence_over_old(self, monkeypatch, tmp_path):
        ref_path = self._make_ref(str(tmp_path), [
            {"img": 300, "cn": "旧名", "en": "OldName", "sect": "he"}
        ])
        wiki_cards = {"300": {"cn": "新名", "en": "NewName", "sect": "dx"}}
        wiki_path = self._make_wiki(str(tmp_path), wiki_cards)
        monkeypatch.setattr(cardnames, "WIKI_DATA", wiki_path)
        monkeypatch.setattr(cardnames, "CARD_ID_MAP", str(tmp_path / "nonexistent.json"))
        resolve = cardnames.load_resolver(ref_path)
        result = resolve(300)
        assert result["cn"] == "新名"
        assert result["en"] == "NewName"
        assert result["sect"] == "dx"

    def test_fallback_to_hash_name(self, monkeypatch, tmp_path):
        ref_path = self._make_ref(str(tmp_path), [])
        wiki_path = self._make_wiki(str(tmp_path), {})
        monkeypatch.setattr(cardnames, "WIKI_DATA", wiki_path)
        monkeypatch.setattr(cardnames, "CARD_ID_MAP", str(tmp_path / "nonexistent.json"))
        resolve = cardnames.load_resolver(ref_path)
        result = resolve(99999)
        assert result["en"] == "#99999"
        assert result["cn"] == ""
        assert result["sect"] == ""

    def test_img_from_old_catalog(self, monkeypatch, tmp_path):
        ref_path = self._make_ref(str(tmp_path), [
            {"img": 400, "cn": "A", "en": "A", "sect": "sw"}
        ])
        wiki_path = self._make_wiki(str(tmp_path), {})
        monkeypatch.setattr(cardnames, "WIKI_DATA", wiki_path)
        monkeypatch.setattr(cardnames, "CARD_ID_MAP", str(tmp_path / "nonexistent.json"))
        resolve = cardnames.load_resolver(ref_path)
        result = resolve(400)
        assert result["img"] == 400

    def test_img_fallback_to_famid(self, monkeypatch, tmp_path):
        ref_path = self._make_ref(str(tmp_path), [])
        wiki_path = self._make_wiki(str(tmp_path), {})
        monkeypatch.setattr(cardnames, "WIKI_DATA", wiki_path)
        monkeypatch.setattr(cardnames, "CARD_ID_MAP", str(tmp_path / "nonexistent.json"))
        resolve = cardnames.load_resolver(ref_path)
        result = resolve(12345)
        assert result["img"] == 12345
