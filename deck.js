"use strict";
const WIKI = "https://sharpobject.github.io/yxp_wiki/assets/cards/";

// ---- i18n ------------------------------------------------------------------
const UI = {
  en: {
    deckTitle: "Yi Xian Combo Explorer",
    deckSubPre: "Card-pair synergy from", deckSubMid: "ranked games ·",
    deckSubPost: "combos shown", navHome: "Home", navCards: "Cards", navDecks: "Combos", navFate: "Fate", navXY: "Heavenly",
    tier: "DaoXin tier", language: "Language", season: "Season", career: "Career",
    character: "Character", rounds: "Rounds", sortby: "Sort by",
    sortLift: "Synergy (lift)", winrate: "Win rate", games: "Games", comboSize: "Cards",
    mingames: "Min games", search: "Search", nomatch: "No combos match these filters.",
    footData: "Data:", footArt: "card art:",
    deckFootNote: "Win rate = round wins / rounds the pair shared the board. Lift = pair win rate − the two cards' average solo win rate.",
    wrByRound: "Win rate by round", popByRound: "Popularity by round (games)",
    all: "All", none: "None", allSel: "All", nSel: "selected", searchPh: "card name…",
    colCombo: "Combo", colWr: "Win rate", colGames: "Games", colLift: "Lift",
    overall: "overall", solo: "solo", together: "together", noSideJob: "No side-job",
    notEnough: "Not enough data at this Min games.",
  },
  zh: {
    deckTitle: "弈仙牌 卡组组合分析",
    deckSubPre: "卡牌组合协同，数据来自", deckSubMid: "次排位对局 ·",
    deckSubPost: "个组合", navHome: "首页", navCards: "卡牌", navDecks: "卡组", navFate: "仙命", navXY: "天衍",
    tier: "道心段位", language: "语言", season: "赛季", career: "副职",
    character: "角色", rounds: "回合", sortby: "排序",
    sortLift: "协同提升", winrate: "胜率", games: "场次", comboSize: "组合大小",
    mingames: "最少场次", search: "搜索", nomatch: "没有符合条件的组合。",
    footData: "数据：", footArt: "卡图：",
    deckFootNote: "胜率 = 两张卡同场回合的胜场 / 同场回合数。协同提升 = 组合胜率 − 两张卡各自单卡胜率的平均。",
    wrByRound: "各回合胜率", popByRound: "各回合同场次数",
    all: "全部", none: "清空", allSel: "全部", nSel: "项已选", searchPh: "卡牌名称…",
    colCombo: "组合", colWr: "胜率", colGames: "场次", colLift: "协同",
    overall: "总体", solo: "单卡", together: "同场", noSideJob: "无副职",
    notEnough: "当前最少场次下数据不足。",
  },
};
const SEASON_NAMES = {
  7: { en: "Tianji Sigil", zh: "天机刻印" },
  8: { en: "Dream Weave", zh: "临渊织梦" },
  9: { en: "Tian Yan Wan Xiang", zh: "天衍万象" },
};
const SECT_CODE = {
  sw: { en: "Cloud Spirit Sword Sect", zh: "云灵剑宗" }, dx: { en: "Duan Xuan Sect", zh: "锻玄宗" },
  he: { en: "Heptastar Pavilion", zh: "七星阁" }, fe: { en: "Five Elements Alliance", zh: "五行道盟" },
  el: { en: "Elixirist", zh: "炼丹师" }, fu: { en: "Fuluist", zh: "符咒师" },
  mu: { en: "Musician", zh: "琴师" }, ft: { en: "Fortune Teller", zh: "命理师" },
  pm: { en: "Plant Master", zh: "灵植师" }, fm: { en: "Formation Master", zh: "阵法师" },
  pa: { en: "Painter", zh: "画师" }, no_marking: { en: "Neutral", zh: "无门派" },
  spiritual_pet: { en: "Spirit Pet", zh: "灵宠" }, talisman: { en: "Treasure", zh: "法宝" },
  rh: { en: "Fusion", zh: "融汇" }, tr: { en: "Transform", zh: "转换牌" }, mj: { en: "Dream", zh: "梦境" },
  "": { en: "—", zh: "—" },
};
const t = (k) => (UI[S.lang][k] ?? UI.en[k] ?? k);

