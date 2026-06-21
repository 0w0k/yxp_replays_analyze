"use strict";
// 首页(landing)：读 data/home.json，用 Chart.js 渲染 4 个吸睛的聚合数据图（仪表盘风格）：
//   卡牌=出场×胜率 四象限散点(按门派着色) · 卡组=连招 lift 渐变条形
//   仙命=天赋持有胜率 渐变条形 · 天衍=门派选取占比 环形
// 设计借鉴「道心榜」数据大屏：KPI 卡条 · 编号分区 · 中位线分区 · 渐变填充。

const UI = {
  en: {
    navHome: "Home", navCards: "Cards", navDecks: "Combos", navFate: "Fate", navXY: "Heavenly",
    heroBadge: "Tian Yan Wan Xiang · Current season",
    heroTitle: "Yi Xian · Heavenly Derivation Data",
    heroTagline: "What's strong this season — straight from real ranked games.",
    seasonPill: "Season · Tian Yan Wan Xiang",
    heroLoading: "Loading…",
    updated: (d) => `Updated ${d}`,
    kpiGames: "Games analysed", kpiGamesSub: "ranked, DaoXin ≥ 4000",
    kpiTianyan: "Heavenly sample", kpiTianyanSub: "games with fateStrategyData",
    kpiCards: "Cards covered", kpiCardsSub: "cards seen this season",
    kpiFates: "Fate library", kpiFatesSub: "fates across 5 sects",
    cardCardsTitle: "Cards · usage × win rate",
    cardCardsMetric: "x = plays   y = win rate   · median quadrants · coloured by sect",
    cardCombosTitle: "Combos · top synergy",
    cardCombosMetric: "lift = pair WR − the two cards' avg solo WR · Top 8",
    cardFatesTitle: "Fate · best talents",
    cardFatesMetric: "round win rate while holding the talent · large-sample Top 8",
    cardTyTitle: "Heavenly · pick share by sect",
    cardTyMetric: "4-pick at each of 3 breakthroughs · share of picks per sect",
    enterCards: "Open Cards →", enterCombos: "Open Combos →", enterFates: "Open Fate →", enterTy: "Open Heavenly →",
    footData: "Data:", footArt: "card art:",
    statCards: "most-played", statCombos: "top synergy", statFates: "best held WR", statTianyan: "most picked",
    axGames: "play count", axWr: "win rate",
    ttUsage: "plays", ttWr: "WR", ttLift: "lift", ttHeld: "held WR", ttPick: "pick rate", ttPicked: "picks",
    qTR: "META PICK", qTL: "DARK HORSE", qBR: "OVERRATED", qBL: "NICHE",
  },
  zh: {
    navHome: "首页", navCards: "卡牌", navDecks: "卡组", navFate: "仙命", navXY: "天衍",
    heroBadge: "天衍万象 · 当前赛季",
    heroTitle: "弈仙牌 · 天衍万象数据站",
    heroTagline: "用真实天梯对局，告诉你这赛季什么强。",
    seasonPill: "赛季 · 天衍万象",
    heroLoading: "加载中…",
    updated: (d) => `更新于 ${d}`,
    kpiGames: "分析对局", kpiGamesSub: "道心 ≥ 4000 天梯",
    kpiTianyan: "天衍样本", kpiTianyanSub: "含 fateStrategyData 的对局",
    kpiCards: "覆盖卡牌", kpiCardsSub: "本赛季出场过的卡牌",
    kpiFates: "命格库", kpiFatesSub: "五大门派天衍命格",
    cardCardsTitle: "卡牌 · 出场 × 胜率",
    cardCardsMetric: "x=出场量　y=胜率　· 中位线四象限 · 点按门派着色",
    cardCombosTitle: "卡组 · 最强连招",
    cardCombosMetric: "lift = 双卡胜率 − 两卡单卡胜率均值 · Top 8",
    cardFatesTitle: "仙命 · 高价值天赋",
    cardFatesMetric: "持有该天赋时的回合胜率 · 大样本 Top 8",
    cardTyTitle: "天衍 · 门派选取占比",
    cardTyMetric: "三次突破 4 选 1 · 各门派命格被选取份额",
    enterCards: "进入卡牌页 →", enterCombos: "进入卡组页 →", enterFates: "进入仙命页 →", enterTy: "进入天衍页 →",
    footData: "数据：", footArt: "卡面：",
    statCards: "出场王", statCombos: "最强连招", statFates: "持有胜率", statTianyan: "最热天衍",
    axGames: "出场量", axWr: "胜率",
    ttUsage: "出场", ttWr: "胜率", ttLift: "协同", ttHeld: "持有胜率", ttPick: "选取率", ttPicked: "选取",
    qTR: "版本答案", qTL: "黑马 · 被低估", qBR: "大众陷阱", qBL: "冷门",
  },
};

