"use strict";
const WIKI = "https://sharpobject.github.io/yxp_wiki/assets/cards/";
const STRIDE = 8; // [seasonIdx, charIdx, career, fam, level, round, wins, losses]

// ---- i18n ------------------------------------------------------------------
const UI = {
  en: {
    navHome: "Home", navCards: "Cards", navDecks: "Combos", navFate: "Fate", navXY: "Heavenly",
    title: "Yi Xian Card Explorer", subPre: "Win rate & popularity from",
    subMid: "card-battles ·", subPost: "cards shown", tier: "DaoXin tier",
    language: "Language", season: "Season", career: "Career", character: "Character",
    rounds: "Rounds", sortby: "Sort by", popularity: "Popularity", winrate: "Win rate",
    cardname: "Name", mingames: "Min games", search: "Search", nomatch: "No cards match these filters.",
    footData: "Data:", footArt: "card art:",
    footNote: "Win rate = round wins / rounds the card was on the player's board. Levels merged on tiles.",
    levels: "Levels", wrByRound: "Win rate by round", popByRound: "Popularity by round (games)",
    version: "Version", verLatest: "Latest 1.7.5", verPrev: "Earlier",
    all: "All", none: "None", allSel: "All", nSel: "selected", searchPh: "card name…",
    sect: "Sect", baseLevel: "base", overall: "overall",
    notEnough: "Not enough data to calculate win rate at this Min games.",
  },
  zh: {
    navHome: "首页", navCards: "卡牌", navDecks: "卡组", navFate: "仙命", navXY: "天衍",
    title: "弈仙牌 卡牌数据", subPre: "数据来自", subMid: "次出战 ·", subPost: "张卡牌",
    tier: "道心段位", language: "语言", season: "赛季", career: "副职", character: "角色",
    rounds: "回合", sortby: "排序", popularity: "使用率", winrate: "胜率", cardname: "名称",
    mingames: "最少场次", search: "搜索", nomatch: "没有符合条件的卡牌。",
    footData: "数据：", footArt: "卡图：",
    footNote: "胜率 = 该回合胜场 / 该卡在场上的回合数。卡面已合并等级。",
    levels: "等级", wrByRound: "各回合胜率", popByRound: "各回合使用次数",
    version: "版本", verLatest: "最新 1.7.5", verPrev: "之前版本",
    all: "全部", none: "清空", allSel: "全部", nSel: "项已选", searchPh: "卡牌名称…",
    sect: "门派", baseLevel: "基础", overall: "总体",
    notEnough: "当前最少场次下数据不足，无法计算胜率。",
  },
};
// season number -> {en,zh}
const SEASON_NAMES = {
  7: { en: "Tianji Sigil", zh: "天机刻印" },
  8: { en: "Dream Weave", zh: "临渊织梦" },
};
// card sect_code -> character sect (charId leading digit) for normalization denom
const SECT_TO_LEAD = { sw: 1, he: 2, fe: 3, dx: 4 };
// card sect_code -> career number for side-job cards
const CAREER_CARD = { el: 1, fu: 2, mu: 3, pa: 4, fm: 5, pm: 6, ft: 7 };
// card sect_code -> {en,zh}
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
  th: 4000, lang: "zh", version: "v175",
  seasons: new Set(), careers: new Set(), chars: new Set(),
  rlo: 1, rhi: 27, sort: "pop", minGames: 30, q: "",
  modalFam: null, modalLevels: new Set(),
};
// business data dir per selected version ("v175" -> data/v175, "prev" -> data)
const dataBase = () => (S.version === "v175" ? "data/v175" : "data");
const cache = {};
let NAMES = null, DATA = null;
const $ = (s) => document.querySelector(s);
let raf = 0;
const schedule = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; render(); }); };

