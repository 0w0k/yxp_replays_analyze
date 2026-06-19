#!/usr/bin/env python3
"""Build multi-card combo aggregates (data/combos.json) for sizes 2..6.

Exact 7-8 card boards almost never repeat, so we stop at 6. Larger combos are
mined with Apriori (a k-combo is only kept if it appears >= the per-size global
support AND all its (k-1)-subsets are frequent), which keeps memory/output
bounded while preserving the full season/char/career/round dimensions.

Methodology matches the pair page: round-level, the file owner's board that
round (match d.uid — NOT homePlayerId), win = winerId == d.uid.

Output (one flat int array per size, like the pair page):
  combos["k"] stride = 4 + k + 4 : [season,char,career,round, fam1..famk, w,g,w6,g6]
  plus singles (lift baseline) and the card list.
"""
import io
import json
import os
import tarfile
import time
from collections import defaultdict, Counter
from itertools import combinations

import zstandard

import cardnames

FIRST, LAST, STEP = 30210000, 30747000, 1000
ARCHIVES = [f"{n}" for n in range(FIRST, LAST + 1, STEP)]
HERE = os.path.dirname(os.path.abspath(__file__))
REPLAYS = os.environ.get("REPLAYS_DIR") or r"D:\Coding\yxp_replays_analyze\replays"
OUT = os.path.join(HERE, "data", "combos.json")
REF_CARDS = os.path.join(HERE, "data", "data_4000.json")

SEASONS = [9]
SEASON_IDX = {s: i for i, s in enumerate(SEASONS)}
MIN_SCORE, HI_SCORE = 4000, 6000
MIN_K, MAX_K = 3, 6
# per-size global support to keep (tuned for the full season)
MIN_SUP = {2: 30, 3: 150, 4: 120, 5: 90, 6: 60}  # global support (full season)
# don't ship dim-rows below this many games (keeps the file lean)
MIN_ROW = {2: 6, 3: 4, 4: 3, 5: 3, 6: 3}
FREQ_CAP = 45000  # auto-raise support if a size exceeds this many frequent combos
PCHAR, PCAR = 32, 8  # dims: season, char, career (NO round for 3+ card combos)


