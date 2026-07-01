"use strict";
const WIKI = "https://sharpobject.github.io/yxp_wiki/assets/cards/";
const WIKI_FATES = "https://sharpobject.github.io/yxp_wiki/assets/fates/";
function esc(s) {
  if (typeof s !== "string") return String(s);
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// ---- i18n ------------------------------------------------------------------
const UI = {
  en: {
    fateTitle: "Yi Xian Talent / Dao-Yun Explorer",
    fateSubPre: "Tian Yan Wan Xiang ·", fateSubMid: "ranked games ·", fateSubPost: "shown",
    navHome: "Home", navCards: "Cards", navDecks: "Combos", navFate: "Fate", navXY: "Heavenly",
    version: "Version", verLatest: "Latest 1.7.5", verPrev: "Earlier",
    tier: "DaoXin tier", language: "Language", system: "System", metric: "Metric",
    talent: "Talent", daoyun: "Dao-Yun", mHeld: "Held win rate", mDraft: "Draft",
    career: "Career", character: "Character", rounds: "Rounds", sortby: "Sort by",
    mingames: "Min games", search: "Search", nomatch: "No rows match these filters.",
    footData: "Data:",
    fateFootNote: "Held win rate = round wins / rounds held (round-level). Draft pick rate = picked / offered in a 4-pick. The 仙命/fateBranch system is not recorded in the replays, so this shows the talent draft + dao-yun.",
    wrByRound: "Win rate by round", popByRound: "Popularity by round (games)",
    all: "All", none: "None", allSel: "All", nSel: "selected", searchPh: "name…",
    winrate: "Win rate", usage: "Games", cardname: "Name", pickrate: "Pick rate",
    offered: "Offered", heldwr: "Held WR", noSideJob: "No side-job",
    overall: "overall", notEnough: "Not enough data at this Min games.",
    colTalent: "Talent", colDaoyun: "Dao-Yun",
  },
  zh: {
    fateTitle: "弈仙牌 天赋 / 道韵分析",
    fateSubPre: "天衍万象 ·", fateSubMid: "次排位对局 ·", fateSubPost: "项",
    navHome: "首页", navCards: "卡牌", navDecks: "卡组", navFate: "仙命", navXY: "天衍",
    version: "版本", verLatest: "最新 1.7.5", verPrev: "之前版本",
    tier: "道心段位", language: "语言", system: "系统", metric: "指标",
    talent: "天赋", daoyun: "道韵", mHeld: "持有胜率", mDraft: "选秀",
    career: "副职", character: "角色", rounds: "回合", sortby: "排序",
    mingames: "最少场次", search: "搜索", nomatch: "没有符合条件的项。",
    footData: "数据：",
    fateFootNote: "持有胜率 = 该回合带着它时的胜场 / 持有回合数（回合级）。选取率 = 出现在4选1里被选走的比例。仙命(fateBranch)系统未写入replay，故这里分析天赋选秀 + 道韵。",
    wrByRound: "各回合胜率", popByRound: "各回合持有次数",
    all: "全部", none: "清空", allSel: "全部", nSel: "项已选", searchPh: "名称…",
    winrate: "胜率", usage: "场次", cardname: "名称", pickrate: "选取率",
    offered: "出现次数", heldwr: "持有胜率", noSideJob: "无副职",
    overall: "总体", notEnough: "当前最少场次下数据不足。",
    colTalent: "天赋", colDaoyun: "道韵",
  },
};
const t = (k) => (UI[S.lang][k] ?? UI.en[k] ?? k);

// ---- state -----------------------------------------------------------------
const S = {
  th: 4000, lang: "zh", version: "v175", sys: "tal", metric: "held",
  careers: new Set(), chars: new Set(),
  rlo: 1, rhi: 27, sort: "wr", minGames: 50, q: "", detail: null,
};
let NAMES = null, F = null;
const $ = (s) => document.querySelector(s);
let raf = 0;
const schedule = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; render(); }); };
// business data dir per selected version ("v175" -> data/v175, "prev" -> data)
const dataBase = () => (S.version === "v175" ? "data/v175" : "data");

// ---- load ------------------------------------------------------------------
async function boot() {
  NAMES = await fetch("data/names.json").then((r) => r.json());
  wireStatic();
  await loadVersion();
}
async function loadVersion() {
  closeModal();
  F = await fetch(`${dataBase()}/fates.json`).then((r) => r.json());
  const m = F.meta;
  S.careers = new Set(m.careers);
  S.chars = new Set(m.charIds);
  S.rlo = m.rounds[0]; S.rhi = m.rounds[1];
  buildCareer(); buildCharacter(); buildRoundSlider();
  applyLang(); render();
}

