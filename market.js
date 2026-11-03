// Market page: draws the six sections from computeMarket() (market-calc.js).
// Charts are plain SVG built here, so the page needs no library and works offline.
const NS = "http://www.w3.org/2000/svg";
const $ = id => document.getElementById(id);
const fmt = n => n.toLocaleString();
const dateLabel = iso => new Date(iso + "T00:00:00Z")
  .toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
const COLORS = { all: "var(--series-1)", role: "var(--series-2)" };

function h(tag, attrs = {}, text) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text !== undefined) e.textContent = text;
  return e;
}
function s(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.append(e);
  return e;
}
function text(parent, x, y, str, cls, anchor = "start") {
  const t = s("text", { x, y, class: cls, "text-anchor": anchor }, parent);
  t.textContent = str;
  return t;
}

// ---- tooltip: one element, value first, label second; also shown on keyboard focus ----
const tip = {
  el: null,
  show(target, value, label, extra) {
    const el = this.el || (this.el = $("tip"));
    el.replaceChildren(h("div", { class: "tip-value" }, value), h("div", { class: "tip-label" }, label));
    if (extra) el.append(h("div", { class: "tip-extra" }, extra));
    el.hidden = false;
    const r = target.getBoundingClientRect();
    const w = el.offsetWidth;
    el.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, r.left + r.width / 2 - w / 2)) + "px";
    el.style.top = Math.max(8, r.top - el.offsetHeight - 8) + "px";
  },
  hide() { if (this.el) this.el.hidden = true; },
};

function wireHit(rect, bar, value, label, extra) {
  const on = () => { bar && bar.classList.add("hot"); tip.show(rect, value, label, extra); };
  const off = () => { bar && bar.classList.remove("hot"); tip.hide(); };
  rect.addEventListener("pointerenter", on);
  rect.addEventListener("pointerleave", off);
  rect.addEventListener("focus", on);
  rect.addEventListener("blur", off);
}

// Top of the y axis: four whole-number steps (so counts never show 2.5).
function niceMax(v) {
  if (v <= 4) return 4;
  const raw = v / 4, pow = 10 ** Math.floor(Math.log10(raw));
  const steps = pow >= 10 ? [1, 2, 2.5, 5, 10] : [1, 2, 5, 10];
  return steps.find(m => m * pow >= raw) * pow * 4;
}

// Column with a square base and a 4px rounded top.
function columnPath(x, y, w, base) {
  const r = Math.min(4, w / 2, base - y);
  return `M${x},${base}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${base}Z`;
}

function empty(host, message) {
  host.replaceChildren(h("div", { class: "chart-empty" }, message));
}

// ---- column chart: one series per chart ----
// opts: labels[], values[], color, valueText(v), noun, markers {label: text}, percent
function columnChart(host, opts) {
  const { labels, values, color, markers = {}, percent = false } = opts;
  const W = Math.max(280, host.clientWidth || 600), H = 230;
  const m = { l: percent ? 44 : 40, r: 10, t: 18, b: 46 };
  const pw = W - m.l - m.r, ph = H - m.t - m.b, base = m.t + ph;
  const top = percent ? 1 : niceMax(Math.max(0, ...values));
  const y = v => base - (v / top) * ph;
  const tickText = v => percent ? Math.round(v * 100) + "%" : fmt(v);

  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img",
    "aria-label": opts.aria, class: "chart" });
  for (let i = 0; i <= 4; i++) {
    const v = (top / 4) * i, yy = y(v);
    s("line", { x1: m.l, x2: W - m.r, y1: yy, y2: yy, class: i ? "grid" : "axis" }, svg);
    text(svg, m.l - 6, yy + 4, tickText(v), "tick", "end");
  }
  const slot = pw / labels.length, bw = Math.min(24, slot * 0.7);
  const step = Math.max(1, Math.ceil(46 / slot));
  const peak = Math.max(...values), lastIdx = values.length - 1;

  labels.forEach((label, i) => {
    const cx = m.l + slot * i + slot / 2, x = cx - bw / 2, v = values[i];
    let bar = null;
    if (v > 0) bar = s("path", { d: columnPath(x, y(v), bw, base), fill: color, class: "bar" }, svg);
    if ((lastIdx - i) % step === 0) text(svg, cx, base + 16, dateLabelOr(label), "tick", "middle");
    if (markers[label]) {
      s("path", { d: `M${cx - 5},${base + 32}L${cx + 5},${base + 32}L${cx},${base + 24}Z`, class: "marker" }, svg);
    }
    // Label only the peak and the latest value; the tooltip and table carry the rest.
    if (v > 0 && (v === peak || i === lastIdx) && (i === lastIdx || values.indexOf(peak) === i)) {
      text(svg, cx, y(v) - 5, percent ? Math.round(v * 100) + "%" : fmt(v), "value", "middle");
    }
    const hit = s("rect", { x: m.l + slot * i, y: m.t, width: slot, height: ph + 22, fill: "transparent",
      tabindex: 0, role: "img", "aria-label": `${dateLabelOr(label)}: ${opts.valueText(v)}` }, svg);
    wireHit(hit, bar, opts.valueText(v), dateLabelOr(label), markers[label]);
  });
  host.replaceChildren(svg);
}
// Labels are ISO dates on the day charts and plain text ("3", "15+") on the histogram.
const dateLabelOr = l => /^\d{4}-\d{2}-\d{2}$/.test(l) ? dateLabel(l) : l;