const S = { lang: "zh" };
const t = (k) => (UI[S.lang][k] ?? UI.en[k] ?? k);
let H = null;
const charts = {};
const $ = (s) => document.querySelector(s);

const C = { gold: "#f0d088", cyan: "#7be6d6", purple: "#c79bff", blue: "#6f8cff",
  muted: "#94a0b4", line: "rgba(124,142,205,.16)", text: "#e8edf5" };
// 门派色（卡牌散点 / 天衍环形 / 图例 共用）
const SECT_COLOR = { "通用": "#7c8aa5", "云灵剑宗": "#5b8cff", "七星阁": "#c08bff", "五行道盟": "#36c46b", "锻玄宗": "#e8954e" };
const SECT_EN = { "通用": "Neutral", "云灵剑宗": "Sword", "七星阁": "Heptastar", "五行道盟": "Five Elements", "锻玄宗": "Duan Xuan" };
const SECT_ORDER = ["云灵剑宗", "七星阁", "五行道盟", "锻玄宗", "通用"];

const pct = (v) => (v * 100).toFixed(1) + "%";
const plus = (v) => (v >= 0 ? "+" : "") + (v * 100).toFixed(1) + "%";
const wan = (v) => (v / 10000).toFixed(0) + "万";
const wanEn = (v) => (v / 1000).toFixed(0) + "k";
const big = (v) => (S.lang === "zh" ? wan(v) : wanEn(v));

// 沿 x 轴的水平渐变（横向条形用）：图区从左到右 c0 -> c1。
function hGrad(chart, c0, c1) {
  const { ctx, chartArea } = chart;
  if (!chartArea) return c1;
  const g = ctx.createLinearGradient(chartArea.left, 0, chartArea.right, 0);
  g.addColorStop(0, c0); g.addColorStop(1, c1);
  return g;
}

async function boot() {
  wireLang();
  if (typeof Chart === "undefined") { $("#updatedPill").textContent = "Chart.js failed to load."; return; }
  Chart.defaults.color = C.muted;
  Chart.defaults.font.family = "system-ui,-apple-system,Segoe UI,Roboto,'Microsoft YaHei',sans-serif";
  Chart.defaults.font.size = 11;
  try { H = await fetch("data/home.json").then((r) => r.json()); } catch (e) { H = null; }
  applyLang(); renderAll();
}

function base(extra) {
  return Object.assign({
    responsive: true, maintainAspectRatio: false,
    animation: { duration: 600 },
    plugins: { legend: { display: false }, tooltip: {
      backgroundColor: "rgba(14,16,30,.95)", borderColor: C.line, borderWidth: 1,
      titleColor: C.text, bodyColor: "#cdd6ff", padding: 8, displayColors: false } },
  }, extra);
}

function valueLabel(fmt, color) {
  return { id: "vlab", afterDatasetsDraw(c) {
    const { ctx } = c, m = c.getDatasetMeta(0);
    ctx.save(); ctx.fillStyle = color || C.text; ctx.font = "700 11px system-ui"; ctx.textBaseline = "middle";
    m.data.forEach((bar, i) => ctx.fillText(fmt(c.data.datasets[0].data[i]), bar.x + 7, bar.y));
    ctx.restore();
  } };
}

function median(arr) {
  const a = arr.slice().sort((x, y) => x - y), n = a.length;
  return n ? (n % 2 ? a[(n - 1) / 2] : (a[n / 2 - 1] + a[n / 2]) / 2) : 0;
}

// 四象限分区：中位线(虚线) + 四角象限标签
function quadrantPlugin(medX, medY) {
  return { id: "quad", beforeDatasetsDraw(c) {
    const { ctx, chartArea: a, scales } = c;
    const px = scales.x.getPixelForValue(medX), py = scales.y.getPixelForValue(medY);
    ctx.save();
    ctx.strokeStyle = "rgba(150,168,224,.30)"; ctx.lineWidth = 1; ctx.setLineDash([5, 5]);
    ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom);
    ctx.moveTo(a.left, py); ctx.lineTo(a.right, py); ctx.stroke();
    ctx.setLineDash([]);
    ctx.font = "800 11px system-ui"; ctx.textBaseline = "top";
    const pad = 8;
    // 右上=版本答案(亮金) 其余低调
    ctx.fillStyle = "rgba(240,208,136,.85)"; ctx.textAlign = "right";
    ctx.fillText(t("qTR"), a.right - pad, a.top + pad);
    ctx.fillStyle = "rgba(123,230,214,.55)"; ctx.textAlign = "left";
    ctx.fillText(t("qTL"), a.left + pad, a.top + pad);
    ctx.fillStyle = "rgba(148,160,180,.45)"; ctx.textBaseline = "bottom";
    ctx.textAlign = "right"; ctx.fillText(t("qBR"), a.right - pad, a.bottom - pad);
    ctx.textAlign = "left"; ctx.fillText(t("qBL"), a.left + pad, a.bottom - pad);
    ctx.restore();
  } };
}

