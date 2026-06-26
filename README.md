# Yi Xian Card Explorer
Interactive win-rate & popularity explorer for Yi Xian (弈仙牌), from the
[sharpobject/yxp_replays](https://huggingface.co/datasets/sharpobject/yxp_replays) dataset.

Static site (no build step to view — just open `index.html`):

- **`index.html`** — **landing page** (`home.js` + Chart.js in `vendor/`, data: `data/home.json`).
  A themed "Heavenly Derivation" **dashboard** (styling cues from the 道心榜 leaderboard): a hero with
  season / last-updated pills, a 4-up **KPI strip** (games analysed, Heavenly sample, cards covered,
  fate library), and 4 Chart.js previews that link to the four tools — a cards usage×win-rate
  **median-quadrant scatter** coloured by sect (黑马 / 版本答案 / 大众陷阱 zones), gradient-filled
  top-combo lift bars and top-talent held-WR bars, and a fate-pick doughnut by sect — each with a
  real Top-1 highlight chip. English / 中文 toggle.
- **`cards.html`** — per-card win rate & popularity (`app.js`, data: `data/data_4000.json` / `data/data_6000.json`).
- **`deck.html`** — card-pair **combo / synergy** explorer (`deck.js`, data: `data/decks.json`).
  Sort by synergy (lift), win rate, or games; filter by career / character / round range / DaoXin tier.
  Click a combo to see its per-round win rate and popularity. Methodology is round-level, matching the card page:
  win rate = round wins / rounds the pair shared the board; *lift* = pair win rate − the two cards' average solo win rate.
- **`fate.html`** — **talent (天赋) / dao-yun (道韵)** explorer (`fate.js`, data: `data/fates.json`).
  Toggle system (talent / dao-yun) × metric (held win rate / draft). Held = round-level win rate while holding it;
  draft = pick rate (picked / offered in a 4-pick) shown next to its held win rate.
  This is the **talent draft** (`talentSelectionDatas`) + dao-yun — NOT the Heavenly-Derivation system.
- **`tianyan.html`** — **Heavenly Derivation (天衍万象仙命 / 天衍)** explorer (`tianyan.js`,
  data: `data/tianyan.json` + `data/fates_wiki.json`). This is the real 天衍 system, sourced from the
  replay field `fateStrategyData.strategies` (4-pick at each of the 3 breakthroughs, strategy id 3/6/9).
  Fate id ↔ `fates_wiki.json` (350 fates across 5 sects, scraped from the wiki). Pick rate = picked / offered;
  held WR = round wins while holding the fate. Filter by fate sect / career / character / breakthrough / tier.
  Heads-up: 天衍 only appears from client **version 001.0007.0002** on (archives ~30530000+); earlier
  season-9 archives have no `fateStrategyData`. The 天衍 builder therefore scans from 30520000.

The combo & fate pages currently use the **current season 天衍万象 (seasonMec 9)** only.
Season map: 7 = 天机刻印, 8 = 临渊织梦, 9 = 天衍万象 (current).

## Regenerating the data

`data/decks.json` and `data/fates.json` are built from the raw `.tar.zst` replay archives
(a local clone of the dataset at `D:\Coding\yxp_replays_analyze\replays`, set `REPLAYS_DIR` to override):

```sh
pip install zstandard
python build_cards.py        # single-card win/usage    -> data/data_4000.json + data_6000.json
python build_decks.py        # card-pair combos (size 2) -> data/decks.json
python build_combos.py       # 3-6 card combos          -> data/combos.json
python build_fates.py        # talents + dao-yun        -> data/fates.json
python build_tianyan_wiki.py # scrape wiki fate map     -> data/fates_wiki.json
python build_tianyan.py      # Heavenly Derivation picks -> data/tianyan.json
python build_home.py         # landing digest           -> data/home.json   (run last)
```

### Per-version data (the Version dropdown)

The four tool pages (cards / deck / fate / tianyan) carry a **Version** dropdown — *Latest
1.7.5* (default) vs *Earlier* (the frozen full `data/*.json`). Each replay carries a
`version` field: `001.0007.0005` = 1.7.5, `…0004` = 1.7.4, etc. The latest-version dataset
lives in `data/v175/` and is rebuilt by re-running the same builders with three optional
env vars (unset = original full-season behaviour):

- `BUILD_FIRST` / `BUILD_LAST` — archive range to scan
- `VERSION_FILTER` — keep only games whose `version` equals this
- `OUT_DIR` — output dir (e.g. `data/v175`); `data/data_4000.json` stays the canonical name source

```sh
# rebuild the 1.7.5 (data/v175) bundle the four pages use as "Latest"
export BUILD_FIRST=31000000 BUILD_LAST=31069000 VERSION_FILTER=001.0007.0005 OUT_DIR=data/v175
python build_cards.py && python build_decks.py && python build_combos.py \
  && python build_fates.py && python build_tianyan.py
IN_DIR=data/v175 OUT_DIR=data/v175 python build_home.py   # home reads data/v175/home.json
```

`fates_wiki.json` / `names.json` are version-independent and always read from `data/`.
The landing page (`index.html`) always shows the latest version (`data/v175/home.json`); the
*Earlier* option reuses the existing frozen `data/*.json` and needs no rebuild.

`build_combos.py` mines 3-6 card combos with Apriori. Because combo *breadth* grows fast as the
season's data accumulates, a per-size `LEAN_CAP` keeps only the highest-game (most-played, most
reliable) combos so the shipped `data/combos.json` stays lean (~10 MB) instead of ballooning to 40 MB+.
Raise/lower `LEAN_CAP` at the top of the script to trade coverage for file size.

`build_home.py` pulls a small digest from the four data files into `data/home.json` for the
landing page (Top-40 cards for the scatter — each tagged with its sect for colouring, Top-8
combos/talents for the bars, and the per-sect fate-pick distribution for the doughnut), plus a
`meta` block with the KPI numbers (population, Heavenly sample, card count, fate count, build date),
so the landing needn't load the multi-MB datasets.

`build_tianyan_wiki.py` scrapes the wiki's Heavenly-Derivation page into a tree
(`data/fates_wiki.json`: 5 sects → fates, plus a `byId` index; 350 fates, ids 1–353), the single
source of truth for all 天衍 id→name/sect/category/icon mapping. `build_tianyan.py` then aggregates
`fateStrategyData` over `seasonMec == 9` games (archives **30520000–30869000** only, where the field
exists). The other builders keep `seasonMec == 9` (天衍万象) ranked games with `beginRankScore >= 4000`
(archives 30210000–30869000), and auto-pick min-game thresholds to keep the output lean.
To target a different season, edit `SEASONS` and the `FIRST` / `LAST` archive range at the
top of each script. Card names/art are reused from `data/data_4000.json`; talent names come
from the sibling `yixian-card-counter-with-proxy/proxy/fate_*map.json`. If a local clone is
absent the scripts fall back to downloading + caching under `$CLAUDE_JOB_DIR/tmp`.