// ---- multiselect (shared pattern) ------------------------------------------
function multiselect(host, summaryFn, renderPanel) {
  host.innerHTML = `<button class="ms-btn"></button><div class="ms-panel" hidden></div>`;
  const btn = host.querySelector(".ms-btn"), panel = host.querySelector(".ms-panel");
  btn.onclick = (e) => {
    e.stopPropagation();
    document.querySelectorAll(".ms-panel").forEach((p) => { if (p !== panel) p.hidden = true; });
    panel.hidden = !panel.hidden;
  };
  panel.onclick = (e) => e.stopPropagation();
  host._refresh = () => { btn.textContent = summaryFn(); renderPanel(panel); };
  host._refresh();
}
function summaryCount(set, total, allWord) { return set.size === total ? allWord : `${set.size} ${t("nSel")}`; }
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

// ---- career ----------------------------------------------------------------
function careerName(c) { return c === 0 ? t("noSideJob") : (NAMES.careers[c] ? NAMES.careers[c][S.lang] : "" + c); }
function buildCareer() {
  const host = document.querySelector('[data-ms="career"]'), careers = F.meta.careers;
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
  const host = document.querySelector('[data-ms="character"]'), ids = F.meta.charIds;
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
  const [lo, hi] = F.meta.rounds, rlo = $("#rlo"), rhi = $("#rhi");
  [rlo, rhi].forEach((el) => { el.min = lo; el.max = hi; });
  rlo.value = lo; rhi.value = hi; S.rlo = lo; S.rhi = hi;
  const upd = (e) => {
    let a = +rlo.value, b = +rhi.value;
    if (a > b) { if (e.target === rlo) { b = a; rhi.value = b; } else { a = b; rlo.value = a; } }
    S.rlo = a; S.rhi = b; $("#roundlbl").textContent = `${a}–${b}`; schedule();
  };
  rlo.oninput = upd; rhi.oninput = upd;
  $("#roundlbl").textContent = `${lo}–${hi}`;
}

// ---- helpers ---------------------------------------------------------------
function curNames() { return S.sys === "tal" ? F.talentNames : F.daoyunNames; }
function curHeld() { return S.sys === "tal" ? F.talHeld : F.dyHeld; }
function curDraft() { return S.sys === "tal" ? F.talDraft : F.dyDraft; }
function selectedCharFlags() { return F.meta.charIds.map((id) => S.chars.has(id)); }
function heldCols() { return S.th === 6000 ? [7, 8] : [5, 6]; }   // [w,g] in held stride 9
function draftCols() { return S.th === 6000 ? [6, 7] : [4, 5]; }  // [offered,picked] in draft stride 8
function itemName(c) { return (S.lang === "zh" && c.cn) ? c.cn : (c.en || c.cn || "#"); }
function wrColor(wr) {
  const x = Math.max(0, Math.min(1, (wr - 0.4) / 0.2));
  return `rgb(${Math.round(232 + (54 - 232) * x)},${Math.round(85 + (196 - 85) * x)},${Math.round(78 + (107 - 78) * x)})`;
}

// ---- aggregation -----------------------------------------------------------
function heldAgg(ignoreRound) {
  const A = curHeld(), N = curNames().length, st = F.meta.heldStride;
  const careers = S.careers, charSel = selectedCharFlags();
  const lo = S.rlo, hi = S.rhi, [wc, gc] = heldCols();
  const w = new Float64Array(N), g = new Float64Array(N);
  for (let i = 0; i < A.length; i += st) {
    if (!ignoreRound) { const rd = A[i + 3]; if (rd < lo || rd > hi) continue; }
    if (!charSel[A[i + 1]]) continue;
    if (!careers.has(A[i + 2])) continue;
    const id = A[i + 4];
    w[id] += A[i + wc]; g[id] += A[i + gc];
  }
  return { w, g };
}
function draftAgg() {
  const A = curDraft(), N = curNames().length, st = F.meta.draftStride;
  const careers = S.careers, charSel = selectedCharFlags();
  const [oc, pc] = draftCols();
  const off = new Float64Array(N), pick = new Float64Array(N);
  for (let i = 0; i < A.length; i += st) {
    if (!charSel[A[i + 1]]) continue;
    if (!careers.has(A[i + 2])) continue;
    const id = A[i + 3];
    off[id] += A[i + oc]; pick[id] += A[i + pc];
  }
  return { off, pick };
}

