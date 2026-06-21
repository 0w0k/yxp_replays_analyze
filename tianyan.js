"use strict";
// 天衍万象仙命（天衍）统计页。
// 数据：data/tianyan.json（fateStrategyData 聚合）+ data/fates_wiki.json（wiki 权威映射）。
// 命格 id 直接对应 fates_wiki.byId，名称/门派/分类/图标全部取自 wiki。

const UI = {
  en: {
    xyTitle: "Heavenly Derivation — fate picks",
    xySubPre: "Tian Yan Wan Xiang · 4-pick ·", xySubMid: "offers ·", xySubPost: "fates",
    navHome: "Home", navCards: "Cards", navDecks: "Combos", navFate: "Fate", navXY: "Heavenly",
    tier: "DaoXin tier", language: "Language", pickRound: "Breakthrough", allPicks: "All",
    fateSect: "Fate sect", career: "Career", character: "Character", sortby: "Sort by",
    minoffers: "Min offers", search: "Search", nomatch: "No fates match these filters.",
    footData: "Data:",
    xyFootNote: "At each of the 3 breakthroughs (strategy id 3/6/9) every player picks 1 of 4 Heavenly-Derivation fates (FateStrategyConfig). Pick rate = picked / offered; held WR = round wins while holding it.",
    all: "All", none: "None", allSel: "All", nSel: "selected", searchPh: "name…",
    offered: "Offered", pickrate: "Pick rate", heldwr: "Held WR", cardname: "Name",
    noSideJob: "No side-job", colFate: "Heavenly fate",
  },
  zh: {
    xyTitle: "天衍选择统计",
    xySubPre: "天衍万象 · 4选1 ·", xySubMid: "次出现 ·", xySubPost: "个仙命",
    navHome: "首页", navCards: "卡牌", navDecks: "卡组", navFate: "仙命", navXY: "天衍",
    tier: "道心段位", language: "语言", pickRound: "突破", allPicks: "全部",
    fateSect: "门派", career: "副职", character: "角色", sortby: "排序",
    minoffers: "最少出现", search: "搜索", nomatch: "没有符合条件的仙命。",
    footData: "数据：",
    xyFootNote: "三次突破（strategy id 3/6/9）各从随机 4 个天衍万象仙命里 4 选 1（FateStrategyConfig）。选取率=被选/出现；持有胜率=带着它时的回合胜率。",
    all: "全部", none: "清空", allSel: "全部", nSel: "项已选", searchPh: "名称…",
    offered: "出现次数", pickrate: "选取率", heldwr: "持有胜率", cardname: "名称",
    noSideJob: "无副职", colFate: "天衍仙命",
  },
};
const t = (k) => (UI[S.lang][k] ?? UI.en[k] ?? k);

const S = {
  th: 4000, lang: "zh", slot: -1,
  careers: new Set(), chars: new Set(), fatesects: new Set(),
  sort: "pr", minGames: 30, q: "",
};
let NAMES = null, F = null, W = null, ICON = "", SECT_OF = null, MAXID = 0;
const $ = (s) => document.querySelector(s);
let raf = 0;
const schedule = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; render(); }); };