// ---- load ------------------------------------------------------------------
async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`fetch ${url}: ${r.status} ${r.statusText}`);
  return r.json();
}
async function boot() {
  try {
    NAMES = await fetchJSON("data/names.json");
    await loadThreshold(4000);
    wireStatic();
  } catch (e) {
    console.error("boot failed:", e);
    const el = $("#grid") || document.body;
    el.innerHTML = `<div class="empty" style="color:#e85050;padding:2em">Failed to load data: ${e.message}</div>`;
  }
}
async function loadThreshold(th) {
  S.th = th;
  const key = `${S.version}:${th}`;
  if (!cache[key]) cache[key] = await fetchJSON(`${dataBase()}/data_${th}.json`);
  DATA = cache[key];
  const m = DATA.meta;
  // default selections = everything
  S.seasons = new Set(m.seasons.map((_, i) => i));
  S.careers = new Set(m.careers);
  S.chars = new Set(m.charIds);
  S.rlo = m.rounds[0]; S.rhi = m.rounds[1];
  buildCareer(); buildCharacter(); buildRoundSlider();
  applyLang(); render();
}

// ---- generic multiselect ---------------------------------------------------
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
function seasonName(s) {
  return SEASON_NAMES[s] ? SEASON_NAMES[s][S.lang] : `${t("season")} ${s}`;
}
function buildSeason() {
  const host = document.querySelector('[data-ms="season"]');
  const seasons = DATA.meta.seasons;
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
  if (c === 0) return S.lang === "zh" ? "无副职" : "No side-job";
  return NAMES.careers[c] ? NAMES.careers[c][S.lang] : "" + c;
}
function buildCareer() {
  const host = document.querySelector('[data-ms="career"]');
  const careers = DATA.meta.careers;
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
  const ids = DATA.meta.charIds;
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
  const [lo, hi] = DATA.meta.rounds;
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

// ---- aggregation -----------------------------------------------------------
function galleryAgg() {
  const f = DATA.facts, m = DATA.meta;
  const seasons = S.seasons, careers = S.careers;
  // map charIdx -> selected? + leading-digit (sect) precomputed
  const charSel = m.charIds.map((id) => S.chars.has(id));
  const charLead = m.charIds.map((id) => +String(id)[0]);
  const lo = S.rlo, hi = S.rhi;
  const nFam = DATA.cards.length;
  const wins = new Float64Array(nFam), losses = new Float64Array(nFam);
  const sectTotal = { 1: 0, 2: 0, 3: 0, 4: 0 };
  const careerTotal = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0 };
  let total = 0;
  for (let i = 0; i < f.length; i += STRIDE) {
    const rd = f[i + 5];
    if (rd < lo || rd > hi) continue;
    if (!seasons.has(f[i])) continue;
    const ci = f[i + 1];
    if (!charSel[ci]) continue;
    const car = f[i + 2];
    if (!careers.has(car)) continue;
    const g = f[i + 6] + f[i + 7];
    const fam = f[i + 3];
    wins[fam] += f[i + 6]; losses[fam] += f[i + 7];
    total += g;
    sectTotal[charLead[ci]] += g;     // card-battles by this character's sect
    careerTotal[car] += g;            // card-battles by this career/side-job
  }
  return { wins, losses, total, sectTotal, careerTotal };
}
// denominator for the normalized popularity sort, picked by the card's faction
function factionDenom(card, agg) {
  const code = card.sect;
  if (SECT_TO_LEAD[code]) return agg.sectTotal[SECT_TO_LEAD[code]] || 0;
  if (CAREER_CARD[code]) return agg.careerTotal[CAREER_CARD[code]] || 0;
  return agg.total || 0; // neutral / pet / talisman -> overall
}

// ---- render gallery --------------------------------------------------------
function wrColor(wr) {
  const x = Math.max(0, Math.min(1, (wr - 0.4) / 0.2));
  return `rgb(${Math.round(232 + (54 - 232) * x)},${Math.round(85 + (196 - 85) * x)},${Math.round(78 + (107 - 78) * x)})`;
}
function cardName(c) { return (S.lang === "zh" && c.cn) ? c.cn : (c.en || c.cn || "#" + c.img); }
function sectLabel(code) { return (SECT_CODE[code] || { en: code, zh: code })[S.lang]; }

