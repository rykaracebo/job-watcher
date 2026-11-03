// The _tx sources are Texas-only copies of national boards, so one posting can
// appear under two sources with the same employer and the same source_id.
// Browse shows it once; the history file keeps both rows.
const TEXAS_COPY = /_tx$/;
const isTexasCopy = r => TEXAS_COPY.test(r.source);

// rows: open history rows. Returns one row per (employer, source_id) with:
//   first_seen  the earliest across the copies (the posting's real age)
//   location    the _tx copy's, when it has one
//   in_texas    true when a _tx copy is open (Workday says one location is in Texas,
//               even when the text only reads "5 Locations")
//   copy_ids    every posting_id the row stands for
function dedupePostings(rows) {
  const groups = new Map();
  for (const r of rows) {
    const key = r.employer + "\u0000" + r.source_id;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(r);
  }
  const out = [];
  for (const copies of groups.values()) {
    const ranked = [...copies].sort((a, b) =>
      a.first_seen.localeCompare(b.first_seen) || isTexasCopy(a) - isTexasCopy(b));
    const texas = copies.find(isTexasCopy);
    out.push({
      ...ranked[0],
      location: texas && texas.location ? texas.location : ranked[0].location,
      in_texas: Boolean(texas),
      copy_ids: copies.map(r => r.posting_id),
    });
  }
  return out;
}

// The shortlist stores posting_ids. A saved id of either copy counts, so a star
// set before de-duplication still shows on the merged row.
const isShortlisted = (row, stars) => row.copy_ids.some(id => stars.has(id));

function toggleShortlist(row, stars) {
  if (isShortlisted(row, stars)) row.copy_ids.forEach(id => stars.delete(id));
  else stars.add(row.posting_id);
}

if (typeof module !== "undefined") module.exports = { dedupePostings, isShortlisted, toggleShortlist };