// ---- horizontal bars: one hue, value at the tip ----
// items: [{ label, value, extra }]
function hbarChart(host, items, opts) {
  const W = Math.max(280, host.clientWidth || 600);
  const rowH = 28, barH = 16;
  const L = Math.min(210, Math.max(110, W * 0.38)), R = 54;
  const H = items.length * rowH + 8;
  const max = Math.max(1, ...items.map(i => i.value));
  const maxChars = Math.floor((L - 12) / 6.4);
  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img",
    "aria-label": opts.aria, class: "chart" });
  s("line", { x1: L, x2: L, y1: 0, y2: H - 4, class: "axis" }, svg);
  items.forEach((it, i) => {
    const y0 = i * rowH + 4, w = Math.max(2, ((W - L - R) * it.value) / max);
    const label = it.label.length > maxChars ? it.label.slice(0, maxChars - 1) + "…" : it.label;
    text(svg, L - 8, y0 + 16, label, "tick label", "end");
    // Square at the baseline, 4px rounded at the tip.
    const r = Math.min(4, w, barH / 2);
    const bar = s("path", { class: "bar", fill: opts.color,
      d: `M${L},${y0 + 2}H${L + w - r}Q${L + w},${y0 + 2} ${L + w},${y0 + 2 + r}V${y0 + 2 + barH - r}` +
         `Q${L + w},${y0 + 2 + barH} ${L + w - r},${y0 + 2 + barH}H${L}Z` }, svg);
    text(svg, L + w + 6, y0 + 15, fmt(it.value), "value", "start");
    const hit = s("rect", { x: 0, y: i * rowH, width: W, height: rowH, fill: "transparent", tabindex: 0,
      role: "img", "aria-label": `${it.label}: ${fmt(it.value)} ${opts.unit}` }, svg);
    wireHit(hit, bar, `${fmt(it.value)} ${opts.unit}`, it.label, it.extra);
  });
  host.replaceChildren(svg);
}

// ---- table view: every chart has one, so no value needs a tooltip ----
function tableView(host, headers, rows) {
  const old = host.querySelector("details.tableview");
  if (old) old.remove();
  const table = h("table");
  const head = h("tr");
  headers.forEach((t, i) => head.append(h("th", i ? { class: "num" } : {}, t)));
  const thead = h("thead");
  thead.append(head);
  table.append(thead);
  const body = h("tbody");
  for (const r of rows) {
    const tr = h("tr");
    r.forEach((c, i) => tr.append(h("td", i ? { class: "num" } : {}, String(c))));
    body.append(tr);
  }
  table.append(body);
  const d = h("details", { class: "tableview" });
  d.append(h("summary", {}, "View as a table"), h("div", { class: "table-wrap" }));
  d.lastChild.append(table);
  host.append(d);
}

const redraws = [];
const plural = (n, one, many) => `${fmt(n)} ${n === 1 ? one : many}`;
const sum = a => a.reduce((x, y) => x + y, 0);