function render() {
  const A = galleryAgg();
  const { wins, losses, total } = A;
  let rows = [];
  for (let i = 0; i < DATA.cards.length; i++) {
    const g = wins[i] + losses[i];
    if (g < S.minGames) continue;
    const c = DATA.cards[i];
    if (S.q) {
      const q = S.q.toLowerCase();
      if (!(c.en.toLowerCase().includes(q) || (c.cn || "").includes(S.q))) continue;
    }
    // normalized popularity score = appearances / faction's total appearances (after filter)
    const denom = factionDenom(c, A);
    rows.push({ c, g, wr: g ? wins[i] / g : 0, score: denom ? g / denom : 0 });
  }
  if (S.sort === "wr") rows.sort((a, b) => b.wr - a.wr || b.g - a.g);
  else if (S.sort === "name") rows.sort((a, b) => cardName(a.c).localeCompare(cardName(b.c)));
  else rows.sort((a, b) => b.score - a.score || b.g - a.g);

  $("#gamecount").textContent = total.toLocaleString();
  $("#cardcount").textContent = rows.length.toLocaleString();
  const grid = $("#grid"); grid.innerHTML = "";
  $("#empty").hidden = rows.length > 0;
  const frag = document.createDocumentFragment();
  for (const r of rows) frag.appendChild(tile(r));
  grid.appendChild(frag);
}
function tile(r) {
  const c = r.c, col = wrColor(r.wr), name = cardName(c);
  const el = document.createElement("div");
  el.className = "card";
  el.innerHTML = `
    <img loading="lazy" src="${WIKI}${c.img}_${S.lang}.png"
      onerror="this.onerror=null;this.src='${WIKI}${c.img}_en.png'" alt="${name}">
    <div class="nm">${name}</div>
    <div class="sect">${sectLabel(c.sect)}</div>
    <div class="stats"><span class="wr" style="color:${col}">${(r.wr * 100).toFixed(1)}%</span>
      <span class="pop">n=${r.g.toLocaleString()}</span></div>
    <div class="bar"><i style="width:${(r.wr * 100).toFixed(1)}%;background:${col}"></i></div>`;
  el.onclick = () => openModal(c.i);
  return el;
}

// ---- card detail modal -----------------------------------------------------
function openModal(fam) {
  S.modalFam = fam;
  S.modalLevels = new Set(Object.keys(DATA.cards[fam].lv).map(Number));
  $("#modal").hidden = false;
  renderModal();
}
function closeModal() { $("#modal").hidden = true; S.modalFam = null; }

