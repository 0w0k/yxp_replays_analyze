#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首页(landing)用的精简数据：从四个页面的 data 文件各抽 Top5 -> data/home.json.

口径与各子页一致(season9, 段位分>=4000, 全角色/全副职/全回合)：
  cards   : data/data_4000.json   每卡 wins/losses 聚合，按出场(g)取 Top5（条形=胜率）
  combos  : data/decks.json       复刻 deck.js 的 pair lift，按 lift 取 Top5
  fates   : data/fates.json       talDraft 选取率(picked/offered)，按选取率 Top5
  tianyan : data/tianyan.json     天衍 draft 选取率，按选取率 Top5（名/门派来自 fates_wiki）
首页只读这个几 KB 的文件，不必加载几 MB 的大 JSON。
"""
import datetime
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
# IN_DIR = 业务数据来源(可指向 data/v175 做按版本汇总)，STATIC = 版本无关的静态文件
# (fates_wiki.json 永远从 data/ 读)，OUT_DIR = 输出目录。默认全为 data/，行为不变。
IN_DIR = os.path.join(HERE, os.environ.get("IN_DIR") or "data")
STATIC = os.path.join(HERE, "data")
OUT_DIR = os.path.join(HERE, os.environ.get("OUT_DIR") or "data")
D = IN_DIR
OUT = os.path.join(OUT_DIR, "home.json")
TOPN = 5            # 数据亮点 chip 取 top1，天衍 top5
TOP_CARDS = 40      # 卡牌散点图的点数
TOP_BARS = 8        # 条形图(卡组/仙命)的条数

# 卡牌门派码 -> 中文门派名（与 home.js 的 SECT_COLOR / 天衍门派一致）。
# 四大门派之外（道具/灵宠/职业牌等）统一归「通用」，散点按此着色。
SECT_CN = {"sw": "云灵剑宗", "he": "七星阁", "fe": "五行道盟", "dx": "锻玄宗"}


def load(name):
    path = os.path.join(D, name)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: required data file not found: {path}", file=sys.stderr)
        raise
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON in {path}: {e}", file=sys.stderr)
        raise


def load_static(name):
    # 版本无关的静态文件(如 fates_wiki.json)始终从 data/ 读
    path = os.path.join(STATIC, name)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: required static file not found: {path}",
              file=sys.stderr)
        raise
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON in {path}: {e}", file=sys.stderr)
        raise


def top_cards():
    j = load("data_4000.json")
    cards, facts = j["cards"], j["facts"]
    n = len(cards)
    wins = [0.0] * n
    g = [0.0] * n
    for i in range(0, len(facts), 8):
        fam = facts[i + 3]
        w, l = facts[i + 6], facts[i + 7]
        wins[fam] += w
        g[fam] += w + l
    order = sorted(range(n), key=lambda k: g[k], reverse=True)
    out = []
    for k in order[:TOP_CARDS]:
        c = cards[k]
        out.append({"cn": c["cn"], "wr": (wins[k] / g[k]) if g[k] else 0,
                    "g": int(g[k]), "sect": SECT_CN.get(c.get("sect"), "通用")})
    # nCards = 出场过(g>0)的卡牌总数，用于首页 KPI
    ncards = sum(1 for x in g if x > 0)
    return out, j["meta"].get("population"), ncards


def top_combos():
    j = load("decks.json")
    cards = j["cards"]
    P, ps = j["pairs"], j["meta"]["pairStride"]
    G, gs = j["singles"], j["meta"]["singleStride"]
    NCARD = len(cards)
    pw, pg = defaultdict(float), defaultdict(float)
    for i in range(0, len(P), ps):
        w, gg = P[i + 6], P[i + 7]          # 4000 档 [winCol, gameCol] = 6,7
        if not gg:
            continue
        key = P[i + 4] * NCARD + P[i + 5]
        pw[key] += w
        pg[key] += gg
    sw = [0.0] * NCARD
    sg = [0.0] * NCARD
    for i in range(0, len(G), gs):
        cidx = G[i + 4]
        sw[cidx] += G[i + 5]                # 4000 档 [winCol, gameCol] = 5,6
        sg[cidx] += G[i + 6]
    rows = []
    for key, gg in pg.items():
        if gg < 2000:                       # 稳一点的样本门槛
            continue
        a, b = divmod(key, NCARD)
        wr = pw[key] / gg
        solo = ((sw[a] / sg[a] if sg[a] else .5) + (sw[b] / sg[b] if sg[b] else .5)) / 2
        rows.append((wr - solo, wr, int(gg), a, b))
    rows.sort(reverse=True)
    out = []
    for lift, wr, gg, a, b in rows[:TOP_BARS]:
        out.append({"a": cards[a]["cn"], "b": cards[b]["cn"],
                    "aImg": cards[a].get("img"), "bImg": cards[b].get("img"),
                    "lift": lift, "wr": wr, "g": gg})
    return out


def top_fates():
    # 持有胜率(held WR)：带着该天赋时的回合胜率，比"选取率"更有指导意义
    # （选取率 Top 全是接近必点的命途天赋，条形会饱和）。大样本门槛去噪。
    j = load("fates.json")
    names = j["talentNames"]
    H, hs = j["talHeld"], j["meta"]["heldStride"]     # stride 9: s,ch,car,rd,idx,w,g,w6,g6
    w, g = defaultdict(float), defaultdict(float)
    for i in range(0, len(H), hs):
        idx = H[i + 4]
        w[idx] += H[i + 5]
        g[idx] += H[i + 6]
    rows = [(w[k] / g[k], int(g[k]), k) for k in g if g[k] >= 20000]
    rows.sort(reverse=True)
    out = []
    for rate, gg, k in rows[:TOP_BARS]:
        c = names[k]
        out.append({"cn": c.get("cn") or c.get("en"), "en": c.get("en"),
                    "img": c.get("img"), "wr": rate, "g": gg})
    return out


def top_tianyan():
    j = load("tianyan.json")
    W = load_static("fates_wiki.json")["byId"]
    A, st = j["draft"], j["meta"]["draftStride"]      # stride 9
    off, pick = defaultdict(float), defaultdict(float)
    for i in range(0, len(A), st):
        fid = A[i + 4]
        off[fid] += A[i + 5]
        pick[fid] += A[i + 6]
    rows = [(pick[f] / off[f], int(off[f]), f) for f in off if off[f] >= 500]
    rows.sort(reverse=True)
    top = []
    for rate, o, fid in rows[:TOPN]:
        info = W.get(str(fid), {})
        top.append({"name": info.get("name", "#%d" % fid), "sect": info.get("sect"),
                    "rate": rate, "off": o, "id": fid})
    # 门派分布（天衍被选总次数）—— doughnut
    sp, so = defaultdict(float), defaultdict(float)
    for fid in off:
        s = (W.get(str(fid)) or {}).get("sect") or "其他"
        sp[s] += pick[fid]
        so[s] += off[fid]
    order = ["通用", "云灵剑宗", "七星阁", "五行道盟", "锻玄宗"]
    sects = [{"sect": s, "picked": int(sp[s]), "rate": (sp[s] / so[s]) if so[s] else 0}
             for s in sorted(sp, key=lambda x: order.index(x) if x in order else 99)]
    return {"top": top, "sects": sects}, j["meta"].get("population")


def main():
    cards, pop, ncards = top_cards()
    combos = top_combos()
    fates = top_fates()
    tianyan, tpop = top_tianyan()
    nfates = len(load_static("fates_wiki.json").get("byId", {}))   # 命格库规模(350)
    out = {
        "meta": {
            "season": "天衍万象",
            "population": pop,                 # 461918 / 61751 (cards/combos/fates 口径)
            "tianyanPopulation": tpop,         # 220140 / 41890 (天衍上线后的子集)
            "nCards": ncards,                  # 出场过的卡牌数(KPI)
            "nFates": nfates,                  # 命格库规模(KPI)
            "updated": datetime.date.today().isoformat(),
            "iconBase": "https://sharpobject.github.io/yxp_wiki/assets/fates/",
            "note": "Top5 per page for the landing page charts.",
        },
        "cards": cards, "combos": combos, "fates": fates, "tianyan": tianyan,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