// ---- state -----------------------------------------------------------------
const S = {
  th: 4000, lang: "zh", size: 2,
  seasons: new Set(), careers: new Set(), chars: new Set(),
  rlo: 1, rhi: 27, sort: "lift", minGames: 50, q: "",
  combo: null, // selected combo's fam indices (into the active card list)
};
const cache = {};
let NAMES = null, DECK = null, CMB = null, NCARD = 0;
const $ = (s) => document.querySelector(s);
let raf = 0;
const schedule = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; render(); }); };

// ---- load ------------------------------------------------------------------
async function boot() {
  NAMES = await fetch("data/names.json").then((r) => r.json());
  DECK = await fetch("data/decks.json").then((r) => r.json());
  NCARD = DECK.cards.length;
  const m = DECK.meta;
  S.seasons = new Set(m.seasons.map((_, i) => i));
  S.careers = new Set(m.careers);
  S.chars = new Set(m.charIds);
  S.rlo = m.rounds[0]; S.rhi = m.rounds[1];
  buildCareer(); buildCharacter(); buildRoundSlider();
  wireStatic(); setSizeUI(); applyLang(); render();
}
// the active data source depends on the selected combo size
function activeCards() { return S.size === 2 ? DECK.cards : CMB.cards; }
function activeMeta() { return S.size === 2 ? DECK.meta : CMB.meta; }

// ---- generic multiselect (shared pattern with the card page) ---------------
function multiselect(host, summaryFn, renderPanel) {
  host.innerHTML = `<button class="ms-btn"></button><div class="ms-panel" hidden></div>`;
  const btn = host.querySelector(".ms-btn");
  const panel = host.querySelector(".ms-panel");
  btn.onclick = (e) => {
    e.stopPropagation();
    document.querySelectorAll(".ms-panel").forEach((p) => { if (p !== panel) p.hidden = true; });
    panel.hidden = !panel.hidden;
  };
  panel.onclick = (e) => e.stopPropagation();
  host._refresh = () => { btn.textContent = summaryFn(); renderPanel(panel); };
  host._refresh();
}
function summaryCount(set, total, allWord) {
  if (set.size === total) return allWord;
  return `${set.size} ${t("nSel")}`;
}
function tools(onAll, onNone) {
  const d = document.createElement("div");
  d.className = "ms-tools";
  d.innerHTML = `<button>${t("all")}</button><button>${t("none")}</button>`;
  d.children[0].onclick = onAll; d.children[1].onclick = onNone;
  return d;
}
function row(label, checked, onToggle, cls = "") {
  const r = document.createElement("label");
  r.className = "ms-row " + cls;
  const cb = document.createElement("input");
  cb.type = "checkbox"; cb.checked = checked;
  cb.onchange = () => onToggle(cb.checked, cb);
  r.appendChild(cb);
  const s = document.createElement("span"); s.textContent = label; r.appendChild(s);
  return r;
}

// ---- season ----------------------------------------------------------------
function seasonName(s) { return SEASON_NAMES[s] ? SEASON_NAMES[s][S.lang] : `${t("season")} ${s}`; }
function buildSeason() {
  const host = document.querySelector('[data-ms="season"]');
  const seasons = DECK.meta.seasons;
  multiselect(host,
    () => summaryCount(S.seasons, seasons.length, t("allSel")),
    (panel) => {
      panel.innerHTML = "";
      panel.appendChild(tools(
        () => { seasons.forEach((_, i) => S.seasons.add(i)); host._refresh(); schedule(); },
        () => { S.seasons.clear(); host._refresh(); schedule(); }));
      seasons.forEach((s, i) => panel.appendChild(row(
        seasonName(s), S.seasons.has(i),
        (on) => { on ? S.seasons.add(i) : S.seasons.delete(i); host._refresh(); schedule(); })));
    });
}

