#!/usr/bin/env python3
"""Rebuild the single-card page data (data/data_4000.json + data_6000.json) for
the current season 天衍万象 (seasonMec 9), in the original format the existing
app.js expects:

  meta  : {threshold, seasons, careers, charIds, levels, rounds}
  cards : [{i, en, cn, sect, img, lv:{level: id}}]
  facts : flat stride 8 [seasonIdx, charIdx, career, fam(=card index), level, round, wins, losses]

Round-level methodology (a card on the home board that round; winerId == home).
Levels are kept separate (level = (id//10000)%100 + 1). Names cover season-9 new
cards via cardnames.load_resolver.
"""
import os
import time
from collections import defaultdict

import cardnames
from replay_utils import (
    HERE, accumulate, build_archives, build_env, download, fam,
    home_side, is_valid_game, iter_replays, level_of, season_index,
    write_json, AutoIndex,
)

FIRST, LAST, ARCHIVES = build_archives(30210000, 30869000)
VERSION_FILTER, OUT_DIR = build_env()

REF_CARDS = os.path.join(HERE, "data", "data_4000.json")
OUT4 = os.path.join(HERE, OUT_DIR, "data_4000.json")
OUT6 = os.path.join(HERE, OUT_DIR, "data_6000.json")
os.makedirs(os.path.join(HERE, OUT_DIR), exist_ok=True)

SEASONS = [9]
SEASON_IDX = season_index(SEASONS)
MIN_SCORE, HI_SCORE = 4000, 6000

PCHAR, PCAR, PLVL, PRD, PFAM = 32, 8, 8, 32, 1024


def main():
    t0 = time.time()
    fam_idx = AutoIndex()
    char_idx = AutoIndex()
    fam_lv = defaultdict(dict)     # famid -> {level: representative id}
    careers_seen, levels_seen = set(), set()
    facts = defaultdict(lambda: [0, 0, 0, 0])  # key -> [w,g,w6,g6]
    pop4 = pop6 = 0

    for ai, name in enumerate(ARCHIVES):
        for d in iter_replays(download(name)):
            if not is_valid_game(d, SEASON_IDX, VERSION_FILTER, MIN_SCORE):
                continue
            score = d.get("beginRankScore", 0)
            rs = d.get("roundStats") or []
            hi = score >= HI_SCORE
            s = SEASON_IDX[d["seasonMec"]]
            ch = char_idx[d.get("charId")]
            car = d.get("career", 0)
            careers_seen.add(car)
            uid = d.get("uid")        # the file owner; their side alternates p1/p2
            pop4 += 1
            pop6 += 1 if hi else 0
            for rd in rs:
                side = home_side(rd, uid)
                if side is None:
                    continue
                win = 1 if rd.get("winerId") == uid else 0
                rn = rd.get("round", 0)
                for c in rd[side]["privateData"].get("usedCards") or []:
                    if not c:
                        continue
                    f = fam(c)
                    lv = level_of(c)
                    fam_lv[f].setdefault(lv, c)
                    levels_seen.add(lv)
                    fi = fam_idx[f]
                    key = (((((s * PCHAR + ch) * PCAR + car) * PLVL + lv) * PRD + rn) * PFAM + fi)
                    accumulate(facts[key], win, hi)
        print(f"[{ai+1}/{len(ARCHIVES)}] {name}: pop={pop4} facts={len(facts)} "
              f"({time.time()-t0:.0f}s)", flush=True)

    # threshold to keep output lean
    def pick(cap):
        for thr in (1, 2, 3, 5, 8, 10):
            n = sum(1 for v in facts.values() if v[1] >= thr)
            if n <= cap:
                return thr
        return 10
    min_g = pick(800_000)
    print(f"min games per fact row: {min_g}", flush=True)

    resolve = cardnames.load_resolver(REF_CARDS)
    inv_fam = fam_idx.inverted()
    # keep only families with a surviving row
    keep = set()
    for k, v in facts.items():
        if v[1] >= min_g:
            keep.add(k % PFAM)
    fam_order = sorted(keep, key=lambda i: inv_fam[i])
    old_to_new = {old: new for new, old in enumerate(fam_order)}

    cards = []
    for new_i, old_i in enumerate(fam_order):
        fid = inv_fam[old_i]
        meta = resolve(fid)
        lv = {str(l): cid for l, cid in sorted(fam_lv[fid].items())}
        cards.append({"i": new_i, "en": meta["en"], "cn": meta["cn"],
                      "sect": meta["sect"], "img": meta["img"], "lv": lv})

    char_ids = char_idx.ordered_keys()

    def unpack(k):
        fi = k % PFAM
        b = k // PFAM
        rd = b % PRD
        b //= PRD
        lv = b % PLVL
        b //= PLVL
        car = b % PCAR
        b //= PCAR
        ch = b % PCHAR
        s = b // PCHAR
        return s, ch, car, lv, rd, fi

    def emit(hi):
        wcol, gcol = (2, 3) if hi else (0, 1)
        arr = []
        for k, v in facts.items():
            if v[1] < min_g:
                continue
            g = v[gcol]
            if hi and g == 0:
                continue
            fi = old_to_new.get(k % PFAM)
            if fi is None:
                continue
            s, ch, car, lv, rd, _ = unpack(k)
            w = v[wcol]
            arr += [s, ch, car, fi, lv, rd, w, g - w]
        return arr

    for thr, out_path, hi, pop in ((4000, OUT4, False, pop4), (6000, OUT6, True, pop6)):
        obj = {
            "meta": {
                "threshold": thr,
                "seasons": SEASONS,
                "careers": sorted(careers_seen),
                "charIds": char_ids,
                "levels": sorted(levels_seen),
                "rounds": [1, 27],
                "population": pop,
            },
            "cards": cards,
            "facts": emit(hi),
        }
        sz = write_json(out_path, obj) / 1e6
        print(f"wrote {out_path}: {sz:.1f}MB facts={len(obj['facts'])//8} "
              f"cards={len(cards)} pop={pop} ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
