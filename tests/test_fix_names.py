"""Unit tests for fix_names.py — fix_card_array and fix_fates with mocked data."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fix_names
import cardnames


@pytest.fixture
def mock_resolver(monkeypatch):
    """Replace the module-level resolver with a controlled mock."""
    lookup = {
        100: {"en": "Fireball", "cn": "火球术", "sect": "fe", "img": 100},
        200: {"en": "IceSpike", "cn": "冰锥术", "sect": "sw", "img": 200},
    }
    default = {"en": "#unknown", "cn": "", "sect": "", "img": 0}

    def mock_resolve(famid):
        return lookup.get(famid, default)

    monkeypatch.setattr(fix_names, "resolve", mock_resolve)
    monkeypatch.setattr(fix_names, "famof", cardnames.fam)
    return lookup


class TestFixCardArray:
    def test_updates_card_fields(self, mock_resolver, tmp_path):
        data = {
            "cards": [
                {"en": "OldFire", "cn": "旧火", "sect": "xx", "img": 100},
                {"en": "OldIce", "cn": "旧冰", "sect": "yy", "img": 200},
            ]
        }
        path = str(tmp_path / "test.json")
        with open(path, "w") as f:
            json.dump(data, f)

        fix_names.fix_card_array(path)

        result = json.load(open(path))
        assert result["cards"][0]["en"] == "Fireball"
        assert result["cards"][0]["cn"] == "火球术"
        assert result["cards"][0]["sect"] == "fe"
        assert result["cards"][1]["en"] == "IceSpike"
        assert result["cards"][1]["cn"] == "冰锥术"
        assert result["cards"][1]["sect"] == "sw"

    def test_no_change_when_already_correct(self, mock_resolver, tmp_path):
        data = {
            "cards": [
                {"en": "Fireball", "cn": "火球术", "sect": "fe", "img": 100},
            ]
        }
        path = str(tmp_path / "test.json")
        with open(path, "w") as f:
            json.dump(data, f)

        fix_names.fix_card_array(path)

        result = json.load(open(path))
        assert result["cards"][0]["en"] == "Fireball"


class TestTalentIdIndex:
    def test_returns_dicts(self, monkeypatch):
        monkeypatch.setattr(fix_names, "COUNTER", "/nonexistent")
        cn2id, en2id = fix_names.talent_id_index()
        assert isinstance(cn2id, dict)
        assert isinstance(en2id, dict)

    def test_with_mock_maps(self, tmp_path, monkeypatch):
        monkeypatch.setattr(fix_names, "COUNTER", str(tmp_path))
        # fate_talent_map.json
        ftm = {
            "42": {"name": "Talent42", "nameCn": "天赋42"},
            "99": {"name": "Talent99", "nameCn": "天赋99"},
        }
        with open(tmp_path / "fate_talent_map.json", "w") as f:
            json.dump(ftm, f)
        # fate_id_map.json
        fid = {"100": "天赋100"}
        with open(tmp_path / "fate_id_map.json", "w") as f:
            json.dump(fid, f)

        cn2id, en2id = fix_names.talent_id_index()
        assert cn2id["天赋42"] == 42
        assert cn2id["天赋99"] == 99
        assert en2id["Talent42"] == 42
        assert cn2id["天赋100"] == 100


class TestFixFates:
    def test_updates_daoyun_names(self, mock_resolver, tmp_path):
        data = {
            "talentNames": [],
            "daoyunNames": [
                {"en": "#100", "cn": "", "img": 100},
            ],
        }
        path = str(tmp_path / "fates.json")
        with open(path, "w") as f:
            json.dump(data, f)

        fix_names.fix_fates(path)

        result = json.load(open(path))
        dy = result["daoyunNames"][0]
        assert dy["en"] == "Fireball"
        assert dy["cn"] == "火球术"

    def test_talent_hash_id_recovery(self, mock_resolver, monkeypatch, tmp_path):
        monkeypatch.setattr(fix_names, "COUNTER", "/nonexistent")
        data = {
            "talentNames": [
                {"en": "#42", "cn": "", "img": 0},
            ],
            "daoyunNames": [],
        }
        path = str(tmp_path / "fates.json")
        with open(path, "w") as f:
            json.dump(data, f)

        fix_names.fix_fates(path)

        result = json.load(open(path))
        assert result["talentNames"][0]["img"] == 42
