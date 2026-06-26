# 设计：四页面版本切换 + 1.7.5 单独聚合

日期：2026-06-27

## 背景
已同步新录像（archive 扩展到 31069000）。录像含 `version` 字段，进度：
1.7.2=`001.0007.0002`(≈30530000)、1.7.3=`001.0007.0003`(≈30700000)、
1.7.4=`001.0007.0004`(≈30800000–31000000)、**1.7.5=`001.0007.0005`(≈31050000 起)**。

## 需求（已与用户确认）
- 四个工具页（cards/deck/fate/tianyan）新增「版本」下拉：**最新版本 1.7.5 / 之前版本**，**默认 1.7.5**。
- 「之前版本」= **冻结的现有 `data/*.json`**（截至 30869000），不重新聚合。
- 「最新版本 1.7.5」= 仅 `version==001.0007.0005` 的数据，需新建聚合。
- home 首页**始终只显示 1.7.5**，不加下拉。

## 数据层
- 新目录 `data/v175/`：`data_4000.json`、`data_6000.json`、`decks.json`、`combos.json`、`fates.json`、`tianyan.json`、`home.json`。
- 静态、与版本无关的 `names.json`、`fates_wiki.json` 始终从 `data/` 读，不复制。
- 现有 `data/*.json`（除 home.js 指向变化外）完全不动 = 之前版本。

## 聚合（改造 5 个构建器，向后兼容）
为 `build_cards/decks/combos/fates/tianyan.py` 增加可选环境变量，不设则行为不变：
- `BUILD_FIRST` / `BUILD_LAST` — archive 范围（1.7.5 用 31000000–31069000）
- `VERSION_FILTER` — 设了则每局额外要求 `d["version"]==该值`
- `OUT_DIR` — 输出目录（默认 `data`，1.7.5 用 `data/v175`）

`REF_CARDS`（名称解析）始终指向规范的 `data/data_4000.json`，与 OUT_DIR 解耦。
用「宽范围 31000000 起 + version 精确过滤」稳妥覆盖 1.7.4→1.7.5 边界。

`build_home.py`：业务数据从 `IN_DIR`（=data/v175）读，`fates_wiki.json` 仍从 data/ 读，
输出到 `data/v175/home.json`。

## 前端
- 四页各加一个「版本」`<select>`（沿用 `.ctl` 样式），选项 最新版本 1.7.5 / 之前版本，默认 1.7.5。
- 引入 `DATA_BASE`（`"data/v175"` 或 `"data"`）；业务数据 fetch 路径按版本解析，静态文件固定 `data/`。
- 切版本时重新 fetch + 重渲染，复用各页已有 load/init 流程，缓存键含 version。
- i18n：下拉 label 与选项补 EN/中文词条。
- home.js 的 `data/home.json` 改为 `data/v175/home.json`。

## YAGNI
- 不拆 1.7.4 等多版本；只有「之前版本(全量)」与「1.7.5」两项。
- home 不做切换。
