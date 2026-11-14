"use strict";
/* Pond Water Forecast front end. Plain JavaScript, no libraries. All text is inserted with textContent (never innerHTML). */

const $ = (id) => document.getElementById(id);
const SVGNS = "http://www.w3.org/2000/svg";

function el(tag, props, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (k === "text") n.textContent = v;
    else if (k === "class") n.className = v;
    else n.setAttribute(k, v);
  }
  for (const c of kids.flat()) if (c != null) n.append(c.nodeType ? c : document.createTextNode(String(c)));
  return n;
}
function svg(tag, attrs) {
  const n = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v);
  return n;
}
function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }

/* ------------------------------------------------------------------ tabs */
const tabs = [["tabPaste", "panelPaste"], ["tabFile", "panelFile"], ["tabExample", "panelExample"]];
let fileText = "";
function showTab(id) {
  for (const [t, p] of tabs) {
    const on = t === id;
    $(t).classList.toggle("on", on);
    $(t).setAttribute("aria-selected", String(on));
    $(p).hidden = !on;
  }
}
for (const [t] of tabs) $(t).addEventListener("click", () => showTab(t));

$("fileBox").addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (!f) return;
  if (f.size > 2000000) { showProblem("That file is too large. Please send at most the last 3 days of readings."); return; }
  const r = new FileReader();
  r.onload = () => { fileText = String(r.result); $("fileName").textContent = `Chosen: ${f.name}`; };
  r.readAsText(f);
});

$("loadExample").addEventListener("click", async () => {
  try {
    const r = await fetch("/api/example");
    const j = await r.json();
    $("pasteBox").value = j.csv;
    $("pondName").value = "Example pond (made-up numbers)";
    showTab("tabPaste");
  } catch { showProblem("We could not load the example. Please try again."); }
});

/* ------------------------------------------------------------------ run */
function showProblem(msg) { const p = $("problem"); p.textContent = msg; p.hidden = !msg; }

$("go").addEventListener("click", async () => {
  showProblem("");
  const onFile = $("tabFile").classList.contains("on");
  const text = onFile ? fileText : $("pasteBox").value;
  if (!text.trim()) { showProblem(onFile ? "Please choose a file first." : "Please paste your readings first, or choose Try an example."); return; }
  const btn = $("go");
  btn.disabled = true; btn.textContent = "Working it out...";
  try {
    const r = await fetch("/api/forecast", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pond_name: $("pondName").value, csv_text: text }) });
    const j = await r.json();
    if (!r.ok) { showProblem(j.problem || "Something went wrong. Please try again."); return; }
    render(j);
  } catch {
    showProblem("We could not reach the forecast service. Please check your connection and try again.");
  } finally {
    btn.disabled = false; btn.textContent = "Get my forecast";
  }
});