// ---- career ----------------------------------------------------------------
function careerName(c) {
  if (c === 0) return t("noSideJob");
  return NAMES.careers[c] ? NAMES.careers[c][S.lang] : "" + c;
}
function buildCareer() {
  const host = document.querySelector('[data-ms="career"]');
  const careers = DECK.meta.careers;
  multiselect(host,
    () => summaryCount(S.careers, careers.length, t("allSel")),
    (panel) => {
      panel.innerHTML = "";
      panel.appendChild(tools(
        () => { careers.forEach((c) => S.careers.add(c)); host._refresh(); schedule(); },
        () => { S.careers.clear(); host._refresh(); schedule(); }));
      careers.forEach((c) => panel.appendChild(row(
        careerName(c), S.careers.has(c),
        (on) => { on ? S.careers.add(c) : S.careers.delete(c); host._refresh(); schedule(); })));
    });
}

// ---- character (grouped by sect) -------------------------------------------
function charName(id) { return NAMES.characters[id] ? NAMES.characters[id][S.lang] : "" + id; }
function sectName(n) { return NAMES.sects[n] ? NAMES.sects[n][S.lang] : "" + n; }
function buildCharacter() {
  const host = document.querySelector('[data-ms="character"]');
  const ids = DECK.meta.charIds;
  const bySect = {};
  ids.forEach((id) => { const s = +String(id)[0]; (bySect[s] = bySect[s] || []).push(id); });
  multiselect(host,
    () => summaryCount(S.chars, ids.length, t("allSel")),
    (panel) => {
      panel.innerHTML = "";
      panel.appendChild(tools(
        () => { ids.forEach((id) => S.chars.add(id)); host._refresh(); schedule(); },
        () => { S.chars.clear(); host._refresh(); schedule(); }));
      Object.keys(bySect).sort().forEach((s) => {
        const group = bySect[s];
        const allOn = group.every((id) => S.chars.has(id));
        const gr = row(sectName(+s), allOn, (on) => {
          group.forEach((id) => on ? S.chars.add(id) : S.chars.delete(id));
          host._refresh(); schedule();
        }, "group");
        gr.querySelector("input").indeterminate = !allOn && group.some((id) => S.chars.has(id));
        panel.appendChild(gr);
        group.forEach((id) => panel.appendChild(row(
          charName(id), S.chars.has(id),
          (on) => { on ? S.chars.add(id) : S.chars.delete(id); host._refresh(); schedule(); }, "child")));
      });
    });
}

// ---- round dual slider -----------------------------------------------------
function buildRoundSlider() {
  const [lo, hi] = DECK.meta.rounds;
  const rlo = $("#rlo"), rhi = $("#rhi");
  [rlo, rhi].forEach((el) => { el.min = lo; el.max = hi; });
  rlo.value = lo; rhi.value = hi; S.rlo = lo; S.rhi = hi;
  const upd = (e) => {
    let a = +rlo.value, b = +rhi.value;
    if (a > b) { if (e.target === rlo) { b = a; rhi.value = b; } else { a = b; rlo.value = a; } }
    S.rlo = a; S.rhi = b;
    $("#roundlbl").textContent = `${a}–${b}`;
    schedule();
  };
  rlo.oninput = upd; rhi.oninput = upd;
  $("#roundlbl").textContent = `${lo}–${hi}`;
}

// ---- helpers ---------------------------------------------------------------
function selectedCharFlags(meta) {
  // index space (matching facts) -> selected?
  return (meta || DECK.meta).charIds.map((id) => S.chars.has(id));
}
// column offsets differ: pairs have an extra card index, so they sit one later.
// singles 9 cols [s,ch,car,rd,fam, w,g, w6,g6]; pairs 10 cols [s,ch,car,rd,a,b, w,g, w6,g6]
function pairCols() { return S.th === 6000 ? [8, 9] : [6, 7]; }   // [winCol, gameCol]
function singleCols() { return S.th === 6000 ? [7, 8] : [5, 6]; }
function cardName(c) { return (S.lang === "zh" && c.cn) ? c.cn : (c.en || c.cn || "#" + c.img); }
function sectLabel(code) { return (SECT_CODE[code] || { en: code, zh: code })[S.lang]; }
function wrColor(wr) {
  const x = Math.max(0, Math.min(1, (wr - 0.4) / 0.2));
  return `rgb(${Math.round(232 + (54 - 232) * x)},${Math.round(85 + (196 - 85) * x)},${Math.round(78 + (107 - 78) * x)})`;
}
function liftColor(l) {
  if (l >= 0) { const x = Math.min(1, l / 0.1); return `rgb(${Math.round(148 - 112 * x)},${Math.round(160 + 36 * x)},${Math.round(180 - 73 * x)})`; }
  const x = Math.min(1, -l / 0.1); return `rgb(${Math.round(148 + 84 * x)},${Math.round(160 - 75 * x)},${Math.round(180 - 102 * x)})`;
}