def fam(c):
    return c - ((c // 10000) % 100) * 10000


def src(name):
    local = os.path.join(REPLAYS, name + ".tar.zst")
    if os.path.exists(local):
        return local
    return None


def iter_replays(path):
    with open(path, "rb") as f:
        raw = zstandard.ZstdDecompressor().stream_reader(f).read()
    tf = tarfile.open(fileobj=io.BytesIO(raw))
    for m in tf.getmembers():
        if m.name.endswith(".json"):
            try:
                yield json.load(tf.extractfile(m))["data"]
            except Exception:
                continue


def main():
    t0 = time.time()
    fam_idx, char_idx = {}, {}
    careers_seen = set()

    def fidx(f):
        i = fam_idx.get(f)
        if i is None:
            i = fam_idx[f] = len(fam_idx)
        return i

    def cidx(c):
        i = char_idx.get(c)
        if i is None:
            i = char_idx[c] = len(char_idx)
        return i

    # ---- 1. load every round-board into memory --------------------------
    # board = (dimkey, win, hi, fams_tuple)  ; dimkey packs (s,ch,car,rd)
    boards = []
    singles = defaultdict(lambda: [0, 0, 0, 0])
    pop4 = pop6 = 0
    for ai, name in enumerate(ARCHIVES):
        path = src(name)
        if not path:
            continue
        for d in iter_replays(path):
            if d.get("seasonMec") not in SEASON_IDX:
                continue
            score = d.get("beginRankScore", 0)
            if score < MIN_SCORE:
                continue
            rs = d.get("roundStats") or []
            if not rs:
                continue
            hi = 1 if score >= HI_SCORE else 0
            s = SEASON_IDX[d["seasonMec"]]
            ch = cidx(d.get("charId"))
            car = d.get("career", 0)
            careers_seen.add(car)
            uid = d.get("uid")
            pop4 += 1
            pop6 += hi
            for rd in rs:
                side = "p2" if rd["p2"]["publicData"]["uid"] == uid else (
                    "p1" if rd["p1"]["publicData"]["uid"] == uid else None)
                if side is None:
                    continue
                used = rd[side]["privateData"].get("usedCards") or []
                fs = sorted({fidx(fam(c)) for c in used if c})
                if not fs:
                    continue
                win = 1 if rd.get("winerId") == uid else 0
                rn = rd.get("round", 0)
                dim = (s * PCHAR + ch) * PCAR + car
                for a in fs:
                    v = singles[(dim, a)]
                    v[0] += win
                    v[1] += 1
                    if hi:
                        v[2] += win
                        v[3] += 1
                if len(fs) >= 2:
                    boards.append((dim, win, hi, tuple(fs)))
        print(f"[{ai+1}/{len(ARCHIVES)}] {name}: boards={len(boards)} "
              f"pop={pop4} ({time.time()-t0:.0f}s)", flush=True)

    print(f"loaded {len(boards)} boards, {len(fam_idx)} families "
          f"({time.time()-t0:.0f}s)", flush=True)

    # ---- 2. Apriori: frequent itemsets sizes 2..MAX_K -------------------
    out_combos = {}
    # need frequent pairs as the seed for size-3 pruning (not emitted here; size-2
    # stays in decks.json). Mine pairs first, then 3..MAX_K.
    gp = Counter()
    for (dim, win, hi, fs) in boards:
        for combo in combinations(fs, 2):
            gp[combo] += 1
    prev_freq = {c for c, n in gp.items() if n >= MIN_SUP[2]}
    print(f"  seed frequent pairs(>= {MIN_SUP[2]})={len(prev_freq)} ({time.time()-t0:.0f}s)", flush=True)
    del gp
    for k in range(MIN_K, MAX_K + 1):
        gcnt = Counter()
        for (dim, win, hi, fs) in boards:
            if len(fs) < k:
                continue
            if k == 2:
                for combo in combinations(fs, 2):
                    gcnt[combo] += 1
            else:
                for combo in combinations(fs, k):
                    ok = True
                    for sub in combinations(combo, k - 1):
                        if sub not in prev_freq:
                            ok = False
                            break
                    if ok:
                        gcnt[combo] += 1
        sup = MIN_SUP[k]
        freq = {c for c, n in gcnt.items() if n >= sup}
        while len(freq) > FREQ_CAP:
            sup = int(sup * 1.5)
            freq = {c for c, n in gcnt.items() if n >= sup}
        print(f"  size {k}: candidates={len(gcnt)} frequent(>= {sup})={len(freq)} "
              f"({time.time()-t0:.0f}s)", flush=True)
        prev_freq = freq
        # 3. full-dim aggregation for frequent combos of this size
        dimc = defaultdict(lambda: [0, 0, 0, 0])
        for (dim, win, hi, fs) in boards:
            if len(fs) < k:
                continue
            for combo in combinations(fs, k):
                if combo in freq:
                    v = dimc[(dim, combo)]
                    v[0] += win
                    v[1] += 1
                    if hi:
                        v[2] += win
                        v[3] += 1
        out_combos[k] = dimc
        del gcnt

    # ---- 4. reindex surviving families, emit ----------------------------
    keep = set()
    for k, dimc in out_combos.items():
        for (dim, combo), v in dimc.items():
            if v[1] >= MIN_ROW[k]:
                keep.update(combo)
    # also keep families referenced by emitted singles
    sing_rows = {}
    for (dim, a), v in singles.items():
        if v[1] >= 5:
            sing_rows[(dim, a)] = v
            keep.add(a)

    inv_fam = {i: f for f, i in fam_idx.items()}
    fam_order = sorted(keep, key=lambda i: inv_fam[i])
    old_to_new = {old: i for i, old in enumerate(fam_order)}

    resolve = cardnames.load_resolver(REF_CARDS)
    cards = []
    for old in fam_order:
        m = resolve(inv_fam[old])
        cards.append({"i": len(cards), "en": m["en"], "cn": m["cn"],
                      "sect": m["sect"], "img": m["img"]})

    inv_char = {i: c for c, i in char_idx.items()}
    char_ids = [inv_char[i] for i in sorted(inv_char)]

    def unpack(dim):
        car = dim % PCAR
        b = dim // PCAR
        ch = b % PCHAR
        s = b // PCHAR
        return s, ch, car

    combos_arr = {}
    for k, dimc in out_combos.items():
        arr = []
        for (dim, combo), v in dimc.items():
            if v[1] < MIN_ROW[k]:
                continue
            if any(c not in old_to_new for c in combo):
                continue
            s, ch, car = unpack(dim)
            arr.extend([s, ch, car])
            arr.extend(sorted(old_to_new[c] for c in combo))
            arr.extend([v[0], v[1], v[2], v[3]])
        combos_arr[str(k)] = arr

    sing_arr = []
    for (dim, a), v in sing_rows.items():
        if a not in old_to_new:
            continue
        s, ch, car = unpack(dim)
        sing_arr.extend([s, ch, car, old_to_new[a], v[0], v[1], v[2], v[3]])

    out = {
        "meta": {
            "seasons": SEASONS, "careers": sorted(careers_seen), "charIds": char_ids,
            "rounds": [1, 27], "sizes": list(range(2, MAX_K + 1)),
            "minSup": MIN_SUP, "minRow": MIN_ROW,
            "population": {"t4000": pop4, "t6000": pop6},
            "singleStride": 9,  # s,ch,car,rd, fam, w,g,w6,g6
        },
        "cards": cards,
        "singles": sing_arr,
        "combos": combos_arr,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    sz = os.path.getsize(OUT) / 1e6
    counts = {k: len(v) // (3 + int(k) + 4) for k, v in combos_arr.items()}
    print(f"wrote {OUT}: {sz:.1f}MB cards={len(cards)} rows-per-size={counts} "
          f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
