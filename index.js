const PAGE = 50;                        // postings drawn at a time per list
const $ = id => document.getElementById(id);
const state = { inRole: true, shown: { new: PAGE, removed: PAGE } };
let newRows = [], removedRows = [];

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

const isTexasCopy = name => /_tx$/.test(name);

function renderStats(status) {
  const tiles = [
    ["Days with a successful run", status.days_with_success, `since ${status.first_run_date}`],
    ["Open postings", status.open, "all sources, counted by source"],
    ["New today", status.new_today, "first run of a source not counted"],
    ["Removed today", status.removed_today, "no longer listed by their source"],
  ];
  $("stats").replaceChildren(...tiles.map(([label, value, note]) => {
    const t = el("div", "tile");
    t.append(el("div", "tile-label", label), el("div", "tile-value", value.toLocaleString()),
             el("div", "tile-note", note));
    return t;
  }));
}

function renderSources(status) {
  $("sources").replaceChildren(...status.sources.map(s => {
    const tr = el("tr");
    const name = el("td", "", s.name + (isTexasCopy(s.name) ? " (Texas copy)" : ""));
    const badge = el("span", "badge " + (s.ok ? "ok" : "fail"), s.ok ? "OK" : "Failed");
    const result = el("td");
    result.append(badge);
    if (!s.ok && s.error) result.append(el("span", "errtext", " " + s.error));
    tr.append(name, result, el("td", "num", s.count.toLocaleString()));
    return tr;
  }));
}

function posting(r) {
  const box = el("div", "change");
  const body = el("div");
  body.append(el("div", "title", r.title || "(no title)"));
  body.append(el("div", "meta",
    `${r.employer} · ${r.location || "Location not listed"} · ${r.source}`));
  box.append(body);
  if (/^https?:\/\//.test(r.url)) {
    const a = el("a", "apply", "Open");
    a.href = r.url;
    a.target = "_blank";
    a.rel = "noopener";
    box.append(a);
  }
  return box;
}

function renderList(kind, rows, heading) {
  const hits = state.inRole ? rows.filter(r => r.in_role === "true") : rows;
  $(kind + "Head").textContent = `${heading} (${rows.length.toLocaleString()})` +
    (state.inRole ? ` · ${hits.length.toLocaleString()} in my role` : "");
  const list = $(kind + "List");
  list.replaceChildren();
  if (!hits.length) {
    list.append(el("div", "empty", rows.length ? "None in your role." : "None in this run."));
  }
  for (const r of hits.slice(0, state.shown[kind])) list.append(posting(r));
  $(kind + "More").hidden = hits.length <= state.shown[kind];
}

function render() {
  renderList("new", newRows, "New postings");
  renderList("removed", removedRows, "Removed postings");
}

async function getJSON(url) {
  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) throw new Error(r.status);
  return r;
}

async function load() {
  try {
    const [csv, status] = await Promise.all([
      getJSON("data/history.csv").then(r => r.text()),
      getJSON("data/status.json").then(r => r.json()),
    ]);
    const date = status.run_time.slice(0, 10);
    const rows = parseCSV(csv);
    // Same definitions as status.json: new leaves out first-run postings.
    newRows = rows.filter(r => r.first_seen === date && r.first_run !== "true");
    removedRows = rows.filter(r => r.removed_date === date);

    const failed = status.sources.filter(s => !s.ok).length;
    $("asof").textContent = `Last run ${status.run_time.replace("T", " ").replace("Z", " UTC")}` +
      ` · ${status.sources.length - failed} of ${status.sources.length} sources OK`;
    renderStats(status);
    renderSources(status);

    const firstRuns = [...new Set(rows.filter(r => r.first_run === "true" && r.first_seen === date)
      .map(r => r.source))].sort();
    $("firstRunNote").textContent = firstRuns.length
      ? `First run today for ${firstRuns.join(", ")}: their postings were already open, so they are not counted as new.`
      : "";

    $("roleSwitch").addEventListener("click", e => {
      if (!e.target.dataset.role) return;
      state.inRole = e.target.dataset.role === "1";
      for (const b of $("roleSwitch").children) b.classList.toggle("on", b === e.target);
      state.shown = { new: PAGE, removed: PAGE };
      render();
    });
    $("newMore").onclick = () => { state.shown.new += PAGE; render(); };
    $("removedMore").onclick = () => { state.shown.removed += PAGE; render(); };
    render();
  } catch (err) {
    $("asof").textContent = "";
    $("stats").replaceChildren(el("div", "error", "Could not load the data files. Try reloading."));
  }
}

load();