function modalAgg() {
  // for the selected card, respect season/career/char filters (NOT round range),
  // include only selected levels; return per-round [w,l] and overall.
  const f = DATA.facts, m = DATA.meta, fam = S.modalFam;
  const charSel = m.charIds.map((id) => S.chars.has(id));
  const [lo, hi] = m.rounds;
  const perW = new Float64Array(hi + 1), perL = new Float64Array(hi + 1);
  let tw = 0, tl = 0;
  for (let i = 0; i < f.length; i += STRIDE) {
    if (f[i + 3] !== fam) continue;
    if (!S.seasons.has(f[i])) continue;
    if (!charSel[f[i + 1]]) continue;
    if (!S.careers.has(f[i + 2])) continue;
    if (!S.modalLevels.has(f[i + 4])) continue;
    const rd = f[i + 5];
    perW[rd] += f[i + 6]; perL[rd] += f[i + 7];
    tw += f[i + 6]; tl += f[i + 7];
  }
  return { perW, perL, tw, tl, lo, hi };
}
function renderModal() {
  if (S.modalFam == null) return;
  const c = DATA.cards[S.modalFam];
  $("#mImg").src = `${WIKI}${c.img}_${S.lang}.png`;
  $("#mImg").onerror = function () { this.onerror = null; this.src = `${WIKI}${c.img}_en.png`; };
  $("#mName").textContent = cardName(c);
  $("#mSect").textContent = sectLabel(c.sect);

  // level chips
  const chips = $("#mLevels"); chips.innerHTML = "";
  Object.keys(c.lv).map(Number).sort().forEach((lv) => {
    const on = S.modalLevels.has(lv);
    const chip = document.createElement("label");
    chip.className = "lchip" + (on ? "" : " off");
    chip.innerHTML = `<input type="checkbox" ${on ? "checked" : ""}>
      <span>${lv === 0 ? t("baseLevel") : "Lv" + lv}</span>`;
    chip.querySelector("input").onchange = (e) => {
      e.target.checked ? S.modalLevels.add(lv) : S.modalLevels.delete(lv);
      if (S.modalLevels.size === 0) { S.modalLevels.add(lv); e.target.checked = true; } // keep >=1
      renderModal();
    };
    chips.appendChild(chip);
  });

  const { perW, perL, tw, tl, lo, hi } = modalAgg();
  const tot = tw + tl;
  $("#mTot").innerHTML = `<b style="color:${wrColor(tot ? tw / tot : 0)}">${(tot ? tw / tot * 100 : 0).toFixed(1)}%</b>
    ${t("overall")} · n=${tot.toLocaleString()}`;

  // charts
  const rounds = [];
  for (let r = lo; r <= hi; r++) rounds.push(r);
  const maxPop = Math.max(1, ...rounds.map((r) => perW[r] + perL[r]));

  // Win rate by round: only show a round's win rate if it has >= Min games samples.
  const minG = S.minGames;
  const wrHost = $("#chartWR");
  const anyQual = rounds.some((r) => perW[r] + perL[r] >= minG);
  if (!anyQual) {
    wrHost.innerHTML = `<div class="chart-empty">${t("notEnough")}</div>`;
  } else {
    drawChart(wrHost, rounds, (r) => {
      const g = perW[r] + perL[r];
      if (g < minG) return { h: 0, label: r, tip: `R${r}: n=${g} (< ${minG})`, color: "#556", faded: true };
      const wr = perW[r] / g;
      return { h: wr, label: r, tip: `R${r}: ${(wr * 100).toFixed(1)}% (n=${g})`, color: wrColor(wr), faded: false };
    }, true);
  }
  // Popularity by round: always show all rounds (a count is not sample-skewed).
  drawChart($("#chartPop"), rounds, (r) => {
    const g = perW[r] + perL[r];
    return { h: g / maxPop, label: r, tip: `R${r}: ${g.toLocaleString()}`, color: "#5b8cff", faded: g === 0 };
  }, false);
}
function drawChart(host, items, fn, isWr) {
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
  if (isWr) { // 50% reference line via a faint marker is skipped for simplicity
  }
}

// ---- language --------------------------------------------------------------
function applyLang() {
  document.documentElement.lang = S.lang === "zh" ? "zh" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $("#search").placeholder = t("searchPh");
  // refresh dynamic controls' labels
  ["career", "character"].forEach((k) => {
    const h = document.querySelector(`[data-ms="${k}"]`); if (h && h._refresh) h._refresh();
  });
  render();
  if (S.modalFam != null) renderModal();
}

// ---- wiring ----------------------------------------------------------------
function seg(id, fn) {
  $("#" + id).addEventListener("click", (e) => {
    if (e.target.tagName !== "BUTTON") return;
    [...e.currentTarget.children].forEach((b) => b.classList.remove("on"));
    e.target.classList.add("on"); fn(e.target.dataset.v);
  });
}
function wireStatic() {
  seg("threshold", (v) => loadThreshold(+v));
  seg("version", (v) => { S.version = v; loadThreshold(S.th); });
  seg("lang", (v) => { S.lang = v; applyLang(); });
  $("#sort").addEventListener("change", (e) => { S.sort = e.target.value; render(); });
  $("#mingames").addEventListener("input", (e) => {
    S.minGames = +e.target.value; $("#minlbl").textContent = e.target.value; schedule();
    if (S.modalFam != null) renderModal();
  });
  $("#search").addEventListener("input", (e) => { S.q = e.target.value.trim(); schedule(); });
  $("#modalClose").addEventListener("click", closeModal);
  $(".modal-bg").addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
  document.addEventListener("click", () => document.querySelectorAll(".ms-panel").forEach((p) => p.hidden = true));
}

boot();
