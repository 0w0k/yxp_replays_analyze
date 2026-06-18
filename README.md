# Yi Xian Card Explorer
Interactive win-rate & popularity explorer for Yi Xian (弈仙牌), from the
[sharpobject/yxp_replays](https://huggingface.co/datasets/sharpobject/yxp_replays) dataset.

Three pages (static site, no build step to view — just open `index.html`):

- **`index.html`** — per-card win rate & popularity (`app.js`, data: `data/data_4000.json` / `data/data_6000.json`).
- **`deck.html`** — card-pair **combo / synergy** explorer (`deck.js`, data: `data/decks.json`).
  Sort by synergy (lift), win rate, or games; filter by career / character / round range / DaoXin tier.
  Click a combo to see its per-round win rate and popularity. Methodology is round-level, matching the card page:
  win rate = round wins / rounds the pair shared the board; *lift* = pair win rate − the two cards' average solo win rate.
- **`fate.html`** — **talent (天赋) / dao-yun (道韵)** explorer (`fate.js`, data: `data/fates.json`).
  Toggle system (talent / dao-yun) × metric (held win rate / draft). Held = round-level win rate while holding it;
  draft = pick rate (picked / offered in a 4-pick) shown next to its held win rate.
  Note: the 仙命 / fateBranch system itself is never populated in the replays, so this analyses the talent draft + dao-yun.

The combo & fate pages currently use the **current season 天衍万象 (seasonMec 9)** only.
Season map: 7 = 天机刻印, 8 = 临渊织梦, 9 = 天衍万象 (current).

## Regenerating the data

`data/decks.json` and `data/fates.json` are built from the raw `.tar.zst` replay archives
(a local clone of the dataset at `D:\Coding\yxp_replays_analyze\replays`, set `REPLAYS_DIR` to override):

```sh
pip install zstandard
python build_decks.py        # card-pair combos  -> data/decks.json
python build_fates.py        # talents + dao-yun -> data/fates.json
```

Both keep `seasonMec == 9` (天衍万象) ranked games with `beginRankScore >= 4000`
(archives 30210000–30747000), and auto-pick min-game thresholds to keep the output lean.
To target a different season, edit `SEASONS` and the `FIRST` / `LAST` archive range at the
top of each script. Card names/art are reused from `data/data_4000.json`; talent names come
from the sibling `yixian-card-counter-with-proxy/proxy/fate_*map.json`. If a local clone is
absent the scripts fall back to downloading + caching under `$CLAUDE_JOB_DIR/tmp`.
