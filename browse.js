const PAGE = 200;                       // postings drawn at a time
const STAR_KEY = "jobwatcher.shortlist";

// Location text differs by employer: "Plano, TX", "Irving Texas United States", "Dallas".
const DFW_CITIES = /\b(dallas|fort worth|irving|plano|frisco|addison|richardson|westlake|las colinas|southlake|arlington|garland|mckinney|allen|lewisville|carrollton|coppell|grapevine|denton|dfw)\b/i;
const TEXAS = /(,\s*tx\b|\btexas\b|\btx\b)/i;

const isTexas = loc => TEXAS.test(loc);
// A DFW city name must come with Texas, or with no state at all ("Dallas").
// "Arlington, VA" and "Addison, Illinois" have a state part and are not Dallas.
const isDFW = loc => DFW_CITIES.test(loc) && (TEXAS.test(loc) || !loc.includes(","));

const $ = id => document.getElementById(id);
const state = { inRole: true, quick: "", shown: PAGE };
let rows = [], lastRun = "", stars = loadStars();

function loadStars() {
  try { return new Set(JSON.parse(localStorage.getItem(STAR_KEY) || "[]")); }
  catch { return new Set(); }
}
function saveStars() {
  try { localStorage.setItem(STAR_KEY, JSON.stringify([...stars])); } catch { /* storage blocked */ }
}

const dayNumber = s => Date.parse(s + "T00:00:00Z") / 86400000;
// Days open = last run date minus first-seen date. For postings already open
// when watching began, this counts from the day we started watching.
const daysOpen = r => Math.max(0, dayNumber(lastRun) - dayNumber(r.first_seen));

function matches(r) {
  if (state.inRole && r.in_role !== "true") return false;
  if ($("starredOnly").checked && !stars.has(r.posting_id)) return false;
  const q = $("q").value.trim().toLowerCase();
  if (q && !r.title.toLowerCase().includes(q)) return false;
  if ($("employer").value && r.employer !== $("employer").value) return false;
  const loc = $("loc").value.trim().toLowerCase();
  if (loc && !r.location.toLowerCase().includes(loc)) return false;
  if (state.quick === "dfw" && !isDFW(r.location)) return false;
  if (state.quick === "tx" && !isTexas(r.location)) return false;
  const maxDays = $("days").value;
  if (maxDays && daysOpen(r) > Number(maxDays)) return false;
  return true;
}

function render() {
  const sign = $("sort").value === "old" ? 1 : -1;
  const hits = rows.filter(matches).sort((a, b) =>
    sign * a.first_seen.localeCompare(b.first_seen) || a.title.localeCompare(b.title));

  $("count").textContent = `${hits.length.toLocaleString()} posting${hits.length === 1 ? "" : "s"}`;
  $("starCount").textContent = stars.size;

  const list = $("list");
  list.replaceChildren();
  if (!hits.length) {
    list.append(el("div", "empty", "No postings match these filters."));
  }
  for (const r of hits.slice(0, state.shown)) list.append(card(r));
  $("more").hidden = hits.length <= state.shown;
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function card(r) {
  const box = el("div", "posting");

  const star = el("button", "star" + (stars.has(r.posting_id) ? " on" : ""), "★");
  star.title = "Save to shortlist";
  star.setAttribute("aria-pressed", stars.has(r.posting_id));
  star.onclick = () => {
    stars.has(r.posting_id) ? stars.delete(r.posting_id) : stars.add(r.posting_id);
    saveStars();
    render();
  };

  const body = el("div");
  body.append(el("div", "title", r.title || "(no title)"));
  const d = daysOpen(r);
  body.append(el("div", "meta",
    `${r.employer} · ${r.location || "Location not listed"} · first seen ${r.first_seen}` +
    ` · ${d} day${d === 1 ? "" : "s"} open`));

  box.append(star, body);
  if (/^https?:\/\//.test(r.url)) {
    const a = el("a", "apply", "Apply");
    a.href = r.url;
    a.target = "_blank";
    a.rel = "noopener";
    box.append(a);
  }
  return box;
}

function bind() {
  const rerender = () => { state.shown = PAGE; render(); };
  for (const id of ["q", "employer", "loc", "days", "sort", "starredOnly"]) {
    $(id).addEventListener("input", rerender);
  }
  $("roleSwitch").addEventListener("click", e => {
    if (!e.target.dataset.role) return;
    state.inRole = e.target.dataset.role === "1";
    for (const b of $("roleSwitch").children) b.classList.toggle("on", b === e.target);
    rerender();
  });
  $("quickLoc").addEventListener("click", e => {
    if (e.target.dataset.loc === undefined) return;
    state.quick = e.target.dataset.loc;
    for (const b of $("quickLoc").children) b.classList.toggle("on", b === e.target);
    rerender();
  });
  $("more").onclick = () => { state.shown += PAGE; render(); };
}

async function load() {
  try {
    const [csv, status] = await Promise.all([
      fetch("data/history.csv", { cache: "no-cache" }).then(r => { if (!r.ok) throw new Error(r.status); return r.text(); }),
      fetch("data/status.json", { cache: "no-cache" }).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }),
    ]);
    rows = parseCSV(csv).filter(r => r.status === "open");
    lastRun = status.run_time.slice(0, 10);
    const failed = status.sources.filter(s => !s.ok).length;
    $("asof").textContent = `Last run ${status.run_time.replace("T", " ").replace("Z", " UTC")} · ` +
      `${status.open.toLocaleString()} open postings` + (failed ? ` · ${failed} source(s) failed` : "");

    const employers = [...new Set(rows.map(r => r.employer))].sort();
    for (const name of employers) $("employer").append(new Option(name, name));
    bind();
    render();
  } catch (err) {
    $("asof").textContent = "";
    $("list").replaceChildren(el("div", "error", "Could not load the data files. Try reloading."));
  }
}

load();
