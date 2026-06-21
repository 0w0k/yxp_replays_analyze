#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""天衍万象仙命(天衍)聚合 -> data/tianyan.json.

天衍 = replay 的 privateData.fateStrategyData.strategies（4 选 1，strategy id
3/6/9 = 第 1/2/3 次突破）。天衍 ID 直接对应 data/fates_wiki.json 的 byId
(由 build_tianyan_wiki.py 从 wiki 生成)。

口径与 cards/fates/decks 页面一致：seasonMec==9（天衍万象本赛季），段位分
beginRankScore>=4000（6000 为高分档），回合级胜率（winerId==uid 记为该回合胜）。

两个指标：
  * draft (选择率) -> 每个触发点 slot(id 3/6/9)每个天衍 offered/picked
       keyed (season, char, career, slot, fateId) -> [off, pick, off6, pick6]
  * held (持有胜率) -> 每回合 lastRoundData.fateStrategies 里持有的天衍
       keyed (season, char, career, round, fateId) -> [w, g, w6, g6]
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
# 天衍(fateStrategyData)随客户端 version 001.0007.0002 才上线：30210000~3052xxxx
# (ver 0000/0001) 完全没有该字段，只有 ~30530000 起(ver 0002/0003)才有数据。
# 起点设 30520000 保证不漏(前 1~2 个空包成本极小)。
FIRST, LAST, STEP = 30520000, 30869000, 1000          # 含天衍数据的 season-9 包范围
ARCHIVES = [f"{n}" for n in range(FIRST, LAST + 1, STEP)]

HERE = os.path.dirname(os.path.abspath(__file__))
REPLAYS = os.environ.get("REPLAYS_DIR") or r"D:\Coding\yxp_replays_analyze\replays"
CACHE = os.environ.get("DECK_CACHE") or os.path.join(
    os.environ.get("CLAUDE_JOB_DIR", HERE), "tmp")
OUT = os.path.join(HERE, "data", "tianyan.json")

SEASONS = [9]
SEASON_IDX = {s: i for i, s in enumerate(SEASONS)}
MIN_SCORE, HI_SCORE = 4000, 6000
SLOT_OF = {3: 0, 6: 1, 9: 2}          # strategy id -> 第几次突破
MIN_HELD, MIN_DRAFT = 8, 8


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
    if rd["p2"]["publicData"]["uid"] == uid:
        return "p2"
    if rd["p1"]["publicData"]["uid"] == uid:
        return "p1"
    return None


def main():
    t0 = time.time()
    char_idx = {}
    careers_seen = set()
    draft = defaultdict(lambda: [0, 0, 0, 0])   # (s,ch,car,slot,fid)->[off,pick,off6,pick6]
    held = defaultdict(lambda: [0, 0, 0, 0])    # (s,ch,car,rd,fid)->[w,g,w6,g6]
    pop4 = pop6 = 0

    def cidx(c):
        i = char_idx.get(c)
        if i is None:
            i = char_idx[c] = len(char_idx)
        return i

    for ai, name in enumerate(ARCHIVES):
        try:
            path = download(name)
        except Exception as e:
            print(f"[{ai+1}/{len(ARCHIVES)}] {name}: skip ({e})", flush=True)
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
            hi = score >= HI_SCORE
            s = SEASON_IDX[d["seasonMec"]]
            ch = cidx(d.get("charId"))
            car = d.get("career", 0)
            careers_seen.add(car)
            uid = d.get("uid")
            pop4 += 1
            pop6 += 1 if hi else 0

            last_priv = None
            for rd in rs:
                side = home_side(rd, uid)
                if side is None:
                    continue
                pub = rd[side]["publicData"]
                last_priv = rd[side]["privateData"]
                win = 1 if rd.get("winerId") == uid else 0
                rn = rd.get("round", 0)
                # held: 截至该回合持有的天衍天衍
                lrd = pub.get("lastRoundData") or {}
                for fid in {x for x in (lrd.get("fateStrategies") or []) if x}:
                    v = held[(s, ch, car, rn, fid)]
                    v[0] += win
                    v[1] += 1
                    if hi:
                        v[2] += win
                        v[3] += 1

            # draft: strategies 列表累积 -> 用最后一回合的
            if last_priv is not None:
                fsd = last_priv.get("fateStrategyData") or {}
                for ev in (fsd.get("strategies") or []):
                    slot = SLOT_OF.get(ev.get("id"))
                    if slot is None:
                        continue
                    sel = ev.get("selected") or 0
                    for o in (ev.get("pendings") or []):
                        if not o:
                            continue
                        v = draft[(s, ch, car, slot, o)]
                        v[0] += 1
                        if o == sel:
                            v[1] += 1
                        if hi:
                            v[2] += 1
                            if o == sel:
                                v[3] += 1
        print(f"[{ai+1}/{len(ARCHIVES)}] {name}: pop={pop4} "
              f"draft={len(draft)} held={len(held)} ({time.time()-t0:.0f}s)", flush=True)

    inv_char = {i: c for c, i in char_idx.items()}
    char_ids = [inv_char[i] for i in sorted(inv_char)]

    def emit_draft(dd):
        out = []
        for (s, ch, car, slot, fid), v in dd.items():
            if v[0] < MIN_DRAFT:
                continue
            out += [s, ch, car, slot, fid, v[0], v[1], v[2], v[3]]
        return out

    def emit_held(dd):
        out = []
        for (s, ch, car, rn, fid), v in dd.items():
            if v[1] < MIN_HELD:
                continue
            out += [s, ch, car, rn, fid, v[0], v[1], v[2], v[3]]
        return out

    out = {
        "meta": {
            "seasons": SEASONS,
            "careers": sorted(careers_seen),
            "charIds": char_ids,
            "rounds": [1, 27],
            "slotIds": [3, 6, 9],       # strategy id（第 1/2/3 次突破）
            "slots": 3,
            "minHeld": MIN_HELD,
            "minDraft": MIN_DRAFT,
            "population": {"t4000": pop4, "t6000": pop6},
            "archives": len(ARCHIVES),
            "draftStride": 9,           # s,ch,car,slot, fateId, off,pick, off6,pick6
            "heldStride": 9,            # s,ch,car,rd,  fateId, w,g, w6,g6
            "wiki": "data/fates_wiki.json",
            "note": "天衍 = fateStrategyData.strategies; fateId 对应 fates_wiki.byId",
        },
        "draft": emit_draft(draft),
        "held": emit_held(held),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    sz = os.path.getsize(OUT) / 1e6
    print(f"wrote {OUT}: {sz:.2f}MB  draft={len(out['draft'])//9} "
          f"held={len(out['held'])//9} chars={len(char_ids)} "
          f"pop4={pop4} pop6={pop6} ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