async function boot() {
  [NAMES, F, W] = await Promise.all([
    fetch("data/names.json").then((r) => r.json()),
    fetch("data/tianyan.json").then((r) => r.json()),
    fetch("data/fates_wiki.json").then((r) => r.json()),
  ]);
  ICON = W._meta.iconBase;
  SECT_OF = {};                                   // fateId -> sect name
  for (const k in W.byId) { SECT_OF[+k] = W.byId[k].sect; if (+k > MAXID) MAXID = +k; }
  S.careers = new Set(F.meta.careers);
  S.chars = new Set(F.meta.charIds);
  S.fatesects = new Set(W.sects.map((s) => s.name));
  buildFateSect(); buildCareer(); buildCharacter(); wireStatic(); applyLang(); render();
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
// 命格门派（来自 wiki：通用/云灵剑宗/七星阁/五行道盟/锻玄宗）
function buildFateSect() {
  const host = document.querySelector('[data-ms="fatesect"]'), all = W.sects.map((s) => s.name);
  multiselect(host,
    () => summaryCount(S.fatesects, all.length, t("allSel")),
    (panel) => {
      panel.innerHTML = "";
      panel.appendChild(tools(
        () => { all.forEach((n) => S.fatesects.add(n)); host._refresh(); schedule(); },
        () => { S.fatesects.clear(); host._refresh(); schedule(); }));
      W.sects.forEach((s) => panel.appendChild(row(
        `${s.name} (${s.fates.length})`, S.fatesects.has(s.name),
        (on) => { on ? S.fatesects.add(s.name) : S.fatesects.delete(s.name); host._refresh(); schedule(); })));
    });
}
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

// ---- helpers ---------------------------------------------------------------
function selectedCharFlags() { return F.meta.charIds.map((id) => S.chars.has(id)); }
function fateName(id) { const i = W.byId[id]; return (i && i.name) || ("#" + id); }
function fateIcon(id) { const i = W.byId[id]; return i && i.icon ? ICON + i.icon : ""; }
function wrColor(wr) {
  const x = Math.max(0, Math.min(1, (wr - 0.4) / 0.2));
  return `rgb(${Math.round(232 + (54 - 232) * x)},${Math.round(85 + (196 - 85) * x)},${Math.round(78 + (107 - 78) * x)})`;
}

// ---- aggregation -----------------------------------------------------------
function aggregate() {
  const N = MAXID + 1;
  const careers = S.careers, charSel = selectedCharFlags();
  const oc = S.th === 6000 ? 7 : 5, pc = S.th === 6000 ? 8 : 6;  // offered, picked cols
  const off = new Float64Array(N), pick = new Float64Array(N);
  const A = F.draft || [], st = F.meta.draftStride;
  for (let i = 0; i < A.length; i += st) {
    if (S.slot >= 0 && A[i + 3] !== S.slot) continue;
    if (!charSel[A[i + 1]] || !careers.has(A[i + 2])) continue;
    const id = A[i + 4];
    off[id] += A[i + oc]; pick[id] += A[i + pc];
  }
  // held win rate (all rounds) — independent of breakthrough slot
  const H = F.held || [], hs = F.meta.heldStride, hw = S.th === 6000 ? 7 : 5, hg = S.th === 6000 ? 8 : 6;
  const w = new Float64Array(N), g = new Float64Array(N);
  for (let i = 0; i < H.length; i += hs) {
    if (!charSel[H[i + 1]] || !careers.has(H[i + 2])) continue;
    const id = H[i + 4];
    w[id] += H[i + hw]; g[id] += H[i + hg];
  }
  return { off, pick, w, g };
}

// ---- render ----------------------------------------------------------------
function render() {
  const { off, pick, w, g } = aggregate();
  const q = S.q.toLowerCase();
  const match = (id) => !q || fateName(id).includes(S.q) || ("" + id).includes(q);
  let rows = [], totalOff = 0;
  for (let id = 1; id <= MAXID; id++) {
    if (!off[id]) continue;
    if (!S.fatesects.has(SECT_OF[id])) continue;
    totalOff += off[id];
    if (off[id] < S.minGames || !match(id)) continue;
    rows.push({ id, off: off[id], pr: pick[id] / off[id], hw: g[id] ? w[id] / g[id] : null });
  }
  if (S.sort === "off") rows.sort((a, b) => b.off - a.off);
  else if (S.sort === "heldwr") rows.sort((a, b) => (b.hw ?? -1) - (a.hw ?? -1));
  else if (S.sort === "name") rows.sort((a, b) => fateName(a.id).localeCompare(fateName(b.id)));
  else rows.sort((a, b) => b.pr - a.pr || b.off - a.off);

  $("#gamecount").textContent = Math.round(totalOff).toLocaleString();
  $("#rowcount").textContent = rows.length.toLocaleString();
  $("#empty").hidden = rows.length > 0;
  const frag = document.createDocumentFragment();
  frag.appendChild(headerRow());
  rows.slice(0, 400).forEach((r, k) => frag.appendChild(itemRow(r, k + 1)));
  const grid = $("#grid"); grid.innerHTML = ""; grid.appendChild(frag);
}
function headerRow() {
  const el = document.createElement("div");
  el.className = "drow dhead";
  el.innerHTML = `<div class="drank">#</div><div class="dcombo">${t("colFate")}</div>
    <div class="dgames">${t("offered")}</div><div class="dwr">${t("pickrate")}</div>
    <div class="dlift">${t("heldwr")}</div>`;
  return el;
}
function nameCell(id) {
  const info = W.byId[id] || {};
  const nm = fateName(id), src = fateIcon(id);
  const sub = info.sect ? `<span class="fsect">${info.sect}${info.category ? " · " + info.category : ""}</span>` : "";
  return `<span class="cthumb tchip" title="${nm}${info.desc ? " — " + info.desc : ""}">
    <img class="talimg" loading="lazy" src="${src}"
      onerror="this.onerror=null;this.style.display='none';this.nextElementSibling.style.display='inline-block'" alt="">
    <span class="tdot" style="display:none"></span>
    <span class="cnm">${nm}</span>${sub}</span>`;
}
function itemRow(r, rank) {
  const hwTxt = r.hw == null ? "—" : `<span style="color:${wrColor(r.hw)}">${(r.hw * 100).toFixed(1)}%</span>`;
  const el = document.createElement("div");
  el.className = "drow";
  el.innerHTML = `<div class="drank">${rank}</div>
    <div class="dcombo">${nameCell(r.id)}</div>
    <div class="dgames">${r.off.toLocaleString()}</div>
    <div class="dwr"><b>${(r.pr * 100).toFixed(1)}%</b>
      <div class="bar"><i style="width:${(r.pr * 100).toFixed(1)}%;background:#5b8cff"></i></div></div>
    <div class="dlift">${hwTxt}</div>`;
  return el;
}

// ---- sort options ----------------------------------------------------------
function buildSortOptions() {
  const sel = $("#sort");
  const opts = [["pr", t("pickrate")], ["off", t("offered")], ["heldwr", t("heldwr")], ["name", t("cardname")]];
  if (!opts.some(([v]) => v === S.sort)) S.sort = opts[0][0];
  sel.innerHTML = opts.map(([v, l]) => `<option value="${v}"${v === S.sort ? " selected" : ""}>${l}</option>`).join("");
}
function applyLang() {
  document.documentElement.lang = S.lang === "zh" ? "zh" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $("#search").placeholder = t("searchPh");
  ["fatesect", "career", "character"].forEach((k) => {
    const h = document.querySelector(`[data-ms="${k}"]`); if (h && h._refresh) h._refresh();
  });
  buildSortOptions(); render();
}
function seg(id, fn) {
  $("#" + id).addEventListener("click", (e) => {
    if (e.target.tagName !== "BUTTON") return;
    [...e.currentTarget.children].forEach((b) => b.classList.remove("on"));
    e.target.classList.add("on"); fn(e.target.dataset.v);
  });
}
function wireStatic() {
  seg("threshold", (v) => { S.th = +v; schedule(); });
  seg("lang", (v) => { S.lang = v; applyLang(); });
  seg("slot", (v) => { S.slot = +v; render(); });
  $("#sort").addEventListener("change", (e) => { S.sort = e.target.value; render(); });
  $("#mingames").addEventListener("input", (e) => {
    S.minGames = +e.target.value; $("#minlbl").textContent = e.target.value; schedule();
  });
  $("#search").addEventListener("input", (e) => { S.q = e.target.value.trim(); schedule(); });
  document.addEventListener("click", () => document.querySelectorAll(".ms-panel").forEach((p) => p.hidden = true));
}
boot();