function render(c) {
  const lastLabel = dateLabel(c.lastDate), nDays = c.days.length;
  $("asof").textContent = `Data through ${c.lastDate} UTC · ${plural(nDays, "day", "days")} of history · ` +
    "computed in your browser from data/history.csv";

  // Days a source first ran. Their postings are first-run, so they are not counted as new,
  // but open totals jump; the markers keep that from reading as market activity.
  const added = Object.entries(c.sourcesAdded);
  const markers = {};
  const box = $("timeline");
  box.replaceChildren(h("strong", {}, "When each source started"));
  const ul = h("ul");
  added.forEach(([date, names], i) => {
    const texas = names.filter(n => n.endsWith("_tx"));
    let line = `${dateLabel(date)}: ${i === 0 ? "watching began with " : ""}${plural(names.length, "source", "sources")} (${names.join(", ")})`;
    if (texas.length) line += ". The _tx sources are Texas-only copies of national boards, so their postings are also counted under the national source";
    ul.append(h("li", {}, line));
    markers[date] = `${plural(names.length, "source", "sources")} first ran this day: ${names.join(", ")}. ` +
      "Their existing postings are not counted as new, but open totals rise.";
  });
  box.append(ul, h("p", { class: "legendline" }, "▲ marks these days on the daily charts."));
  box.hidden = !added.length;

  // 1. New postings per day, two panels (the scales differ too much for one axis)
  const sumAll = sum(c.newAll), sumRole = sum(c.newRole);
  $("h1").textContent = `${fmt(sumAll)} new postings since watching began, ${fmt(sumRole)} in your role`;
  $("p1").textContent = "A posting is new on the day it is first seen. Postings that were already open when a " +
    "source was first watched (first-run postings) are left out because their start date is unknown, so the first day " +
    "always shows zero. The two panels use their own scales because your role is a small slice of the whole.";
  const c1 = $("c1");
  c1.replaceChildren();
  const panels = [["All postings", c.newAll, COLORS.all], ["In my role", c.newRole, COLORS.role]];
  const hosts1 = panels.map(([title, values, color]) => {
    const panel = h("div", { class: "panel" });
    const t = h("div", { class: "panel-title" });
    t.append(h("span", { class: "key", style: `background:${color}` }), h("span", {}, `${title} · ${fmt(sum(values))} total`));
    const chart = h("div");
    panel.append(t, chart);
    c1.append(panel);
    return { chart, title, values, color };
  });
  const draw1 = () => hosts1.forEach(({ chart, title, values, color }) => columnChart(chart, {
    labels: c.days, values, color, markers, aria: `New postings per day, ${title.toLowerCase()}`,
    valueText: v => `${fmt(v)} new`,
  }));
  draw1(); redraws.push(draw1);
  tableView(c1, ["Date", "New postings", "New in my role"], c.days.map((d, i) => [d, c.newAll[i], c.newRole[i]]));

  // 2. Removed postings per day
  const sumRemoved = sum(c.removed), lastRemoved = c.removed[nDays - 1];
  $("h2").textContent = `${fmt(sumRemoved)} postings have been removed, ${fmt(lastRemoved)} on ${lastLabel}`;
  $("p2").textContent = "A posting is removed on the day its source has a file and no longer lists it. " +
    "A posting that comes back is open again and drops out of these counts. Removals can only start on the second day.";
  const draw2 = () => columnChart($("c2"), { labels: c.days, values: c.removed, color: COLORS.all, markers,
    aria: "Removed postings per day", valueText: v => `${fmt(v)} removed` });
  draw2(); redraws.push(draw2);
  tableView($("c2"), ["Date", "Removed postings"], c.days.map((d, i) => [d, c.removed[i]]));

  // 3. Open postings per employer
  const top = c.employers[0];
  $("h3").textContent = top ? `${top.employer} has the most open postings: ${fmt(top.open)} of ${fmt(c.openTotal)}` : "No open postings";
  $("p3").textContent = `Open postings per employer as of ${lastLabel}, counted by source as the history file holds them. ` +
    (added.some(([, n]) => n.some(x => x.endsWith("_tx")))
      ? "Wells Fargo, Truist, Fidelity and Santander also have Texas-only copies, so a posting in Texas is counted under both. "
      : "") + "Hover or focus a bar to see how many are in your role.";
  const draw3 = () => hbarChart($("c3"), c.employers.map(e => ({
    label: e.employer, value: e.open, extra: `${fmt(e.inRole)} in my role`,
  })), { color: COLORS.all, unit: "open", aria: "Open postings per employer" });
  draw3(); redraws.push(draw3);
  tableView($("c3"), ["Employer", "Open postings", "In my role"], c.employers.map(e => [e.employer, e.open, e.inRole]));

  // 4. Days open
  const d4 = c.daysOpen;
  $("h4").textContent = d4.n ? `Removed postings were open a median of ${fmt(d4.median)} ${d4.median === 1 ? "day" : "days"}`
    : "No removed postings to measure yet";
  $("p4").textContent = "For removed postings that are not first-run postings: the removed date minus the first-seen date. " +
    `${fmt(d4.n)} postings qualify so far. The bars count postings by days open; 15 or more days share one bar.`;
  if (d4.n) {
    const cap = 15, cnt = new Map();
    for (const [d, n] of d4.counts) cnt.set(Math.min(d, cap), (cnt.get(Math.min(d, cap), 0) || 0) + n);
    const upto = Math.max(...cnt.keys());
    const labels = [], values = [];
    for (let d = 1; d <= upto; d++) { labels.push(d === cap ? `${cap}+` : String(d)); values.push(cnt.get(d) || 0); }
    const draw4 = () => columnChart($("c4"), { labels, values, color: COLORS.all, aria: "Removed postings by days open",
      valueText: v => `${fmt(v)} postings` });
    draw4(); redraws.push(draw4);
    tableView($("c4"), ["Days open", "Removed postings"], labels.map((l, i) => [l, values[i]]));
  } else empty($("c4"), "The chart appears once a posting that was not already open at the start has been removed.");

  // 5. Share removed within seven days
  const w = c.withinSeven;
  if (w.share === null) {
    $("h5").textContent = "Too early to say how many postings are removed within a week";
    const ready = w.earliestNew ? dateLabel(new Date(Date.parse(w.earliestNew + "T00:00:00Z") + 7 * 864e5).toISOString().slice(0, 10)) : null;
    $("p5").textContent = "Among postings that are not first-run postings and were first seen at least seven days before the " +
      "last run, this is the share removed within seven days of first being seen. " +
      (ready ? `The first postings qualify once the last run is ${ready} or later.` : "No qualifying postings yet.");
    empty($("c5"), "The chart appears once postings are old enough to qualify.");
  } else {
    $("h5").textContent = `${Math.round(w.share * 100)}% of postings were removed within seven days`;
    $("p5").textContent = `${fmt(w.quick)} of ${fmt(w.eligible)} postings that are not first-run postings and were first seen at least ` +
      "seven days before the last run were removed within seven days of first being seen. The bars show each first-seen day.";
    const labels = w.cohorts.map(x => x.date), values = w.cohorts.map(x => x.quick / x.n);
    const draw5 = () => columnChart($("c5"), { labels, values, color: COLORS.all, percent: true,
      aria: "Share removed within seven days, by first-seen day",
      valueText: v => `${Math.round(v * 100)}% removed within 7 days` });
    draw5(); redraws.push(draw5);
    tableView($("c5"), ["First seen", "Postings", "Removed within 7 days", "Share"],
      w.cohorts.map(x => [x.date, x.n, x.quick, `${Math.round((x.quick / x.n) * 100)}%`]));
  }

  // 6. Top locations (exactly as the source lists them)
  const real = c.locations.filter(l => !PLACEHOLDER.test(l.location) && l.location);
  const topLoc = real[0];
  $("h6").textContent = topLoc ? `${topLoc.location} has the most open postings: ${fmt(topLoc.count)}` : "No locations yet";
  $("p6").textContent = "Open postings by the location text each source gives, as listed. Workday shows postings with several " +
    `locations only as “N Locations”; ${fmt(c.placeholderOpen)} open postings read that way and are left out of the chart ` +
    "(they are in the table). The same city can appear under more than one spelling.";
  const draw6 = () => hbarChart($("c6"), real.slice(0, 12).map(l => ({ label: l.location, value: l.count })),
    { color: COLORS.all, unit: "open", aria: "Top locations among open postings" });
  draw6(); redraws.push(draw6);
  tableView($("c6"), ["Location", "Open postings"], c.locations.slice(0, 25).map(l => [l.location || "(not listed)", l.count]));
}

async function load() {
  try {
    const res = await fetch("data/history.csv", { cache: "no-cache" });
    if (!res.ok) throw new Error(res.status);
    const calc = computeMarket(parseCSV(await res.text()));
    if (!calc) throw new Error("empty history");
    render(calc);
    let timer;
    window.addEventListener("resize", () => { clearTimeout(timer); timer = setTimeout(() => redraws.forEach(f => f()), 150); });
  } catch (err) {
    $("asof").textContent = "";
    $("s1").replaceChildren(h("div", { class: "error" }, "Could not load the data file. Try reloading."));
  }
}

load();