function renderAll() {
  if (!H) return;
  Object.values(charts).forEach((c) => c.destroy());

  // 1) 卡牌四象限散点：x=出场量, y=胜率%, 颜色按门派, 中位线分区
  const cd = H.cards;
  const medX = median(cd.map((c) => c.g));
  const medY = median(cd.map((c) => +(c.wr * 100).toFixed(2)));
  charts.cards = new Chart($("#chartCards"), {
    type: "scatter",
    data: { datasets: [{
      data: cd.map((c) => ({ x: c.g, y: +(c.wr * 100).toFixed(2), cn: c.cn, sect: c.sect })),
      pointBackgroundColor: cd.map((c) => (SECT_COLOR[c.sect] || C.blue) + "cc"),
      pointBorderColor: cd.map((c) => SECT_COLOR[c.sect] || C.blue),
      pointBorderWidth: 1,
      pointRadius: cd.map((c) => 4 + Math.min(7, c.g / 120000)),
      pointHoverRadius: cd.map((c) => 6 + Math.min(7, c.g / 120000)),
    }] },
    options: base({
      layout: { padding: { top: 6, right: 10 } },
      plugins: { legend: { display: false }, tooltip: { callbacks: {
        title: (it) => it[0].raw.cn,
        label: (it) => `${it.raw.sect} · ${t("ttUsage")} ${it.raw.x.toLocaleString()} · ${t("ttWr")} ${it.raw.y}%` } } },
      scales: {
        x: { title: { display: true, text: t("axGames"), color: C.muted, font: { size: 10 } },
          grid: { color: C.line }, ticks: { callback: wan, maxTicksLimit: 5 } },
        y: { title: { display: true, text: t("axWr"), color: C.muted, font: { size: 10 } },
          grid: { color: C.line }, ticks: { callback: (v) => v + "%" }, suggestedMin: 44, suggestedMax: 64 },
      },
    }),
    plugins: [quadrantPlugin(medX, medY)],
  });
  fillLegend();

  // 2) 卡组条形：lift（rank1 在顶部）渐变蓝->青
  const kb = H.combos.slice();
  charts.combos = new Chart($("#chartCombos"), {
    type: "bar",
    data: { labels: kb.map((c) => `${c.a}+${c.b}`),
      datasets: [{ data: kb.map((c) => +(c.lift * 100).toFixed(2)),
        backgroundColor: (ctx) => hGrad(ctx.chart, "#4a6cf0", "#46e3cf"),
        borderRadius: 5, barPercentage: .82 }] },
    options: base({
      indexAxis: "y", layout: { padding: { right: 46 } },
      plugins: { legend: { display: false }, tooltip: { callbacks: {
        label: (it) => { const c = kb[it.dataIndex]; return `${t("ttLift")} ${plus(c.lift)} · ${t("ttWr")} ${pct(c.wr)} · ${c.g.toLocaleString()}`; } } } },
      scales: { x: { grid: { color: C.line }, ticks: { callback: (v) => "+" + v + "%" }, beginAtZero: true },
        y: { grid: { display: false }, ticks: { color: C.text, font: { size: 10.5 } } } },
    }),
    plugins: [valueLabel((v) => "+" + v.toFixed(1) + "%", "#5fe6d2")],
  });

  // 3) 仙命条形：持有胜率（rank1 在顶部）渐变紫->品红
  const fb = H.fates.slice();
  charts.fates = new Chart($("#chartFates"), {
    type: "bar",
    data: { labels: fb.map((f) => f.cn),
      datasets: [{ data: fb.map((f) => +(f.wr * 100).toFixed(2)),
        backgroundColor: (ctx) => hGrad(ctx.chart, "#7a5cff", "#e06ad6"),
        borderRadius: 5, barPercentage: .82 }] },
    options: base({
      indexAxis: "y", layout: { padding: { right: 44 } },
      plugins: { legend: { display: false }, tooltip: { callbacks: {
        label: (it) => { const f = fb[it.dataIndex]; return `${t("ttHeld")} ${pct(f.wr)} · ${f.g.toLocaleString()}`; } } } },
      scales: { x: { grid: { color: C.line }, ticks: { callback: (v) => v + "%" }, suggestedMin: 55, suggestedMax: 66 },
        y: { grid: { display: false }, ticks: { color: C.text, font: { size: 10.5 } } } },
    }),
    plugins: [valueLabel((v) => v.toFixed(1) + "%", "#e58bdf")],
  });

  // 4) 天衍环形：门派选取占比
  const ty = H.tianyan.sects;
  const total = ty.reduce((s, x) => s + x.picked, 0);
  charts.tianyan = new Chart($("#chartTianyan"), {
    type: "doughnut",
    data: { labels: ty.map((s) => s.sect),
      datasets: [{ data: ty.map((s) => s.picked), backgroundColor: ty.map((s) => SECT_COLOR[s.sect] || C.blue),
        borderColor: "rgba(10,11,22,.7)", borderWidth: 2, hoverOffset: 7 }] },
    options: base({
      cutout: "64%", layout: { padding: 6 },
      plugins: { legend: { display: true, position: "right",
          labels: { color: "#cdd6ff", boxWidth: 10, boxHeight: 10, font: { size: 11 }, padding: 8,
            generateLabels: (c) => c.data.labels.map((lb, i) => ({
              text: S.lang === "zh" ? lb : (SECT_EN[lb] || lb),
              fillStyle: c.data.datasets[0].backgroundColor[i], strokeStyle: "transparent", index: i })) } },
        tooltip: { callbacks: {
          label: (it) => `${S.lang === "zh" ? it.label : (SECT_EN[it.label] || it.label)} · ${t("ttPicked")} ${it.raw.toLocaleString()} (${(it.raw / total * 100).toFixed(0)}%)` } } },
    }),
    plugins: [{ id: "ctext", afterDraw(c) {
      const { ctx, chartArea } = c, x = (chartArea.left + chartArea.right) / 2, y = (chartArea.top + chartArea.bottom) / 2;
      ctx.save(); ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillStyle = C.text; ctx.font = "800 18px system-ui"; ctx.fillText(big(total), x, y - 6);
      ctx.fillStyle = C.muted; ctx.font = "10px system-ui"; ctx.fillText(t("ttPicked"), x, y + 13);
      ctx.restore();
    } }],
  });
}

