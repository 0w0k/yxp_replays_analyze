#!/usr/bin/env python3
"""Distil the Yi Xian wiki (github.com/sharpobject/yxp_wiki) into one structured
relationship file: data/wiki.json. This is the SINGLE SOURCE OF TRUTH for every
name / sect / grouping used by the site — no guessing, no heuristics.

  sects      : code -> {cn, en}
  careers    : code -> {cn, en}
  characters : id   -> {cn, en, sect}
  cards      : famid-> {cn, en, sect, cat}   (sect from the card page's own
               sect / side-job / character link; cards the wiki does not put in a
               sect keep a category code: 融汇/转换/梦境/法宝/灵宠/...)
  talents    : id   -> {cn, en, sect}

Run:  python build_wiki_data.py     (clones the wiki sparsely if needed)
"""
import json
import os
import re
import subprocess
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
WIKI = os.environ.get("WIKI_DIR") or os.path.join(
    os.environ.get("CLAUDE_JOB_DIR", HERE), "tmp", "wiki")
OUT = os.path.join(HERE, "data", "wiki.json")

SECTS = {"sw": {"cn": "云灵剑宗", "en": "Cloud Spirit Sword Sect"},
         "he": {"cn": "七星阁", "en": "Heptastar Pavilion"},
         "fe": {"cn": "五行道盟", "en": "Five Elements Alliance"},
         "dx": {"cn": "锻玄宗", "en": "Duan Xuan Sect"}}
CAREERS = {"el": {"cn": "炼丹师", "en": "Elixirist"}, "fu": {"cn": "符咒师", "en": "Fuluist"},
           "mu": {"cn": "琴师", "en": "Musician"}, "pa": {"cn": "画师", "en": "Painter"},
           "fm": {"cn": "阵法师", "en": "Formation Master"}, "pm": {"cn": "灵植师", "en": "Plant Master"},
           "ft": {"cn": "命理师", "en": "Fortune Teller"}}
# non-sect card categories the wiki uses, given a stable code + label
CATCODE = {"融汇": ("rh", "融汇", "Fusion"), "转换牌": ("tr", "转换牌", "Transform"),
           "梦境": ("mj", "梦境", "Dream"), "法宝": ("talisman", "法宝", "Treasure"),
           "灵宠": ("spiritual_pet", "灵宠", "Spirit Pet")}
SECTSLUG = {"cloud-spirit-sword-sect": "sw", "heptastar-pavilion": "he",
            "five-elements-alliance": "fe", "duan-xuan-sect": "dx"}
JOBSLUG = {"elixirist": "el", "fuluist": "fu", "musician": "mu", "painter": "pa",
           "formation-master": "fm", "plant-master": "pm", "fortune-teller": "ft"}
LEAD = {"1": "sw", "2": "he", "3": "fe", "4": "dx"}
GROUP = {"cloud-spirit-sword-sect": "sw", "heptastar-pavilion": "he",
         "five-elements-alliance": "fe", "duan-xuan-sect": "dx",
         "general": "general", "heavenly-derivation": "heaven"}


def fam(c):
    return c - ((c // 10000) % 100) * 10000


def ensure_wiki():
    if os.path.isdir(os.path.join(WIKI, "zh", "cards")):
        return
    os.makedirs(os.path.dirname(WIKI), exist_ok=True)
    subprocess.run(["git", "clone", "--filter=blob:none", "--depth", "1", "--sparse",
                    "https://github.com/sharpobject/yxp_wiki.git", WIKI], check=True)
    subprocess.run(["git", "-C", WIKI, "sparse-checkout", "set", "zh", "en"], check=True)


def rd(p):
    return open(p, encoding="utf-8", errors="ignore").read()


def h1(h):
    m = re.search(r"<h1>(.*?)</h1>", h)
    return m.group(1).strip() if m else ""


def en_name(h):
    m = re.search(r"original-name[^>]*>.*?</span>(.*?)</p>", h, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def link_sect(h):
    for sl in re.findall(r"/zh/sects/([a-z-]+)\.html", h):
        if sl in SECTSLUG:
            return SECTSLUG[sl]
    for sl in re.findall(r"/zh/side-jobs/([a-z-]+)\.html", h):
        if sl in JOBSLUG:
            return JOBSLUG[sl]
    m = re.search(r"/zh/characters/(\d+)\.html", h)
    if m:
        return LEAD.get(str(m.group(1))[0])
    return None


def breadcrumb_cat(h):
    bc = re.search(r"breadcrumb.*?</nav>", h, re.S)
    if not bc:
        return ""
    seg = [s.strip() for s in re.sub(r"<[^>]+>", " ", bc.group(0)).split("›")]
    return seg[2] if len(seg) > 2 else ""


def main():
    ensure_wiki()
    out = {"sects": SECTS, "careers": CAREERS, "characters": {}, "cards": {}, "talents": {},
           "catLabels": {c[0]: {"cn": c[1], "en": c[2]} for c in CATCODE.values()}}

    # characters
    for p in glob.glob(os.path.join(WIKI, "zh", "characters", "*.html")):
        b = os.path.splitext(os.path.basename(p))[0]
        if not b.isdigit():
            continue
        h = rd(p)
        out["characters"][b] = {"cn": h1(h), "en": en_name(h), "sect": LEAD.get(b[0], "")}

    # cards
    for p in glob.glob(os.path.join(WIKI, "zh", "cards", "*.html")):
        b = os.path.splitext(os.path.basename(p))[0]
        if not b.isdigit():
            continue
        h = rd(p)
        cat = breadcrumb_cat(h)
        sect = link_sect(h)
        if not sect:
            sect = CATCODE.get(cat, (None,))[0]
        f = fam(int(b))
        if f not in out["cards"]:
            out["cards"][str(f)] = {"cn": h1(h), "en": en_name(h), "sect": sect or "", "cat": cat}

    # talents (fate pages): id -> name + sect grouping
    name_by_id, sect_by_id, en_by_id = {}, {}, {}
    for p in glob.glob(os.path.join(WIKI, "zh", "fates", "*.html")):
        base = os.path.basename(p)[:-5]
        h = rd(p)
        for iid, alt in re.findall(r'Icon_Talent_(\d+)\.png"\s+alt="([^"]*)"', h):
            t = int(iid) % 10000
            if alt:
                name_by_id.setdefault(t, alt)
        for slug, fid in re.findall(r'href="(?:/yxp_wiki/zh/fates/)?([a-z0-9-]+)-(\d+)\.html"', h):
            en_by_id.setdefault(int(fid) % 10000, slug)
        # a fate detail page's OWN breadcrumb sect is authoritative for that fate
        if re.match(r"[a-z].*-\d+$", base):
            fid = int(base.split("-")[-1]) % 10000
            g = link_sect(h)
            if g:
                sect_by_id[fid] = g
        g2 = GROUP.get(base)
        if g2:
            for iid in re.findall(r"Icon_Talent_(\d+)\.png", h):
                sect_by_id.setdefault(int(iid) % 10000, g2)
    for t in set(name_by_id) | set(en_by_id):
        out["talents"][str(t)] = {"cn": name_by_id.get(t, ""), "en": en_by_id.get(t, ""),
                                  "sect": sect_by_id.get(t, "")}

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {OUT}: characters={len(out['characters'])} cards={len(out['cards'])} "
          f"talents={len(out['talents'])}")


if __name__ == "__main__":
    main()
