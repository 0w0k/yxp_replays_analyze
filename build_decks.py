#!/usr/bin/env python3
"""Build deck-combo aggregates (data/decks.json) from the sharpobject/yxp_replays
HuggingFace dataset.

Round-level methodology, matching the single-card explorer:
  - population = ranked ladder games of seasons 7/8 with beginRankScore >= 4000
  - for each round, the home player's board (usedCards, levels merged to "families")
    is a set of card-families; that round is a win iff winerId == homePlayerId
  - we aggregate, per (season, character, career, round):
       * singles[fam]      -> wins / games
       * pairs[famA,famB]  -> wins / games   (every unordered pair on the board)
  - two tiers are kept inline per row: total (>=4000) and the >=6000 subset.

Output (data/decks.json) is a compact flat-int-array format the browser sums on
the fly (see deck.js). Triples (3-card combos) are intentionally deferred to v2.
"""
import os
import time
from collections import defaultdict
from itertools import combinations

import cardnames
from replay_utils import (
    HERE, accumulate, build_archives, build_env, download, fam,
    home_side, is_valid_game, iter_replays, season_index,
    write_json, AutoIndex,
)

FIRST, LAST, ARCHIVES = build_archives(30210000, 30869000)
VERSION_FILTER, OUT_DIR = build_env()

OUT = os.path.join(HERE, OUT_DIR, "decks.json")
REF_CARDS = os.path.join(HERE, "data", "data_4000.json")

SEASONS = [9]             # 天衍万象 only; index = position here
SEASON_IDX = season_index(SEASONS)
MIN_SCORE_4000 = 4000
MIN_SCORE_6000 = 6000

# packing: key = ((((s*32 + char)*8 + car)*32 + rd)*512 + a)*512 + b
PCHAR, PCAR, PRD, PFAM = 32, 8, 32, 512


def main():
    t0 = time.time()
    fam_idx = AutoIndex()
    char_idx = AutoIndex()
    careers_seen = set()
    # value = [w, g, w6, g6]
    singles = defaultdict(lambda: [0, 0, 0, 0])
    pairs = defaultdict(lambda: [0, 0, 0, 0])
    pop4 = pop6 = 0
    rounds_seen = 0

    for ai, name in enumerate(ARCHIVES):
        path = download(name)
        for d in iter_replays(path):
            if not is_valid_game(d, SEASON_IDX, VERSION_FILTER, MIN_SCORE_4000):
                continue
            score = d.get("beginRankScore", 0)
            rs = d.get("roundStats") or []
            hi = score >= MIN_SCORE_6000
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
                used = rd[side]["privateData"].get("usedCards") or []
                fs = sorted({fam(c) for c in used if c})
                if not fs:
                    continue
                win = 1 if rd.get("winerId") == uid else 0
                rn = rd.get("round", 0)
                rounds_seen += 1
                ids = [fam_idx[f] for f in fs]
                base = ((s * PCHAR + ch) * PCAR + car) * PRD + rn
                for a in ids:
                    v = singles[base * PFAM + a]
                    accumulate(v, win, hi)
                for a, b in combinations(ids, 2):
                    v = pairs[(base * PFAM + a) * PFAM + b]
                    accumulate(v, win, hi)
        print(f"[{ai+1}/{len(ARCHIVES)}] {name}: pop={pop4} "
              f"pairKeys={len(pairs)} singleKeys={len(singles)} "
              f"({time.time()-t0:.0f}s)", flush=True)

    # ---- pick thresholds so the shipped arrays stay lean -------------------
    def pick(counts, candidates, cap):
        for thr in candidates:
            n = sum(1 for v in counts.values() if v[1] >= thr)
            if n <= cap:
                return thr, n
        return candidates[-1], sum(1 for v in counts.values()
                                   if v[1] >= candidates[-1])

    min_single, n_single = pick(singles, [5, 8, 10, 15, 20], 90_000)
    min_pair, n_pair = pick(pairs, [8, 10, 12, 15, 20, 30, 50], 200_000)
    print(f"thresholds: single>={min_single} ({n_single} rows) "
          f"pair>={min_pair} ({n_pair} rows)", flush=True)

    # ---- reindex families to only those that survive -----------------------
    keep_fam = set()
    for k, v in singles.items():
        if v[1] >= min_single:
            keep_fam.add(k % PFAM)
    for k, v in pairs.items():
        if v[1] >= min_pair:
            keep_fam.add(k % PFAM)
            keep_fam.add((k // PFAM) % PFAM)

    inv_fam = fam_idx.inverted()
    old_to_new = {}
    fam_order = sorted(keep_fam, key=lambda i: inv_fam[i])
    for new_i, old_i in enumerate(fam_order):
        old_to_new[old_i] = new_i

    resolve = cardnames.load_resolver(REF_CARDS)
    cards = []
    for new_i, old_i in enumerate(fam_order):
        m = resolve(inv_fam[old_i])
        cards.append({"i": new_i, "en": m["en"], "cn": m["cn"],
                      "sect": m["sect"], "img": m["img"]})

    char_ids = char_idx.ordered_keys()

    # ---- emit flat arrays --------------------------------------------------
    def unpack(k):
        b = k // PFAM
        rd = b % PRD
        b //= PRD
        car = b % PCAR
        b //= PCAR
        ch = b % PCHAR
        s = b // PCHAR
        return s, ch, car, rd

    sing_arr = []
    for k, v in singles.items():
        if v[1] < min_single:
            continue
        fa = old_to_new.get(k % PFAM)
        if fa is None:
            continue
        s, ch, car, rd = unpack(k)
        sing_arr += [s, ch, car, rd, fa, v[0], v[1], v[2], v[3]]

    pair_arr = []
    for k, v in pairs.items():
        if v[1] < min_pair:
            continue
        fb = old_to_new.get(k % PFAM)
        fa = old_to_new.get((k // PFAM) % PFAM)
        if fa is None or fb is None:
            continue
        s, ch, car, rd = unpack(k // PFAM)
        pair_arr += [s, ch, car, rd, fa, fb, v[0], v[1], v[2], v[3]]

    out = {
        "meta": {
            "seasons": SEASONS,
            "careers": sorted(careers_seen),
            "charIds": char_ids,
            "rounds": [1, 27],
            "minSingleGames": min_single,
            "minPairGames": min_pair,
            "population": {"t4000": pop4, "t6000": pop6},
            "roundsSeen": rounds_seen,
            "archives": len(ARCHIVES),
            "singleStride": 9,   # s,ch,car,rd, fam, w,g, w6,g6
            "pairStride": 10,    # s,ch,car,rd, a,b, w,g, w6,g6
        },
        "cards": cards,
        "singles": sing_arr,
        "pairs": pair_arr,
    }
    sz = write_json(OUT, out) / 1e6
    print(f"wrote {OUT}: {sz:.1f}MB  cards={len(cards)} "
          f"singles={len(sing_arr)//9} pairs={len(pair_arr)//10}  "
          f"pop4={pop4} pop6={pop6}  ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
