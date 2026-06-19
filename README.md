# Yi Xian Card Explorer
Interactive win-rate & popularity explorer for Yi Xian (弈仙牌), from the
[sharpobject/yxp_replays](https://huggingface.co/datasets/sharpobject/yxp_replays) dataset.

Four pages (static site, no build step to view — just open `index.html`):

- **`index.html`** — per-card win rate & popularity (`app.js`, data: `data/data_4000.json` / `data/data_6000.json`).
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
  season-9 archives have no `fateStrategyData`.

The combo & fate pages currently use the **current season 天衍万象 (seasonMec 9)** only.
Season map: 7 = 天机刻印, 8 = 临渊织梦, 9 = 天衍万象 (current).

## Regenerating the data

`data/decks.json` and `data/fates.json` are built from the raw `.tar.zst` replay archives
(a local clone of the dataset at `D:\Coding\yxp_replays_analyze\replays`, set `REPLAYS_DIR` to override):

```sh
pip install zstandard
python build_decks.py        # card-pair combos        -> data/decks.json
python build_fates.py        # talents + dao-yun        -> data/fates.json
python build_tianyan_wiki.py # scrape wiki fate map     -> data/fates_wiki.json
python build_tianyan.py      # Heavenly Derivation picks -> data/tianyan.json
```

`build_tianyan_wiki.py` scrapes the wiki's Heavenly-Derivation page into a tree
(`data/fates_wiki.json`: 5 sects → fates, plus a `byId` index; 350 fates, ids 1–353), the single
source of truth for all 天衍 id→name/sect/category/icon mapping. `build_tianyan.py` then aggregates
`fateStrategyData` over `seasonMec == 9` games (archives **30520000–30747000** only, where the field
exists). The other builders keep `seasonMec == 9` (天衍万象) ranked games with `beginRankScore >= 4000`
(archives 30210000–30747000), and auto-pick min-game thresholds to keep the output lean.
To target a different season, edit `SEASONS` and the `FIRST` / `LAST` archive range at the
top of each script. Card names/art are reused from `data/data_4000.json`; talent names come
from the sibling `yixian-card-counter-with-proxy/proxy/fate_*map.json`. If a local clone is
absent the scripts fall back to downloading + caching under `$CLAUDE_JOB_DIR/tmp`.
