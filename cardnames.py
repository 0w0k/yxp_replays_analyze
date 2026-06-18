"""Shared card-name resolver covering the current season.

The bundled single-card catalog (data/data_4000.json) is from seasons 7-8 and is
missing ~119 of 天衍万象's card families. card_id_map.json (from the sibling
card-counter project) is a current id->cn-name map that covers everything, so we
merge: cn/img/sect from the old catalog when present, else cn from card_id_map;
en falls back to cn for new cards.
"""
import json
import os

CARD_ID_MAP = os.environ.get("CARD_ID_MAP") or \
    r"D:\Coding\yixian-card-counter-with-proxy\proxy\card_id_map.json"
HERE = os.path.dirname(os.path.abspath(__file__))
SECT_MAP = os.path.join(HERE, "data", "sect_map.json")  # famid -> sect code (wiki-derived)


def fam(c):
    return c - ((c // 10000) % 100) * 10000


def load_resolver(ref_cards_path):
    old = {}
    try:
        ref = json.load(open(ref_cards_path, encoding="utf-8"))
        for c in ref["cards"]:
            old[fam(c["img"])] = c
    except Exception as e:
        print("cardnames: no ref catalog", e)
    try:
        cim = json.load(open(CARD_ID_MAP, encoding="utf-8"))
        cim = {int(k): v for k, v in cim.items()}
    except Exception as e:
        print("cardnames: no card_id_map", e)
        cim = {}
    try:
        smap = {int(k): v for k, v in json.load(open(SECT_MAP, encoding="utf-8")).items()}
    except Exception as e:
        print("cardnames: no sect_map", e)
        smap = {}

    def resolve(famid):
        o = old.get(famid)
        cn = (o.get("cn") if o else None) or cim.get(famid) or cim.get(famid + 10000) or ""
        en = (o.get("en") if o else None) or cn or f"#{famid}"
        # sect: wiki-derived map is authoritative; fall back to old catalog
        sect = smap.get(famid) or (o.get("sect") if o else None) or ""
        img = (o.get("img") if o else None) or famid
        return {"en": en, "cn": cn, "sect": sect, "img": img}

    return resolve
