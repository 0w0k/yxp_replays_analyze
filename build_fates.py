#!/usr/bin/env python3
"""Build talent (天赋) + dao-yun (道韵) aggregates -> data/fates.json.

Note: the real 仙命 / fateBranch system is NOT recorded in this dataset
(seasons 7, version 001.0005 -> fateBranchData is empty in 100% of games), so
this analyses the talent draft instead. The community card-counter calls the
talent draft "fate", which is what users mean by 仙命 here.

There is also no game-level outcome (`data.win` is always False, `battleRank`
is a uniform seat index), so every win rate is round-level, exactly like the
card / combo pages: a talent/daoyun "held" a round counts that round's
winerId == homePlayerId as a win.

Two metrics per system:
  * held  -> round-level: rounds won while holding it / rounds held
             keyed (season, char, career, round, id)  [w,g,w6,g6]
  * draft -> selection events (talentSelectionDatas / daoYunSelectionDatas):
             how often it was offered (in pendings) vs picked (selected)
             keyed (season, char, career, id)  [offered,picked,off6,pick6]
"""
import io
import json
import os
import tarfile
import time
import urllib.request
from collections import defaultdict

import zstandard

BASE_URL = "https://huggingface.co/datasets/sharpobject/yxp_replays/resolve/main"
# Season 9 = 天衍万象 (current). Local clone archives in this range are seasonMec 9.
FIRST, LAST, STEP = 30210000, 30869000, 1000
# Optional per-version build overrides (defaults keep the original behaviour).
FIRST = int(os.environ.get("BUILD_FIRST", FIRST))
LAST = int(os.environ.get("BUILD_LAST", LAST))
VERSION_FILTER = os.environ.get("VERSION_FILTER") or None
OUT_DIR = os.environ.get("OUT_DIR") or "data"
ARCHIVES = [f"{n}" for n in range(FIRST, LAST + 1, STEP)]

HERE = os.path.dirname(os.path.abspath(__file__))
REPLAYS = os.environ.get("REPLAYS_DIR") or os.path.join(HERE, "replays")
CACHE = os.environ.get("DECK_CACHE") or os.path.join(
    os.environ.get("CLAUDE_JOB_DIR", HERE), "tmp")
OUT = os.path.join(HERE, OUT_DIR, "fates.json")
REF_CARDS = os.path.join(HERE, "data", "data_4000.json")
# talent name maps from the sibling card-counter project (en + cn)
COUNTER = os.environ.get("COUNTER_DIR") or os.path.join(HERE, "..", "yixian-card-counter-with-proxy")
FATE_TALENT_MAP = os.path.join(COUNTER, "proxy", "fate_talent_map.json")
FATE_ID_MAP = os.path.join(COUNTER, "proxy", "fate_id_map.json")

SEASONS = [9]            # 天衍万象 only
SEASON_IDX = {s: i for i, s in enumerate(SEASONS)}
MIN_SCORE = 4000
HI_SCORE = 6000


