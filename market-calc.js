// Every number on the Market page comes from here, computed from the history rows.
// The definitions follow the assignment:
//   - first_run postings were already open when a source was first watched, so
//     their start date is unknown and they are left out where noted.
//   - Everything is counted by source row, as history.csv holds it. A Texas
//     copy (_tx source) of a posting is a second row.
const dayNumber = s => Date.parse(s + "T00:00:00Z") / 86400000;
const dateOf = n => new Date(n * 86400000).toISOString().slice(0, 10);
const PLACEHOLDER = /^\d+ locations?$/i;      // Workday: "5 Locations", no cities listed

function median(values) {
  if (!values.length) return null;
  const v = [...values].sort((a, b) => a - b);
  const mid = v.length >> 1;
  return v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2;
}

function countBy(rows, keyOf) {
  const m = new Map();
  for (const r of rows) m.set(keyOf(r), (m.get(keyOf(r)) || 0) + 1);
  return m;
}

function computeMarket(rows) {
  if (!rows.length) return null;
  let first = Infinity, last = -Infinity;
  for (const r of rows) {
    first = Math.min(first, dayNumber(r.first_seen));
    last = Math.max(last, dayNumber(r.last_seen));
  }
  const days = [];
  for (let d = first; d <= last; d++) days.push(dateOf(d));

  const isNew = r => r.first_run !== "true";
  const inRole = r => r.in_role === "true";
  const removedRows = rows.filter(r => r.removed_date !== "");
  const openRows = rows.filter(r => r.status === "open");

  // 1. New postings per day: first seen that day, first-run postings left out.
  const newRows = rows.filter(isNew);
  const newAll = countBy(newRows, r => r.first_seen);
  const newRole = countBy(newRows.filter(inRole), r => r.first_seen);
  // 2. Removed postings per day.
  const removed = countBy(removedRows, r => r.removed_date);

  // 3. Open postings per employer as of the last run.
  const byEmployer = new Map();
  for (const r of openRows) {
    const e = byEmployer.get(r.employer) || { employer: r.employer, open: 0, inRole: 0 };
    e.open++;
    if (inRole(r)) e.inRole++;
    byEmployer.set(r.employer, e);
  }
  const employers = [...byEmployer.values()]
    .sort((a, b) => b.open - a.open || a.employer.localeCompare(b.employer));

  // 4. Days open: removed postings that are not first-run, removed date minus first seen.
  const openDays = removedRows.filter(isNew)
    .map(r => dayNumber(r.removed_date) - dayNumber(r.first_seen));
  const daysOpenCounts = countBy(openDays.map(String), x => x);

  // 5. Share removed within seven days: not first-run, first seen at least seven days
  //    before the last run; the share with removed date minus first seen of 7 or fewer.
  const earliestNew = newRows.length ? newRows.reduce((m, r) => r.first_seen < m ? r.first_seen : m, "9999") : null;
  const eligible = newRows.filter(r => dayNumber(r.first_seen) <= last - 7);
  const quick = r => r.removed_date !== "" &&
    dayNumber(r.removed_date) - dayNumber(r.first_seen) <= 7;
  const cohorts = [...countBy(eligible, r => r.first_seen)].sort()
    .map(([date, n]) => ({ date, n, quick: eligible.filter(r => r.first_seen === date && quick(r)).length }));

  // 6. Top locations among open postings, exactly as listed.
  const locations = [...countBy(openRows, r => r.location)]
    .map(([location, count]) => ({ location, count }))
    .sort((a, b) => b.count - a.count || a.location.localeCompare(b.location));

  // When each source first ran, so jumps caused by adding a source can be marked.
  const firstRunDay = new Map();
  for (const r of rows) {
    if (r.first_run === "true" && (!firstRunDay.has(r.source) || r.first_seen < firstRunDay.get(r.source))) {
      firstRunDay.set(r.source, r.first_seen);
    }
  }
  const sourcesAdded = new Map();
  for (const [source, date] of [...firstRunDay].sort()) {
    if (!sourcesAdded.has(date)) sourcesAdded.set(date, []);
    sourcesAdded.get(date).push(source);
  }

  const get = (m, d) => m.get(d) || 0;
  return {
    firstDate: dateOf(first),
    lastDate: dateOf(last),
    days,
    newAll: days.map(d => get(newAll, d)),
    newRole: days.map(d => get(newRole, d)),
    removed: days.map(d => get(removed, d)),
    openTotal: openRows.length,
    employers,
    daysOpen: {
      n: openDays.length,
      median: median(openDays),
      counts: [...daysOpenCounts].map(([d, c]) => [Number(d), c]).sort((a, b) => a[0] - b[0]),
    },
    withinSeven: {
      earliestNew,
      eligible: eligible.length,
      quick: eligible.filter(quick).length,
      share: eligible.length ? eligible.filter(quick).length / eligible.length : null,
      cohorts,
    },
    locations,
    placeholderOpen: openRows.filter(r => PLACEHOLDER.test(r.location)).length,
    sourcesAdded: Object.fromEntries(sourcesAdded),
  };
}

if (typeof module !== "undefined") module.exports = { computeMarket, median, dayNumber, dateOf, PLACEHOLDER };
