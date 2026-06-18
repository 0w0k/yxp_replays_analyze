#!/usr/bin/env python3
"""Post-process already-built decks.json / fates.json to refresh card / dao-yun
names through the merged resolver (covers 天衍万象 new cards). Cheap: only rewrites
the name arrays, leaves the aggregated fact arrays untouched. Run after the builds.
"""
import json
import os

import cardnames

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "data", "data_4000.json")
resolve = cardnames.load_resolver(REF)
famof = cardnames.fam


def fix_decks(path):
    d = json.load(open(path, encoding="utf-8"))
    fixed = 0
    for c in d["cards"]:
        m = resolve(famof(c["img"]))
        if c.get("en") != m["en"] or c.get("cn") != m["cn"]:
            fixed += 1
        c["en"], c["cn"], c["sect"], c["img"] = m["en"], m["cn"], m["sect"], m["img"]
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{os.path.basename(path)}: refreshed {fixed}/{len(d['cards'])} card names")


def fix_fates(path):
    d = json.load(open(path, encoding="utf-8"))
    fixed = 0
    for c in d.get("daoyunNames", []):
        idv = c["img"] if c.get("img") else (
            int(c["en"][1:]) if str(c.get("en", "")).startswith("#") and c["en"][1:].isdigit() else 0)
        if not idv:
            continue
        m = resolve(famof(idv))
        if m["cn"] or not m["en"].startswith("#"):
            if c.get("cn") != m["cn"]:
                fixed += 1
            c["en"], c["cn"], c["img"] = m["en"], m["cn"], m["img"]
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{os.path.basename(path)}: refreshed {fixed} dao-yun names")


if __name__ == "__main__":
    decks = os.path.join(HERE, "data", "decks.json")
    fates = os.path.join(HERE, "data", "fates.json")
    if os.path.exists(decks):
        fix_decks(decks)
    if os.path.exists(fates):
        fix_fates(fates)