def fam(cid):
    return cid - ((cid // 10000) % 100) * 10000


def tbase(tid):
    """Talent family: strip the +10000-per-level offset."""
    return tid % 10000


def download(name):
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
        if not m.name.endswith(".json"):
            continue
        try:
            yield json.load(tf.extractfile(m))["data"]
        except Exception:
            continue


def home_side(rd, uid):
    # the file owner's side alternates p1/p2; homePlayerId is the battle's first
    # player and is the opponent ~2/3 of the time, so match the owner's uid.
    if rd["p2"]["publicData"]["uid"] == uid:
        return "p2"
    if rd["p1"]["publicData"]["uid"] == uid:
        return "p1"
    return None


def main():
    t0 = time.time()
    char_idx = {}
    careers_seen = set()
    tal_held = defaultdict(lambda: [0, 0, 0, 0])   # (s,ch,car,rd,tal)->[w,g,w6,g6]
    tal_draft = defaultdict(lambda: [0, 0, 0, 0])  # (s,ch,car,tal)->[off,pick,off6,pick6]
    tal_slot = defaultdict(lambda: [0, 0, 0, 0])   # 天衍 (s,ch,car,slot,tal)->[off,pick,off6,pick6]
    dy_held = defaultdict(lambda: [0, 0, 0, 0])
    dy_draft = defaultdict(lambda: [0, 0, 0, 0])
    pop4 = pop6 = 0

    def cidx(c):
        i = char_idx.get(c)
        if i is None:
            i = char_idx[c] = len(char_idx)
        return i

    for ai, name in enumerate(ARCHIVES):
        path = download(name)
        for d in iter_replays(path):
            if d.get("seasonMec") not in SEASON_IDX:
                continue
            if VERSION_FILTER and d.get("version") != VERSION_FILTER:
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

            last_priv = None
            for rd in rs:
                side = home_side(rd, uid)
                if side is None:
                    continue
                pub = rd[side]["publicData"]
                priv = rd[side]["privateData"]
                last_priv = priv
                win = 1 if rd.get("winerId") == uid else 0
                rn = rd.get("round", 0)
                # held talents this round
                for t in {tbase(x) for x in (pub.get("talents") or []) if x}:
                    v = tal_held[(s, ch, car, rn, t)]
                    v[0] += win
                    v[1] += 1
                    if hi:
                        v[2] += win
                        v[3] += 1
                # held dao-yun this round (single value, set once chosen)
                dy = priv.get("daoYun")
                if dy:
                    v = dy_held[(s, ch, car, rn, dy)]
                    v[0] += win
                    v[1] += 1
                    if hi:
                        v[2] += win
                        v[3] += 1

            # draft: selection lists are cumulative -> use the final round's.
            # talentSelectionDatas = 天衍选择: 4-pick at slots id 2..5 (rounds ~3/6/9/11).
            if last_priv is not None:
                for ev in (last_priv.get("talentSelectionDatas") or []):
                    slot = (ev.get("id") or 0) - 2   # id 2..5 -> slot 0..3
                    bases = {tbase(o) for o in ev.get("pendings", []) if o}
                    sel = tbase(ev.get("selected") or 0)
                    for b in bases:
                        v = tal_draft[(s, ch, car, b)]
                        v[0] += 1
                        if b == sel:
                            v[1] += 1
                        if hi:
                            v[2] += 1
                            if b == sel:
                                v[3] += 1
                        if slot >= 0:           # 天衍 per-slot offered/picked
                            v2 = tal_slot[(s, ch, car, slot, b)]
                            v2[0] += 1
                            if b == sel:
                                v2[1] += 1
                            if hi:
                                v2[2] += 1
                                if b == sel:
                                    v2[3] += 1
                for ev in (last_priv.get("daoYunSelectionDatas") or []):
                    opts = {o for o in ev.get("pendings", []) if o}
                    sel = ev.get("selected") or 0
                    for o in opts:
                        v = dy_draft[(s, ch, car, o)]
                        v[0] += 1
                        if o == sel:
                            v[1] += 1
                        if hi:
                            v[2] += 1
                            if o == sel:
                                v[3] += 1
        print(f"[{ai+1}/{len(ARCHIVES)}] {name}: pop={pop4} "
              f"talHeld={len(tal_held)} dyHeld={len(dy_held)} "
              f"({time.time()-t0:.0f}s)", flush=True)

    # ---- names -------------------------------------------------------------
    talent_en, talent_cn = {}, {}
    try:
        ftm = json.load(open(FATE_TALENT_MAP, encoding="utf-8"))
        for k, v in ftm.items():
            talent_en[int(k)] = v.get("name")
            talent_cn[int(k)] = v.get("nameCn")
    except Exception as e:
        print("warn: no fate_talent_map", e)
    try:
        fid = json.load(open(FATE_ID_MAP, encoding="utf-8"))
        for k, v in fid.items():
            talent_cn.setdefault(int(k), v)
    except Exception as e:
        print("warn: no fate_id_map", e)

    import cardnames
    resolve = cardnames.load_resolver(REF_CARDS)

    def talent_name(b):
        return {"en": talent_en.get(b) or f"#{b}", "cn": talent_cn.get(b) or ""}

    def daoyun_name(idv):
        m = resolve(fam(idv))
        return {"en": m["en"], "cn": m["cn"], "img": m["img"]}

    # ---- compact indexing per system --------------------------------------
    tal_ids = sorted(set([k[4] for k in tal_held] + [k[3] for k in tal_draft]))
    dy_ids = sorted(set([k[4] for k in dy_held] + [k[3] for k in dy_draft]))
    tal_pos = {t: i for i, t in enumerate(tal_ids)}
    dy_pos = {t: i for i, t in enumerate(dy_ids)}

    inv_char = {i: c for c, i in char_idx.items()}
    char_ids = [inv_char[i] for i in sorted(inv_char)]

    def emit_held(dd, pos):
        out = []
        for (s, ch, car, rn, idv), v in dd.items():
            if v[1] < MIN_HELD:
                continue
            out += [s, ch, car, rn, pos[idv], v[0], v[1], v[2], v[3]]
        return out

    def emit_draft(dd, pos):
        out = []
        for (s, ch, car, idv), v in dd.items():
            if v[0] < MIN_DRAFT:
                continue
            out += [s, ch, car, pos[idv], v[0], v[1], v[2], v[3]]
        return out

    def emit_slot(dd, pos):
        out = []
        for (s, ch, car, slot, idv), v in dd.items():
            if v[0] < MIN_DRAFT or idv not in pos:
                continue
            out += [s, ch, car, slot, pos[idv], v[0], v[1], v[2], v[3]]
        return out

    out = {
        "meta": {
            "seasons": SEASONS,
            "careers": sorted(careers_seen),
            "charIds": char_ids,
            "rounds": [1, 27],
            "minHeld": MIN_HELD,
            "minDraft": MIN_DRAFT,
            "population": {"t4000": pop4, "t6000": pop6},
            "archives": len(ARCHIVES),
            "heldStride": 9,    # s,ch,car,rd, id, w,g, w6,g6
            "draftStride": 8,   # s,ch,car, id, offered,picked, off6,pick6
            "slotStride": 9,    # s,ch,car,slot, id, offered,picked, off6,pick6 (天衍选择)
            "slots": 4,         # 天衍选择 4 次 (slot 0..3, id 2..5)
            "note": "round-level win rate; 仙命/fateBranch absent in data, this is the talent draft",
        },
        "talentNames": [talent_name(t) for t in tal_ids],
        "daoyunNames": [daoyun_name(t) for t in dy_ids],
        "talHeld": emit_held(tal_held, tal_pos),
        "talDraft": emit_draft(tal_draft, tal_pos),
        "talSlot": emit_slot(tal_slot, tal_pos),
        "dyHeld": emit_held(dy_held, dy_pos),
        "dyDraft": emit_draft(dy_draft, dy_pos),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    sz = os.path.getsize(OUT) / 1e6
    print(f"wrote {OUT}: {sz:.1f}MB  talents={len(tal_ids)} daoyun={len(dy_ids)} "
          f"talHeld={len(out['talHeld'])//9} talDraft={len(out['talDraft'])//8} "
          f"dyHeld={len(out['dyHeld'])//9} dyDraft={len(out['dyDraft'])//8} "
          f"pop4={pop4} pop6={pop6} ({time.time()-t0:.0f}s)", flush=True)


MIN_HELD, MIN_DRAFT = 8, 8
if __name__ == "__main__":
    main()
