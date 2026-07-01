#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""天衍万象仙命(Heavenly Derivation)wiki → JSON.

抓取 sharpobject 的 yxp_wiki 天衍页面，解析成树状结构 data/fates_wiki.json，
作为后续所有天衍 mapping 的唯一权威来源。

天衍 = replay 里的 fateStrategyData.strategies（4 选 1，id 3/6/9）。
天衍 ID 与本文件的 byId 直接对应（ID 范围 1~353，共 350 个）。

页面 DOM:
  <h2>门派 <span class="muted">(N)</span></h2>
  <article class="fate-card" id="fate-strategy-{ID}">
    <img src=".../Icon_FateStrategy_{ID}.png">
    <h3>天衍名</h3><span class="muted">ID {ID}</span>
    <div class="phase-strip"><span class="phase-chip">分类</span>
       <span class="phase-chip">权重 a / b / c</span> ...</div>
    <p>效果描述</p>
  </article>
"""
import json
import os
import re
import sys
import urllib.request

URL = "https://sharpobject.github.io/yxp_wiki/zh/fates/heavenly-derivation.html"
ICON_BASE = "https://sharpobject.github.io/yxp_wiki/assets/fates/"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "tmp_wiki.html")
OUT = os.path.join(HERE, "data", "fates_wiki.json")

H2_RE = re.compile(r'<h2>(.*?)<span class="muted">\((\d+)\)</span></h2>')
ART_RE = re.compile(r'<article class="fate-card" id="fate-strategy-(\d+)">(.*?)</article>', re.S)
IMG_RE = re.compile(r'<img src="([^"]+)"')
H3_RE = re.compile(r'<h3>(.*?)</h3>')
CHIP_RE = re.compile(r'<span class="phase-chip">(.*?)</span>')
P_RE = re.compile(r'<p>(.*?)</p>', re.S)
WEIGHT_RE = re.compile(r'^\s*权重\s*([\d/\s]+)$')


def fetch():
    try:
        html = urllib.request.urlopen(URL, timeout=30).read().decode("utf-8")
        with open(CACHE, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"fetched {len(html)} bytes from wiki", flush=True)
        return html
    except Exception as e:
        print(f"fetch failed ({e}); falling back to cache {CACHE}", flush=True)
        if not os.path.exists(CACHE):
            raise RuntimeError(
                f"wiki fetch failed and no cached copy at {CACHE}"
            ) from e
        return open(CACHE, encoding="utf-8").read()


def clean(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def parse_article(body):
    img = IMG_RE.search(body)
    icon = img.group(1).rsplit("/", 1)[-1] if img else None
    h3 = H3_RE.search(body)
    name = clean(h3.group(1)) if h3 else ""
    chips = [clean(c) for c in CHIP_RE.findall(body)]
    category, tags, weights = None, [], None
    for c in chips:
        m = WEIGHT_RE.match(c)
        if m:
            weights = [int(x) for x in m.group(1).split("/") if x.strip()]
        elif category is None:
            category = c
        else:
            tags.append(c)
    # description = last <p> in the card body
    ps = P_RE.findall(body)
    desc = clean(ps[-1]) if ps else ""
    return {"name": name, "category": category, "tags": tags,
            "weights": weights, "desc": desc, "icon": icon}


def main():
    html = fetch()
    # walk h2 (sect headers) and article (fate cards) in document order
    tokens = []
    for m in H2_RE.finditer(html):
        tokens.append((m.start(), "h2", clean(m.group(1)), int(m.group(2))))
    for m in ART_RE.finditer(html):
        tokens.append((m.start(), "art", int(m.group(1)), m.group(2)))
    tokens.sort(key=lambda x: x[0])

    sects, by_id, cur = [], {}, None
    for _, kind, a, b in tokens:
        if kind == "h2":
            cur = {"name": a, "count": b, "fates": []}
            sects.append(cur)
        else:
            if cur is None:
                continue
            f = parse_article(b)
            f["id"] = a
            f["sect"] = cur["name"]
            cur["fates"].append(f)
            by_id[str(a)] = {"id": a, "name": f["name"], "sect": cur["name"],
                             "category": f["category"], "tags": f["tags"],
                             "weights": f["weights"], "desc": f["desc"],
                             "icon": f["icon"]}

    total = sum(len(s["fates"]) for s in sects)
    out = {
        "_meta": {
            "source": URL,
            "config": "FateStrategyConfig",
            "season": "天衍万象",
            "field": "fateStrategyData.strategies (4-pick, strategy id 3/6/9)",
            "iconBase": ICON_BASE,
            "total": total,
            "sects": [(s["name"], s["count"], len(s["fates"])) for s in sects],
        },
        "sects": sects,
        "byId": by_id,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # ---- validation -------------------------------------------------------
    print(f"wrote {OUT}", flush=True)
    print(f"total fates parsed: {total} (byId: {len(by_id)})", flush=True)
    for s in sects:
        ok = "OK" if s["count"] == len(s["fates"]) else f"!! declared {s['count']}"
        print(f"  {s['name']}: {len(s['fates'])} ({ok})", flush=True)
    ids = sorted(int(k) for k in by_id)
    print(f"id range: {ids[0]}..{ids[-1]}  unique: {len(set(ids))}", flush=True)
    missing_fields = [k for k, v in by_id.items()
                      if not v["name"] or not v["icon"]]
    if missing_fields:
        print(f"WARN missing name/icon for ids: {missing_fields[:20]}", flush=True)
    # spot-check a few well-known ids from the wiki
    for chk in ("12", "14", "18"):
        v = by_id.get(chk)
        print(f"  check ID {chk}: {v['name'] if v else 'MISSING'} "
              f"[{v['sect'] if v else '-'}] cat={v['category'] if v else '-'} "
              f"w={v['weights'] if v else '-'}", flush=True)
    if total != 350:
        print(f"WARN: expected 350 fates, got {total}", flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