// ---- aggregation -----------------------------------------------------------
// returns { rows:[{fams:[idx...], g, wr, lift}], cards, total }
function aggregate() {
  if (S.size === 2) return aggPairs();
  if (!CMB) return { rows: [], cards: [], total: 0 };
  return aggCombos(S.size);
}
function aggPairs() {
  const P = DECK.pairs, G = DECK.singles;
  const ps = DECK.meta.pairStride, gs = DECK.meta.singleStride;
  const seasons = S.seasons, careers = S.careers, charSel = selectedCharFlags(DECK.meta);
  const lo = S.rlo, hi = S.rhi, [pwc, pgc] = pairCols();
  const pw = new Map(), pg = new Map();
  for (let i = 0; i < P.length; i += ps) {
    const rd = P[i + 3];
    if (rd < lo || rd > hi) continue;
    if (!seasons.has(P[i]) || !charSel[P[i + 1]] || !careers.has(P[i + 2])) continue;
    const g = P[i + pgc]; if (!g) continue;
    const key = P[i + 4] * NCARD + P[i + 5];
    pw.set(key, (pw.get(key) || 0) + P[i + pwc]);
    pg.set(key, (pg.get(key) || 0) + g);
  }
  const [swc, sgc] = singleCols();
  const sw = new Float64Array(NCARD), sg = new Float64Array(NCARD);
  for (let i = 0; i < G.length; i += gs) {
    const rd = G[i + 3];
    if (rd < lo || rd > hi) continue;
    if (!seasons.has(G[i]) || !charSel[G[i + 1]] || !careers.has(G[i + 2])) continue;
    sw[G[i + 4]] += G[i + swc]; sg[G[i + 4]] += G[i + sgc];
  }
  const q = S.q.toLowerCase(), rows = [];
  let total = 0;
  for (const [key, g] of pg) {
    total += g;
    if (g < S.minGames) continue;
    const a = (key / NCARD) | 0, b = key % NCARD;
    if (!matchQ([a, b], DECK.cards, q)) continue;
    const wr = pw.get(key) / g;
    const lift = wr - ((sg[a] ? sw[a] / sg[a] : .5) + (sg[b] ? sw[b] / sg[b] : .5)) / 2;
    rows.push({ fams: [a, b], g, wr, lift });
  }
  return { rows, cards: DECK.cards, total };
}
function aggCombos(size) {
  const A = CMB.combos[String(size)] || [], N = CMB.cards.length;
  const stride = 3 + size + 4, base = 3 + size;
  const wc = S.th === 6000 ? base + 2 : base, gc = S.th === 6000 ? base + 3 : base + 1;
  const seasons = S.seasons, careers = S.careers, charSel = selectedCharFlags(CMB.meta);
  const cw = new Map(), cg = new Map();
  for (let i = 0; i < A.length; i += stride) {
    if (!seasons.has(A[i]) || !charSel[A[i + 1]] || !careers.has(A[i + 2])) continue;
    const g = A[i + gc]; if (!g) continue;
    let key = "";
    for (let j = 0; j < size; j++) key += A[i + 3 + j] + ",";
    cw.set(key, (cw.get(key) || 0) + A[i + wc]);
    cg.set(key, (cg.get(key) || 0) + g);
  }
  // singles baseline (combos.json singles: [s,ch,car,fam,w,g,w6,g6], no round)
  const G = CMB.singles, gs = 8, swc = S.th === 6000 ? 6 : 4, sgc = S.th === 6000 ? 7 : 5;
  const sw = new Float64Array(N), sg = new Float64Array(N);
  for (let i = 0; i < G.length; i += gs) {
    if (!seasons.has(G[i]) || !charSel[G[i + 1]] || !careers.has(G[i + 2])) continue;
    sw[G[i + 3]] += G[i + swc]; sg[G[i + 3]] += G[i + sgc];
  }
  const q = S.q.toLowerCase(), rows = [];
  let total = 0;
  for (const [key, g] of cg) {
    total += g;
    if (g < S.minGames) continue;
    const fams = key.split(",").filter((x) => x).map(Number);
    if (!matchQ(fams, CMB.cards, q)) continue;
    const wr = cw.get(key) / g;
    let solo = 0;
    for (const f of fams) solo += sg[f] ? sw[f] / sg[f] : .5;
    rows.push({ fams, g, wr, lift: wr - solo / fams.length });
  }
  return { rows, cards: CMB.cards, total };
}
function matchQ(fams, cards, q) {
  if (!q) return true;
  return fams.some((f) => cards[f].en.toLowerCase().includes(q) || (cards[f].cn || "").includes(S.q));
}