// ---- render ----------------------------------------------------------------
function render() {
  const names = curNames();
  const q = S.q.toLowerCase();
  const match = (c) => !q || (c.en || "").toLowerCase().includes(q) || (c.cn || "").includes(S.q);
  let rows = [], totalGames = 0;
  if (S.metric === "held") {
    const { w, g } = heldAgg(false);
    for (let i = 0; i < names.length; i++) {
      totalGames += g[i];
      if (g[i] < S.minGames || !match(names[i])) continue;
      rows.push({ i, g: g[i], wr: w[i] / g[i] });
    }
    if (S.sort === "pop") rows.sort((a, b) => b.g - a.g);
    else if (S.sort === "name") rows.sort((a, b) => itemName(names[a.i]).localeCompare(itemName(names[b.i])));
    else rows.sort((a, b) => b.wr - a.wr || b.g - a.g);
  } else {
    const { off, pick } = draftAgg();
    const { w, g } = heldAgg(true); // held WR across all rounds for the "好不好" column
    for (let i = 0; i < names.length; i++) {
      totalGames += off[i];
      if (off[i] < S.minGames || !match(names[i])) continue;
      rows.push({ i, off: off[i], pr: pick[i] / off[i], hw: g[i] ? w[i] / g[i] : null });
    }
    if (S.sort === "off") rows.sort((a, b) => b.off - a.off);
    else if (S.sort === "heldwr") rows.sort((a, b) => (b.hw ?? -1) - (a.hw ?? -1));
    else if (S.sort === "name") rows.sort((a, b) => itemName(names[a.i]).localeCompare(itemName(names[b.i])));
    else rows.sort((a, b) => b.pr - a.pr || b.off - a.off);
  }

  $("#gamecount").textContent = Math.round(totalGames).toLocaleString();
  $("#rowcount").textContent = rows.length.toLocaleString();
  const grid = $("#grid");
  grid.className = "deckmain mode-" + S.metric;
  $("#empty").hidden = rows.length > 0;
  const shown = rows.slice(0, 400);
  const frag = document.createDocumentFragment();
  frag.appendChild(headerRow());
  for (let k = 0; k < shown.length; k++) frag.appendChild(itemRow(shown[k], k + 1));
  grid.innerHTML = "";
  grid.appendChild(frag);
}
function headerRow() {
  const el = document.createElement("div");
  el.className = "drow dhead";
  const nameCol = S.sys === "tal" ? t("colTalent") : t("colDaoyun");
  if (S.metric === "held")
    el.innerHTML = `<div class="drank">#</div><div class="dcombo">${nameCol}</div>
      <div class="dwr">${t("winrate")}</div><div class="dgames">${t("usage")}</div>`;
  else
    el.innerHTML = `<div class="drank">#</div><div class="dcombo">${nameCol}</div>
      <div class="dgames">${t("offered")}</div><div class="dwr">${t("pickrate")}</div>
      <div class="dlift">${t("heldwr")}</div>`;
  return el;
}
function nameCell(c) {
  const nm = esc(itemName(c));
  if (S.sys === "dy") {
    // dao-yun grants a card -> show that card's art (wiki fates folder)
    const src = c.img ? `${WIKI_FATES}Card_${c.img}.png` : "";
    return `<span class="cthumb" title="${nm}">
      <img class="dyimg" loading="lazy" src="${src}"
        onerror="this.onerror=null;this.src='${WIKI}${c.img}_zh.png'" alt="">
      <span class="cnm">${nm}</span></span>`;
  }
  // talent -> its fate icon; fall back to a dot if missing
  const src = c.img ? `${WIKI_FATES}Icon_Talent_${c.img}.png` : "";
  return `<span class="cthumb tchip" title="${nm}">
    <img class="talimg" loading="lazy" src="${src}"
      onerror="this.onerror=null;this.style.display='none';this.nextElementSibling.style.display='inline-block'" alt="">
    <span class="tdot" style="display:none"></span>
    <span class="cnm">${nm}</span></span>`;
}
function itemRow(r, rank) {
  const names = curNames(), c = names[r.i];
  const el = document.createElement("div");
  el.className = "drow";
  if (S.metric === "held") {
    const col = wrColor(r.wr);
    el.innerHTML = `<div class="drank">${rank}</div>
      <div class="dcombo">${nameCell(c)}</div>
      <div class="dwr"><b style="color:${col}">${(r.wr * 100).toFixed(1)}%</b>
        <div class="bar"><i style="width:${(r.wr * 100).toFixed(1)}%;background:${col}"></i></div></div>
      <div class="dgames">${r.g.toLocaleString()}</div>`;
  } else {
    const pcol = "#5b8cff", hwTxt = r.hw == null ? "—" :
      `<span style="color:${wrColor(r.hw)}">${(r.hw * 100).toFixed(1)}%</span>`;
    el.innerHTML = `<div class="drank">${rank}</div>
      <div class="dcombo">${nameCell(c)}</div>
      <div class="dgames">${r.off.toLocaleString()}</div>
      <div class="dwr"><b>${(r.pr * 100).toFixed(1)}%</b>
        <div class="bar"><i style="width:${(r.pr * 100).toFixed(1)}%;background:${pcol}"></i></div></div>
      <div class="dlift">${hwTxt}</div>`;
  }
  el.onclick = () => openDetail(r.i);
  return el;
}