/* ------------------------------------------------------------------ render */
function render(j) {
  $("resultsTitle").textContent = `${j.pond_name}: what we expect`;
  $("madeAt").textContent = `Forecast made from your latest reading, ${j.result.made_at}.`;
  $("disclaimer").textContent = j.disclaimer;
  $("ver").textContent = j.result.model_version;

  const sum = $("summary"); clear(sum);
  for (const [k, v] of Object.entries(j.summary)) sum.append(el("div", {}, el("dt", { text: k }), el("dd", { text: v })));
  const iss = $("issues"); clear(iss);
  if (!j.issues.length) iss.append(el("li", { text: "No problems found in your readings." }));
  for (const i of j.issues) iss.append(el("li", { class: i.level === "warn" ? "warn" : "", text: i.text }));

  const lat = $("latest"); clear(lat);
  const L = j.result.latest;
  const names = { DO: ["Oxygen", " mg/L"], pH: ["pH", ""], Temp: ["Water temperature", " °C"] };
  for (const v of ["DO", "pH", "Temp"]) {
    const txt = L[v] == null ? "no recent reading" : (v === "pH" ? L[v].toFixed(2) : L[v].toFixed(1) + names[v][1]);
    lat.append(el("div", {}, el("dt", { text: names[v][0] }), el("dd", { text: txt })));
  }

  renderAlert(j.result.alert);
  const cards = $("forecastCards"); clear(cards);
  for (const v of ["DO", "pH", "Temp"]) cards.append(renderVariable(v, j.result.forecasts[v], j.history));

  $("results").hidden = false;
  $("results").focus({ preventScroll: true });
  $("results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function reasonsList(reasons, note) {
  if (!reasons || !reasons.length) return null;
  return el("div", {}, el("ul", { class: "reasons" }, reasons.map((r) => el("li", { text: `${r.sentence}` }))),
    note ? el("p", { class: "hint", text: note }) : null);
}

function renderAlert(a) {
  const box = $("alertCard"); clear(box);
  const b = el("div", { class: "block" });
  b.append(el("h3", {}, "Chance of very low oxygen", el("span", { class: "badge", text: "Experimental" })));
  b.append(el("p", { class: "muted", text: `How likely oxygen is to drop ${a.threshold_text} at some point. It can raise false alarms, so use it as a hint, not a rule.` }));
  for (const w of a.windows) {
    const row = el("div", { class: "row" });
    row.append(el("div", { class: "when", text: `In ${w.window}` }));
    if (w.status !== "ok") {
      row.append(el("div", { class: "stop", text: `We cannot estimate this: ${w.reason}` }));
    } else {
      const cls = w.level === "High chance" ? "high" : (w.level === "Some chance" ? "some" : "low");
      row.append(el("div", {}, el("span", { class: "value", text: `${w.percent}%` }), " ", el("span", { class: `risk ${cls}`, text: w.level })));
      const m = el("div", { class: `meter ${cls}` }, el("span", {}));
      m.firstChild.style.width = `${Math.max(2, Math.min(100, w.percent))}%`;
      row.append(m);
      const d = el("details", {}, el("summary", { text: "Why this chance?" }), reasonsList(w.reasons, w.reasons_note));
      row.append(d);
    }
    b.append(row);
  }
  box.append(b);
}

function renderVariable(v, items, history) {
  const titles = { DO: "Oxygen", pH: "Acidity (pH)", Temp: "Water temperature" };
  const b = el("div", { class: "block" });
  b.append(el("h3", { text: titles[v] }));
  const ok = items.filter((x) => x.status === "ok");
  if (history && ok.length) b.append(chart(v, history, ok));
  for (const it of items) {
    const row = el("div", { class: "row" });
    row.append(el("div", { class: "when", text: it.when }));
    if (it.status !== "ok") {
      row.append(el("div", { class: "stop", text: `We cannot forecast this: ${it.reason}` }));
    } else {
      row.append(el("div", {}, el("span", { class: "value", text: `About ${it.value_text}` })));
      row.append(el("div", { class: "range", text: `Likely between ${it.range_text}` }));
      row.append(rangeBar(it, ok));
      if (it.note) row.append(el("p", { class: "hint", text: it.note }));
      const d = el("details", {}, el("summary", { text: "How did we get this?" }), el("p", { text: it.story }));
      const rl = reasonsList(it.reasons, it.reasons_note);
      if (rl) { d.append(el("p", { text: "The biggest reasons:" }), rl); }
      row.append(d);
    }
    b.append(row);
  }
  return b;
}

function rangeBar(it, all) {
  const lo = Math.min(...all.map((x) => x.low)), hi = Math.max(...all.map((x) => x.high));
  const span = hi - lo || 1, pad = span * 0.05;
  const pos = (x) => `${(((x - (lo - pad)) / (span + 2 * pad)) * 100).toFixed(1)}%`;
  const bar = el("div", { class: "bar", "aria-hidden": "true" });
  const fill = el("div", { class: "fill" }), dot = el("div", { class: "dot" });
  fill.style.left = pos(it.low); fill.style.right = `${(100 - parseFloat(pos(it.high))).toFixed(1)}%`;
  dot.style.left = pos(it.value);
  bar.append(fill, dot);
  return bar;
}

function chart(v, history, fc) {
  const W = 640, H = 170, padL = 34, padR = 12, padT = 10, padB = 24;
  const ys = history[v].map((y) => (y == null ? null : y));
  const n = ys.length;
  const xsPast = ys.map((_, i) => -((n - 1 - i) * 0.25));
  const allY = [...ys.filter((y) => y != null), ...fc.map((f) => f.low), ...fc.map((f) => f.high)];
  let y0 = Math.min(...allY), y1 = Math.max(...allY);
  const pad = (y1 - y0 || 1) * 0.1; y0 -= pad; y1 += pad;
  if (v === "DO") y0 = Math.max(0, y0);                  // oxygen cannot be below zero, so the chart never shows a negative axis
  const X = (h) => padL + ((h + 24) / 30) * (W - padL - padR);
  const Y = (y) => padT + (1 - (y - y0) / (y1 - y0)) * (H - padT - padB);
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img",
    "aria-label": "Line of the last 24 hours of readings, followed by dots and bars for what we expect next" });
  for (const gy of [0, 0.5, 1]) {
    const yy = padT + gy * (H - padT - padB);
    s.append(svg("line", { x1: padL, x2: W - padR, y1: yy, y2: yy, class: "grid" }));
    const t = svg("text", { x: 2, y: yy + 4 }); t.textContent = (y1 - gy * (y1 - y0)).toFixed(v === "pH" ? 2 : 1); s.append(t);
  }
  let d = "", pen = false;
  ys.forEach((y, i) => { if (y == null) { pen = false; return; } d += `${pen ? "L" : "M"}${X(xsPast[i]).toFixed(1)},${Y(y).toFixed(1)} `; pen = true; });
  s.append(svg("path", { d, class: "past" }));
  s.append(svg("line", { x1: X(0), x2: X(0), y1: padT, y2: H - padB, class: "now" }));
  const label = (x, txt, anchor) => { const t = svg("text", { x, y: H - 6, "text-anchor": anchor }); t.textContent = txt; s.append(t); };
  label(X(-24), "24 hours ago", "start"); label(X(0), "now", "middle"); label(X(6), "+6 hours", "end");
  for (const f of fc) {
    const h = f.ahead_steps * 0.25;
    s.append(svg("line", { x1: X(h), x2: X(h), y1: Y(f.high), y2: Y(f.low), class: "whisker" }));
    s.append(svg("circle", { cx: X(h), cy: Y(f.value), r: 4.5, class: "fc" }));
  }
  return s;
}

/* ------------------------------------------------------------------ about */
(async function loadAbout() {
  try {
    const r = await fetch("/api/about");
    if (!r.ok) return;
    const j = await r.json();
    const ev = $("evidence"), lim = $("limits");
    for (const t of j.evidence) ev.append(el("li", { text: t }));
    for (const t of j.limits) lim.append(el("li", { text: t }));
    $("disclaimer").textContent = j.disclaimer;
    $("ver").textContent = j.model_version;
  } catch { /* the page still works without this */ }
})();