// ---- render table ----------------------------------------------------------
function render() {
  const { rows, cards, total } = aggregate();
  if (S.sort === "wr") rows.sort((x, y) => y.wr - x.wr || y.g - x.g);
  else if (S.sort === "games") rows.sort((x, y) => y.g - x.g);
  else rows.sort((x, y) => y.lift - x.lift || y.g - x.g);

  $("#gamecount").textContent = Math.round(total).toLocaleString();
  $("#combocount").textContent = rows.length.toLocaleString();
  const grid = $("#grid");
  grid.classList.toggle("big", S.size >= 4);
  $("#empty").hidden = rows.length > 0;
  const shown = rows.slice(0, 400);
  const frag = document.createDocumentFragment();
  frag.appendChild(headerRow());
  for (let i = 0; i < shown.length; i++) frag.appendChild(comboRow(shown[i], i + 1, cards));
  grid.innerHTML = "";
  grid.appendChild(frag);
}
function headerRow() {
  const el = document.createElement("div");
  el.className = "drow dhead";
  el.innerHTML =
    `<div class="drank">#</div>
     <div class="dcombo">${t("colCombo")}</div>
     <div class="dwr">${t("colWr")}</div>
     <div class="dgames">${t("colGames")}</div>
     <div class="dlift">${t("colLift")}</div>`;
  return el;
}
function thumb(c) {
  const name = cardName(c);
  return `<span class="cthumb" title="${name}">
    <img loading="lazy" src="${WIKI}${c.img}_${S.lang}.png"
      onerror="this.onerror=null;this.src='${WIKI}${c.img}_en.png'" alt="${name}">
    <span class="cnm">${name}</span></span>`;
}
function comboRow(r, rank, cards) {
  const wcol = wrColor(r.wr), lcol = liftColor(r.lift);
  const lsign = r.lift >= 0 ? "+" : "";
  const el = document.createElement("div");
  el.className = "drow";
  const combo = r.fams.map((f) => thumb(cards[f])).join('<span class="plus">+</span>');
  el.innerHTML =
    `<div class="drank">${rank}</div>
     <div class="dcombo">${combo}</div>
     <div class="dwr"><b style="color:${wcol}">${(r.wr * 100).toFixed(1)}%</b>
       <div class="bar"><i style="width:${(r.wr * 100).toFixed(1)}%;background:${wcol}"></i></div></div>
     <div class="dgames">${r.g.toLocaleString()}</div>
     <div class="dlift" style="color:${lcol}">${lsign}${(r.lift * 100).toFixed(1)}%</div>`;
  el.onclick = () => openCombo(r.fams);
  return el;
}

// ---- combo detail modal ----------------------------------------------------
function openCombo(fams) { S.combo = fams.slice(); $("#modal").hidden = false; renderModal(); }
function closeModal() { $("#modal").hidden = true; S.combo = null; }