// ---- detail modal: per-round held win rate ---------------------------------
function openDetail(i) { S.detail = i; $("#modal").hidden = false; renderModal(); }
function closeModal() { $("#modal").hidden = true; S.detail = null; }
function detailRoundAgg(id) {
  const A = curHeld(), st = F.meta.heldStride;
  const careers = S.careers, charSel = selectedCharFlags(), [wc, gc] = heldCols();
  const [lo, hi] = F.meta.rounds;
  const perW = new Float64Array(hi + 1), perG = new Float64Array(hi + 1);
  let tw = 0, tg = 0;
  for (let i = 0; i < A.length; i += st) {
    if (A[i + 4] !== id) continue;
    if (!charSel[A[i + 1]]) continue;
    if (!careers.has(A[i + 2])) continue;
    const rd = A[i + 3], g = A[i + gc];
    perW[rd] += A[i + wc]; perG[rd] += g; tw += A[i + wc]; tg += g;
  }
  return { perW, perG, tw, tg, lo, hi };
}
function renderModal() {
  if (S.detail == null) return;
  const c = curNames()[S.detail];
  const { perW, perG, tw, tg, lo, hi } = detailRoundAgg(S.detail);
  const wr = tg ? tw / tg : 0;
  $("#mHead").innerHTML = nameCell(c);
  $("#mTot").innerHTML = `<b style="color:${wrColor(wr)}">${(wr * 100).toFixed(1)}%</b> ${t("overall")} · n=${tg.toLocaleString()}`;
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

// ---- sort options adapt to metric ------------------------------------------
function buildSortOptions() {
  const sel = $("#sort");
  const opts = S.metric === "held"
    ? [["wr", t("winrate")], ["pop", t("usage")], ["name", t("cardname")]]
    : [["pr", t("pickrate")], ["off", t("offered")], ["heldwr", t("heldwr")], ["name", t("cardname")]];
  if (!opts.some(([v]) => v === S.sort)) S.sort = opts[0][0];
  sel.innerHTML = opts.map(([v, l]) => `<option value="${v}"${v === S.sort ? " selected" : ""}>${l}</option>`).join("");
}

// ---- language --------------------------------------------------------------
function applyLang() {
  document.documentElement.lang = S.lang === "zh" ? "zh" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $("#search").placeholder = t("searchPh");
  ["career", "character"].forEach((k) => {
    const h = document.querySelector(`[data-ms="${k}"]`); if (h && h._refresh) h._refresh();
  });
  buildSortOptions();
  render();
  if (S.detail != null) renderModal();
}

// ---- wiring ----------------------------------------------------------------
function seg(id, fn) {
  $("#" + id).addEventListener("click", (e) => {
    if (e.target.tagName !== "BUTTON") return;
    [...e.currentTarget.children].forEach((b) => b.classList.remove("on"));
    e.target.classList.add("on"); fn(e.target.dataset.v);
  });
}
function setMetricUI() {
  $("#rounds-ctl").style.opacity = S.metric === "held" ? "1" : ".4";
  $("#rounds-ctl").style.pointerEvents = S.metric === "held" ? "auto" : "none";
  buildSortOptions();
}
function wireStatic() {
  seg("threshold", (v) => { S.th = +v; schedule(); if (S.detail != null) renderModal(); });
  seg("version", (v) => { S.version = v; loadVersion(); });
  seg("lang", (v) => { S.lang = v; applyLang(); });
  seg("system", (v) => { S.sys = v; closeModal(); render(); });
  seg("metric", (v) => { S.metric = v; setMetricUI(); render(); });
  $("#sort").addEventListener("change", (e) => { S.sort = e.target.value; render(); });
  $("#mingames").addEventListener("input", (e) => {
    S.minGames = +e.target.value; $("#minlbl").textContent = e.target.value; schedule();
    if (S.detail != null) renderModal();
  });
  $("#search").addEventListener("input", (e) => { S.q = e.target.value.trim(); schedule(); });
  $("#modalClose").addEventListener("click", closeModal);
  $(".modal-bg").addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
  document.addEventListener("click", () => document.querySelectorAll(".ms-panel").forEach((p) => p.hidden = true));
  setMetricUI();
}

boot();
