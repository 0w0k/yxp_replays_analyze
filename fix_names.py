#!/usr/bin/env python3
"""Post-process built JSON to refresh names / sects / images through the
wiki-derived maps. Cheap: only rewrites name+sect+image fields, leaves the
aggregated fact arrays untouched. Run after the builds.

  - card sect:    data/sect_map.json (wiki-authoritative card -> sect)
  - card names:   cardnames.load_resolver (covers 天衍万象 new cards)
  - talent image: assets/fates/Icon_Talent_{baseid}.png  (id recovered via the
                  talent name maps)
  - dao-yun:      its granted card's art (img stays the card img)
"""
import json
import os

import cardnames

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "data", "data_4000.json")
COUNTER = os.environ.get("COUNTER_DIR") or os.path.join(HERE, "..", "yixian-card-counter-with-proxy", "proxy")
resolve = cardnames.load_resolver(REF)
famof = cardnames.fam


def fix_card_array(path):
    d = json.load(open(path, encoding="utf-8"))
    fixed = 0
    for c in d["cards"]:
        m = resolve(famof(c["img"]))
        if c.get("sect") != m["sect"] or c.get("en") != m["en"]:
            fixed += 1
        c["en"], c["cn"], c["sect"], c["img"] = m["en"], m["cn"], m["sect"], m["img"]
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{os.path.basename(path)}: refreshed {fixed}/{len(d['cards'])} cards")


def talent_id_index():
    """Build cn-name / en-name -> talent base id, to recover the base id for
    Icon_Talent images."""
    cn2id, en2id = {}, {}
    try:
        ftm = json.load(open(os.path.join(COUNTER, "fate_talent_map.json"), encoding="utf-8"))
        for k, v in ftm.items():
            if v.get("nameCn"):
                cn2id.setdefault(v["nameCn"], int(k))
            if v.get("name"):
                en2id.setdefault(v["name"], int(k))
    except Exception as e:
        print("fix: no fate_talent_map", e)
    try:
        fid = json.load(open(os.path.join(COUNTER, "fate_id_map.json"), encoding="utf-8"))
        for k, v in fid.items():
            cn2id.setdefault(v, int(k))
    except Exception as e:
        print("fix: no fate_id_map", e)
    return cn2id, en2id


def fix_fates(path):
    d = json.load(open(path, encoding="utf-8"))
    cn2id, en2id = talent_id_index()
    tfix = 0
    for c in d.get("talentNames", []):
        tid = cn2id.get(c.get("cn")) or en2id.get(c.get("en"))
        if not tid and str(c.get("en", "")).startswith("#") and c["en"][1:].isdigit():
            tid = int(c["en"][1:])
        if tid:
            c["img"] = tid           # -> assets/fates/Icon_Talent_{img}.png
            tfix += 1
    dfix = 0
    for c in d.get("daoyunNames", []):
        idv = c["img"] if c.get("img") else (
            int(c["en"][1:]) if str(c.get("en", "")).startswith("#") and c["en"][1:].isdigit() else 0)
        if not idv:
            continue
        m = resolve(famof(idv))
        if m["cn"]:
            c["en"], c["cn"], c["img"] = m["en"], m["cn"], m["img"]
            dfix += 1
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{os.path.basename(path)}: talent imgs {tfix}, dao-yun {dfix}")


if __name__ == "__main__":
    for f in ("decks.json", "data_4000.json", "data_6000.json"):
        p = os.path.join(HERE, "data", f)
        if os.path.exists(p):
            fix_card_array(p)
    fates = os.path.join(HERE, "data", "fates.json")
    if os.path.exists(fates):
        fix_fates(fates)