// per-round win/games for a pair (size 2 only; decks.json has the round dim)
function pairRoundAgg(a, b) {
  const P = DECK.pairs, ps = DECK.meta.pairStride;
  const seasons = S.seasons, careers = S.careers, charSel = selectedCharFlags(DECK.meta);
  const [wc, gc] = pairCols(), [lo, hi] = DECK.meta.rounds;
  const perW = new Float64Array(hi + 1), perG = new Float64Array(hi + 1);
  let tw = 0, tg = 0;
  for (let i = 0; i < P.length; i += ps) {
    if (P[i + 4] !== a || P[i + 5] !== b) continue;
    if (!seasons.has(P[i]) || !charSel[P[i + 1]] || !careers.has(P[i + 2])) continue;
    const rd = P[i + 3], g = P[i + gc];
    perW[rd] += P[i + wc]; perG[rd] += g; tw += P[i + wc]; tg += g;
  }
  return { perW, perG, tw, tg, lo, hi };
}
// overall win/games for an N-card combo (3-6; combos.json, no round)
function comboOverallN(fams) {
  const size = fams.length, A = CMB.combos[String(size)] || [], stride = 3 + size + 4, base = 3 + size;
  const wc = S.th === 6000 ? base + 2 : base, gc = S.th === 6000 ? base + 3 : base + 1;
  const seasons = S.seasons, careers = S.careers, charSel = selectedCharFlags(CMB.meta);
  let tw = 0, tg = 0;
  for (let i = 0; i < A.length; i += stride) {
    if (!seasons.has(A[i]) || !charSel[A[i + 1]] || !careers.has(A[i + 2])) continue;
    let match = true;
    for (let j = 0; j < size; j++) if (A[i + 3 + j] !== fams[j]) { match = false; break; }
    if (!match) continue;
    tw += A[i + wc]; tg += A[i + gc];
  }
  return { tw, tg };
}
function soloWr(fam) {
  let w = 0, g = 0;
  if (S.size === 2) {
    const G = DECK.singles, gs = DECK.meta.singleStride;
    const seasons = S.seasons, careers = S.careers, charSel = selectedCharFlags(DECK.meta);
    const lo = S.rlo, hi = S.rhi, [wc, gc] = singleCols();
    for (let i = 0; i < G.length; i += gs) {
      if (G[i + 4] !== fam) continue;
      const rd = G[i + 3]; if (rd < lo || rd > hi) continue;
      if (!seasons.has(G[i]) || !charSel[G[i + 1]] || !careers.has(G[i + 2])) continue;
      w += G[i + wc]; g += G[i + gc];
    }
  } else {
    const G = CMB.singles, gs = 8, wc = S.th === 6000 ? 6 : 4, gc = S.th === 6000 ? 7 : 5;
    const seasons = S.seasons, careers = S.careers, charSel = selectedCharFlags(CMB.meta);
    for (let i = 0; i < G.length; i += gs) {
      if (G[i + 3] !== fam) continue;
      if (!seasons.has(G[i]) || !charSel[G[i + 1]] || !careers.has(G[i + 2])) continue;
      w += G[i + wc]; g += G[i + gc];
    }
  }
  return g ? w / g : null;
}
function cardMini(c, extra) {
  return `<div class="mcard">
    <img src="${WIKI}${c.img}_${S.lang}.png" onerror="this.onerror=null;this.src='${WIKI}${c.img}_en.png'" alt="">
    <div><div class="mName" style="font-size:15px">${cardName(c)}</div>
      <div class="mSect">${sectLabel(c.sect)}</div>${extra || ""}</div></div>`;
}
function renderModal() {
  if (!S.combo) return;
  const fams = S.combo, cards = activeCards(), size = fams.length;
  const solos = fams.map(soloWr);
  let tw = 0, tg = 0, perW = null, perG = null, lo, hi;
  if (size === 2) { const r = pairRoundAgg(fams[0], fams[1]); ({ perW, perG, tw, tg, lo, hi } = r); }
  else { const r = comboOverallN(fams); tw = r.tw; tg = r.tg; }
  const wr = tg ? tw / tg : 0;
  const baseline = solos.reduce((a, s) => a + (s ?? 0.5), 0) / solos.length;
  const lift = wr - baseline;
  const soloTxt = (s) => s == null ? "—" : `<span style="color:${wrColor(s)}">${(s * 100).toFixed(1)}%</span> ${t("solo")}`;
  $("#mHead").innerHTML = fams.map((f, i) =>
    cardMini(cards[f], `<div class="mTot" style="margin-top:6px">${soloTxt(solos[i])}</div>`))
    .join('<span class="plus big">+</span>');
  $("#mTot").innerHTML =
    `<b style="color:${wrColor(wr)}">${(wr * 100).toFixed(1)}%</b> ${t("together")} · n=${tg.toLocaleString()}
     · <b style="color:${liftColor(lift)}">${lift >= 0 ? "+" : ""}${(lift * 100).toFixed(1)}%</b> ${t("sortLift")}`;

  // per-round charts only exist for pairs (decks.json has the round dim)
  const charts = document.querySelectorAll(".chart-wrap");
  if (size !== 2 || !perG) { charts.forEach((c) => c.hidden = true); return; }
  charts.forEach((c) => c.hidden = false);
  const rounds = [];
  for (let r = lo; r <= hi; r++) rounds.push(r);
  const maxPop = Math.max(1, ...rounds.map((r) => perG[r]));
  const minG = Math.max(5, S.minGames / 5);
  const wrHost = $("#chartWR");
  if (!rounds.some((r) => perG[r] >= minG)) wrHost.innerHTML = `<div class="chart-empty">${t("notEnough")}</div>`;
  else drawChart(wrHost, rounds, (r) => {
    const g = perG[r];
    if (g < minG) return { h: 0, label: r, tip: `R${r}: n=${g}`, color: "#556", faded: true };
    const w = perW[r] / g;
    return { h: w, label: r, tip: `R${r}: ${(w * 100).toFixed(1)}% (n=${g})`, color: wrColor(w), faded: false };
  });
  drawChart($("#chartPop"), rounds, (r) => {
    const g = perG[r];
    return { h: g / maxPop, label: r, tip: `R${r}: ${g.toLocaleString()}`, color: "#5b8cff", faded: g === 0 };
  });
}
function drawChart(host, items, fn) {
  host.innerHTML = "";
  for (const it of items) {
    const d = fn(it);
    const col = document.createElement("div");
    col.className = "col";
    const pct = Math.max(0, Math.min(1, d.h)) * 100;
    col.innerHTML = `<div class="tip">${d.tip}</div>
      <i style="height:${pct}%;background:${d.color};opacity:${d.faded ? .15 : 1}"></i>
      <span>${d.label}</span>`;
    host.appendChild(col);
  }
}

