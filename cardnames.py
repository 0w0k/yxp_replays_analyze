"""Shared card-name resolver covering the current season.

The bundled single-card catalog (data/data_4000.json) is from seasons 7-8 and is
missing ~119 of 天衍万象's card families. card_id_map.json (from the sibling
card-counter project) is a current id->cn-name map that covers everything, so we
merge: cn/img/sect from the old catalog when present, else cn from card_id_map;
en falls back to cn for new cards.
"""
import json
import os
import sys

CARD_ID_MAP = os.environ.get("CARD_ID_MAP") or \
    r"D:\Coding\yixian-card-counter-with-proxy\proxy\card_id_map.json"
HERE = os.path.dirname(os.path.abspath(__file__))
WIKI_DATA = os.path.join(HERE, "data", "wiki.json")  # single source of truth


def fam(c):
    return c - ((c // 10000) % 100) * 10000


def load_resolver(ref_cards_path):
    # img (wiki card-art id) still comes from the old catalog where present
    old = {}
    try:
        with open(ref_cards_path, encoding="utf-8") as _f:
            ref = json.load(_f)
        for c in ref["cards"]:
            old[fam(c["img"])] = c
    except FileNotFoundError:
        print(f"cardnames: ref catalog not found: {ref_cards_path}",
              file=sys.stderr)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"cardnames: ref catalog unreadable: {e}", file=sys.stderr)
    try:
        with open(WIKI_DATA, encoding="utf-8") as _f:
            wiki = json.load(_f)["cards"]
    except FileNotFoundError:
        print(f"cardnames: wiki.json not found: {WIKI_DATA}",
              file=sys.stderr)
        wiki = {}
    except (json.JSONDecodeError, KeyError) as e:
        print(f"cardnames: wiki.json unreadable: {e}", file=sys.stderr)
        wiki = {}
    try:
        with open(CARD_ID_MAP, encoding="utf-8") as _f:
            cim = {int(k): v for k, v in json.load(_f).items()}
    except FileNotFoundError:
        cim = {}
    except (json.JSONDecodeError, ValueError) as e:
        print(f"cardnames: card_id_map unreadable: {e}", file=sys.stderr)
        cim = {}

    def resolve(famid):
        w = wiki.get(str(famid), {})
        o = old.get(famid)
        cn = w.get("cn") or (o.get("cn") if o else None) or cim.get(famid) or cim.get(famid + 10000) or ""
        en = w.get("en") or (o.get("en") if o else None) or cn or f"#{famid}"
        sect = w.get("sect") or (o.get("sect") if o else None) or ""
        img = (o.get("img") if o else None) or famid
        return {"en": en, "cn": cn, "sect": sect, "img": img}

    return resolve