function fillLegend() {
  const el = $("#legend-cards");
  if (!el || !H) return;
  const present = new Set(H.cards.map((c) => c.sect));
  el.innerHTML = SECT_ORDER.filter((s) => present.has(s)).map((s) =>
    `<span class="lg"><i style="background:${SECT_COLOR[s]}"></i>${S.lang === "zh" ? s : SECT_EN[s]}</span>`).join("");
}

function chip(label, name, value) {
  return `<span class="chip-tag">${label}</span><span class="chip-name">${name}</span><b>${value}</b>`;
}
function fillStats() {
  if (!H) return;
  const c = H.cards[0], k = H.combos[0], f = H.fates[0], y = H.tianyan.top[0];
  if (c) $("#stat-cards").innerHTML = chip(t("statCards"), c.cn, pct(c.wr));
  if (k) $("#stat-combos").innerHTML = chip(t("statCombos"), `${k.a}+${k.b}`, plus(k.lift));
  if (f) $("#stat-fates").innerHTML = chip(t("statFates"), f.cn, pct(f.wr));
  if (y) $("#stat-tianyan").innerHTML = chip(t("statTianyan"), y.name, pct(y.rate));
}

function fillKpis() {
  if (!H || !H.meta) return;
  const m = H.meta;
  const tp = (m.tianyanPopulation || {}).t4000 || 0;
  $("#kpi-games").textContent = (m.population || 0).toLocaleString();
  $("#kpi-tianyan").textContent = tp.toLocaleString();
  $("#kpi-cards").textContent = (m.nCards || 0).toLocaleString();
  $("#kpi-fates").textContent = (m.nFates || 0).toLocaleString();
  if (m.updated) $("#updatedPill").textContent = t("updated")(m.updated);
}

function applyLang() {
  document.documentElement.lang = S.lang === "zh" ? "zh" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.dataset.i18n;
    if (UI[S.lang][key] !== undefined || UI.en[key] !== undefined) el.textContent = t(key);
  });
  fillKpis(); fillStats();
}

function wireLang() {
  $("#lang").addEventListener("click", (e) => {
    if (e.target.tagName !== "BUTTON") return;
    [...e.currentTarget.children].forEach((b) => b.classList.remove("on"));
    e.target.classList.add("on");
    S.lang = e.target.dataset.v;
    applyLang(); renderAll();
  });
}

boot();
