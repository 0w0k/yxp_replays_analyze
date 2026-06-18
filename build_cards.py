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
import io
import json
import os
import tarfile
import time
import urllib.request
from collections import defaultdict

import zstandard

import cardnames

BASE_URL = "https://huggingface.co/datasets/sharpobject/yxp_replays/resolve/main"
FIRST, LAST, STEP = 30210000, 30747000, 1000
ARCHIVES = [f"{n}" for n in range(FIRST, LAST + 1, STEP)]

HERE = os.path.dirname(os.path.abspath(__file__))
REPLAYS = os.environ.get("REPLAYS_DIR") or r"D:\Coding\yxp_replays_analyze\replays"
CACHE = os.environ.get("DECK_CACHE") or os.path.join(
    os.environ.get("CLAUDE_JOB_DIR", HERE), "tmp")
REF_CARDS = os.path.join(HERE, "data", "data_4000.json")
OUT4 = os.path.join(HERE, "data", "data_4000.json")
OUT6 = os.path.join(HERE, "data", "data_6000.json")

SEASONS = [9]
SEASON_IDX = {s: i for i, s in enumerate(SEASONS)}
MIN_SCORE, HI_SCORE = 4000, 6000

PCHAR, PCAR, PLVL, PRD, PFAM = 32, 8, 8, 32, 1024


def fam(c):
    return c - ((c // 10000) % 100) * 10000


def level_of(c):
    return (c // 10000) % 100 + 1


def src(name):
    local = os.path.join(REPLAYS, name + ".tar.zst")
    if os.path.exists(local) and os.path.getsize(local) > 1_000_000:
        return local
    dst = os.path.join(CACHE, name + ".tar.zst")
    if os.path.exists(dst) and os.path.getsize(dst) > 1_000_000:
        return dst
    os.makedirs(CACHE, exist_ok=True)
    tmp = dst + ".part"
    urllib.request.urlretrieve(f"{BASE_URL}/{name}.tar.zst", tmp)
    os.replace(tmp, dst)
    return dst


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
    fam_lv = defaultdict(dict)     # famid -> {level: representative id}
    careers_seen, levels_seen = set(), set()
    facts = defaultdict(lambda: [0, 0, 0, 0])  # key -> [w,g,w6,g6]
    pop4 = pop6 = 0

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

    for ai, name in enumerate(ARCHIVES):
        for d in iter_replays(src(name)):
            if d.get("seasonMec") not in SEASON_IDX:
                continue
            score = d.get("beginRankScore", 0)
            if score < MIN_SCORE:
                continue
            rs = d.get("roundStats") or []
            if not rs:
                continue
            hi = score >= HI_SCORE
            s = SEASON_IDX[d["seasonMec"]]
            ch = cidx(d.get("charId"))
            car = d.get("career", 0)
            careers_seen.add(car)
            uid = d.get("uid")        # the file owner; their side alternates p1/p2
            pop4 += 1
            pop6 += 1 if hi else 0
            for rd in rs:
                # homePlayerId is the battle's first player (opponent ~2/3 of the
                # time); match the file owner's uid to read THEIR board.
                side = "p2" if rd["p2"]["publicData"]["uid"] == uid else (
                    "p1" if rd["p1"]["publicData"]["uid"] == uid else None)
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
                    fi = fidx(f)
                    key = (((((s * PCHAR + ch) * PCAR + car) * PLVL + lv) * PRD + rn) * PFAM + fi)
                    v = facts[key]
                    v[0] += win
                    v[1] += 1
                    if hi:
                        v[2] += win
                        v[3] += 1
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
    inv_fam = {i: f for f, i in fam_idx.items()}
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

    inv_char = {i: c for c, i in char_idx.items()}
    char_ids = [inv_char[i] for i in sorted(inv_char)]

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
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        sz = os.path.getsize(out_path) / 1e6
        print(f"wrote {out_path}: {sz:.1f}MB facts={len(obj['facts'])//8} "
              f"cards={len(cards)} pop={pop} ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
