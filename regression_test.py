#!/usr/bin/env python3
"""Regression test for the rebuilt aggregates. Run after build_*.py + fix_names.py.
Focuses on the home-player-detection fix: a character must only ever play its own
sect's sect-locked cards (+ neutral / career / dao-yun), never another sect's
exclusive cards. Plus data-integrity and win-rate sanity checks.

Exit 0 = all PASS, 1 = some FAIL.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda f: json.load(open(os.path.join(HERE, "data", f), encoding="utf-8"))
MAIN_SECTS = {"sw", "he", "fe", "dx"}
LEAD = {"1": "sw", "2": "he", "3": "fe", "4": "dx"}

fails, passes = [], []


def check(name, ok, detail=""):
    (passes if ok else fails).append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")


def main():
    decks = D("decks.json")
    cards4 = D("data_4000.json")
    fates = D("fates.json")
    wiki = D("wiki.json")

    print("== data integrity ==")
    for fn, obj in (("decks", decks), ("data_4000", cards4), ("fates", fates)):
        m = obj["meta"]
        check(f"{fn}: season == [9]", m["seasons"] == [9], str(m["seasons"]))
        check(f"{fn}: 24 characters", len(m["charIds"]) == 24, str(len(m["charIds"])))
    hashed = [c for c in decks["cards"] if c["en"].startswith("#")]
    check("decks: no #id names", not hashed, f"{len(hashed)} hashed")
    empty = [c for c in decks["cards"] if not c["sect"]]
    check("decks: no empty sect", not empty, f"{len(empty)} empty")
    talimg = [c for c in fates["talentNames"] if not c.get("img")]
    check("fates: all talents have icon id", not talimg, f"{len(talimg)} missing")

    # ---- win-rate sanity: overall single-card win rate ~ 50% --------------
    print("== win-rate sanity ==")
    G, gs = decks["singles"], decks["meta"]["singleStride"]
    tw = sum(G[i + 5] for i in range(0, len(G), gs))
    tg = sum(G[i + 6] for i in range(0, len(G), gs))
    wr = tw / tg if tg else 0
    # NOT 50%: only beginRankScore>=4000 players are counted as the "owner", and
    # they face many sub-4000 opponents (whose perspective is filtered out), so
    # the owner win rate is biased a few points above 50% by selection.
    check("overall single win rate in 0.50–0.58 (rank-filter bias)", 0.50 <= wr <= 0.58, f"{wr:.4f}")

    # ---- HOME-FIX: per-character cross-sect-locked play fraction ----------
    print("== home-detection fix: characters play only their own sect ==")
    N = len(decks["cards"])
    sect = [c["sect"] for c in decks["cards"]]
    cn = [c["cn"] for c in decks["cards"]]
    charIds = decks["meta"]["charIds"]
    # per char index: games per card
    per = [dict() for _ in charIds]
    for i in range(0, len(G), gs):
        ch, fam, g = G[i + 1], G[i + 4], G[i + 6]
        per[ch][fam] = per[ch].get(fam, 0) + g
    worst = 0.0
    for ci, cid in enumerate(charIds):
        my = LEAD[str(cid)[0]]
        tot = sum(per[ci].values())
        if not tot:
            continue
        cross = sum(g for fam, g in per[ci].items()
                    if sect[fam] in MAIN_SECTS and sect[fam] != my)
        frac = cross / tot
        worst = max(worst, frac)
    check("max cross-sect-locked play fraction < 2%", worst < 0.02, f"worst={worst*100:.2f}%")

    # ---- specific: 陆剑心 (sw) must have ZERO of 姜袭明's 星爆术 ----------
    if 1000005 in charIds:
        ci = charIds.index(1000005)
        star = [i for i, c in enumerate(cn) if c == "星爆术"]
        n = sum(per[ci].get(s, 0) for s in star)
        check("陆剑心 plays 星爆术 == 0", n == 0, f"{n} games")

    # ---- names/sect strictly from wiki -----------------------------------
    print("== wiki authority ==")
    def fam(c):
        return c - ((c // 10000) % 100) * 10000
    bad = []
    for c in decks["cards"]:
        w = wiki["cards"].get(str(fam(c["img"])))
        if w and w.get("sect") and c["sect"] != w["sect"]:
            bad.append((c["cn"], c["sect"], w["sect"]))
    check("every card sect matches wiki.json", not bad,
          f"{len(bad)} mismatch e.g. {bad[:3]}")

    # ---- multi-card combos (combos.json) ---------------------------------
    print("== multi-card combos ==")
    try:
        cb = D("combos.json")
        sizes = list(cb["combos"].keys())
        check("combos: sizes 3-6", sizes == ["3", "4", "5", "6"], str(sizes))
        chashed = [c for c in cb["cards"] if c["en"].startswith("#")]
        cempty = [c for c in cb["cards"] if not c["sect"]]
        check("combos: no #id / empty sect", not chashed and not cempty,
              f"{len(chashed)} #id, {len(cempty)} empty")
        # home-fix: 陆剑心 (sw) never has 七星阁-exclusive 星爆术 in any triple
        cci = cb["meta"]["charIds"].index(1000005)
        cstar = [i for i, c in enumerate(cb["cards"]) if c["cn"] == "星爆术"]
        A, st = cb["combos"]["3"], 3 + 3 + 4
        cbad = sum(1 for i in range(0, len(A), st)
                   if A[i + 1] == cci and any(A[i + 3 + j] in cstar for j in range(3)))
        check("combos: 陆剑心 triples with 星爆术 == 0", cbad == 0, f"{cbad}")
    except Exception as e:
        check("combos.json present", False, str(e))

    # ---- 天衍 (talSlot) ---------------------------------------------------
    print("== 天衍 selection ==")
    slot = fates.get("talSlot", [])
    check("talSlot present", len(slot) > 0, f"{len(slot)//9} rows")
    check("4 slots", fates["meta"].get("slots") == 4, str(fates["meta"].get("slots")))

    print(f"\n{'='*40}\n{len(passes)} passed, {len(fails)} failed")
    if fails:
        print("FAILED:", fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