// ---- language --------------------------------------------------------------
function applyLang() {
  document.documentElement.lang = S.lang === "zh" ? "zh" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $("#search").placeholder = t("searchPh");
  ["career", "character"].forEach((k) => {
    const h = document.querySelector(`[data-ms="${k}"]`); if (h && h._refresh) h._refresh();
  });
  render();
  if (S.combo) renderModal();
}

// ---- wiring ----------------------------------------------------------------
function seg(id, fn) {
  $("#" + id).addEventListener("click", (e) => {
    if (e.target.tagName !== "BUTTON") return;
    [...e.currentTarget.children].forEach((b) => b.classList.remove("on"));
    e.target.classList.add("on"); fn(e.target.dataset.v);
  });
}
function setSizeUI() {
  // round filter only applies to pairs (decks.json); combos.json (3-6) has no round dim
  const rc = $("#rounds-ctl");
  if (rc) { rc.style.opacity = S.size === 2 ? "1" : ".4"; rc.style.pointerEvents = S.size === 2 ? "auto" : "none"; }
  document.querySelectorAll("#size button").forEach((b) => b.classList.toggle("on", +b.dataset.v === S.size));
}
function wireStatic() {
  seg("threshold", (v) => { S.th = +v; schedule(); if (S.combo) renderModal(); });
  seg("lang", (v) => { S.lang = v; applyLang(); });
  seg("size", async (v) => {
    S.size = +v; closeModal(); setSizeUI();
    if (S.size >= 3 && !CMB) {          // lazy-load the multi-card data on demand
      $("#grid").innerHTML = `<div class="empty">…</div>`;
      CMB = await fetch("data/combos.json").then((r) => r.json()).catch(() => null);
    }
    render();
  });
  $("#sort").addEventListener("change", (e) => { S.sort = e.target.value; render(); });
  $("#mingames").addEventListener("input", (e) => {
    S.minGames = +e.target.value; $("#minlbl").textContent = e.target.value; schedule();
    if (S.combo) renderModal();
  });
  $("#search").addEventListener("input", (e) => { S.q = e.target.value.trim(); schedule(); });
  $("#modalClose").addEventListener("click", closeModal);
  $(".modal-bg").addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
  document.addEventListener("click", () => document.querySelectorAll(".ms-panel").forEach((p) => p.hidden = true));
}

boot();
