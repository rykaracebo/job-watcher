"""The Market page numbers must follow the assignment's definitions and agree with history.csv.

market-calc.js is run under node (the same file the page loads). An independent Python
version of each definition is the oracle, and status.json is a second cross-check.
"""
import csv
import json
import shutil
import statistics
import subprocess
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
ROOT = Path(__file__).resolve().parent.parent

NODE = """
const vm = require('vm'), fs = require('fs');
vm.runInThisContext(fs.readFileSync('csv.js', 'utf8'));
const { computeMarket } = require('./market-calc.js');
const rows = process.argv[1] === 'FILE' ? parseCSV(fs.readFileSync('data/history.csv', 'utf8'))
                                        : JSON.parse(fs.readFileSync(0, 'utf8'));
console.log(JSON.stringify(computeMarket(rows)));
"""


def market(rows=None):
    arg = "FILE" if rows is None else "STDIN"
    out = subprocess.run(["node", "-e", NODE, arg], cwd=ROOT, capture_output=True, text=True, check=True,
                         input=None if rows is None else json.dumps(rows))
    return json.loads(out.stdout)


def row(source="a", source_id="1", employer="A", location="Dallas, TX", in_role="false",
        first_run="false", first_seen="2026-10-01", last_seen="2026-10-10", removed_date="", **kw):
    r = {"posting_id": f"{source}:{source_id}", "source": source, "source_id": source_id,
         "employer": employer, "location": location, "in_role": in_role, "first_run": first_run,
         "first_seen": first_seen, "last_seen": last_seen, "removed_date": removed_date,
         "status": "removed" if removed_date else "open", "title": "T"}
    r.update(kw)
    return r


# ---------------- independent oracle, straight from the assignment text ----------------

def d(s):
    return date.fromisoformat(s)


def oracle(rows):
    last = max(d(r["last_seen"]) for r in rows)
    first = min(d(r["first_seen"]) for r in rows)
    days = [(first + timedelta(n)).isoformat() for n in range((last - first).days + 1)]
    not_first_run = [r for r in rows if r["first_run"] != "true"]
    new_all = Counter(r["first_seen"] for r in not_first_run)
    new_role = Counter(r["first_seen"] for r in not_first_run if r["in_role"] == "true")
    removed = Counter(r["removed_date"] for r in rows if r["removed_date"])
    open_rows = [r for r in rows if r["status"] == "open"]
    gaps = [(d(r["removed_date"]) - d(r["first_seen"])).days
            for r in not_first_run if r["removed_date"]]
    eligible = [r for r in not_first_run if (last - d(r["first_seen"])).days >= 7]
    quick = [r for r in eligible if r["removed_date"] and (d(r["removed_date"]) - d(r["first_seen"])).days <= 7]
    return {
        "days": days,
        "newAll": [new_all[x] for x in days], "newRole": [new_role[x] for x in days],
        "removed": [removed[x] for x in days],
        "employers": dict(Counter(r["employer"] for r in open_rows)),
        "gaps": sorted(gaps), "median": statistics.median(gaps) if gaps else None,
        "eligible": len(eligible), "quick": len(quick),
        "locations": dict(Counter(r["location"] for r in open_rows)),
        "open": len(open_rows), "last": last.isoformat(),
    }


def check_against_oracle(rows):
    got, want = market(rows), oracle(rows)
    assert got["days"] == want["days"]
    assert got["newAll"] == want["newAll"] and got["newRole"] == want["newRole"]
    assert got["removed"] == want["removed"]
    assert {e["employer"]: e["open"] for e in got["employers"]} == want["employers"]
    assert got["openTotal"] == want["open"] and got["lastDate"] == want["last"]
    assert got["daysOpen"]["n"] == len(want["gaps"]) and got["daysOpen"]["median"] == want["median"]
    hist = sorted(d_ for d_, c in got["daysOpen"]["counts"] for _ in range(c))
    assert hist == want["gaps"]
    assert (got["withinSeven"]["eligible"], got["withinSeven"]["quick"]) == (want["eligible"], want["quick"])
    assert {l["location"]: l["count"] for l in got["locations"]} == want["locations"]


# ---------------- the real history file ----------------

@pytest.fixture(scope="module")
def real_rows():
    with open(ROOT / "data" / "history.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_every_number_matches_the_real_history_file(real_rows):
    check_against_oracle(real_rows)


def test_page_agrees_with_status_json(real_rows):
    got = market()
    status = json.loads((ROOT / "data" / "status.json").read_text())
    assert got["openTotal"] == status["open"]
    assert got["lastDate"] == status["run_time"][:10]
    assert got["newAll"][-1] == status["new_today"]
    assert got["removed"][-1] == status["removed_today"]
    assert len(got["days"]) >= status["days_with_success"]


def test_the_page_parses_the_csv_the_same_way_python_does(real_rows):
    got = market()
    assert sum(e["open"] for e in got["employers"]) == sum(r["status"] == "open" for r in real_rows)
    assert sum(l["count"] for l in got["locations"]) == got["openTotal"]


# ---------------- the definitions, on small hand-made histories ----------------

def test_first_run_postings_are_left_out_of_new_but_not_out_of_open():
    got = market([row("a", "1", first_run="true", first_seen="2026-10-01"),
                  row("a", "2", first_seen="2026-10-02")])
    assert got["newAll"][:2] == [0, 1]
    assert got["openTotal"] == 2


def test_new_in_role_is_a_subset_of_new():
    got = market([row("a", "1", first_seen="2026-10-02", in_role="true"),
                  row("a", "2", first_seen="2026-10-02")])
    assert (got["newAll"][0], got["newRole"][0]) == (2, 1)


def test_removed_per_day_counts_removed_dates_including_first_run_postings():
    got = market([row("a", "1", first_run="true", removed_date="2026-10-03"),
                  row("a", "2", removed_date="2026-10-03"), row("a", "3")])
    assert got["removed"][2] == 2


def test_a_posting_that_returned_has_no_removed_date_and_is_open():
    got = market([row("a", "1", removed_date="")])      # reopened: removed_date cleared
    assert sum(got["removed"]) == 0 and got["openTotal"] == 1


def test_median_of_an_even_count_is_the_average_of_the_middle_two():
    rows = [row("a", str(i), first_seen="2026-10-01", removed_date=f"2026-10-0{1 + g}")
            for i, g in enumerate([1, 2, 3, 6])]
    assert market(rows)["daysOpen"]["median"] == 2.5


def test_days_open_leaves_out_first_run_postings():
    got = market([row("a", "1", first_run="true", removed_date="2026-10-09"),
                  row("a", "2", first_seen="2026-10-01", removed_date="2026-10-03")])
    assert got["daysOpen"]["n"] == 1 and got["daysOpen"]["median"] == 2


def test_no_removals_gives_no_median():
    assert market([row("a", "1")])["daysOpen"]["median"] is None


def test_share_removed_within_seven_days_uses_only_postings_old_enough():
    last = "2026-10-20"
    rows = [
        row("a", "1", first_seen="2026-10-01", last_seen=last, removed_date="2026-10-04"),   # 3 days: yes
        row("a", "2", first_seen="2026-10-01", last_seen=last, removed_date="2026-10-08"),   # 7 days: yes
        row("a", "3", first_seen="2026-10-01", last_seen=last, removed_date="2026-10-09"),   # 8 days: no
        row("a", "4", first_seen="2026-10-02", last_seen=last),                              # still open: no
        row("a", "5", first_seen="2026-10-13", last_seen=last, removed_date="2026-10-14"),   # exactly 7 days old: counted
        row("a", "6", first_seen="2026-10-14", last_seen=last, removed_date="2026-10-15"),   # too recent: left out
        row("a", "7", first_seen="2026-10-01", last_seen=last, first_run="true"),            # first run: left out
    ]
    w = market(rows)["withinSeven"]
    assert (w["eligible"], w["quick"]) == (5, 3)
    assert w["share"] == 0.6


def test_share_is_null_when_nothing_is_old_enough():
    assert market([row("a", "1", first_seen="2026-10-09", last_seen="2026-10-10")])["withinSeven"]["share"] is None


def test_top_locations_count_open_postings_by_the_listed_text():
    rows = [row("a", "1", location="Dallas, TX"), row("a", "2", location="Dallas, TX"),
            row("a", "3", location="2 Locations"), row("a", "4", location="Plano, TX", removed_date="2026-10-05")]
    got = market(rows)
    assert {l["location"]: l["count"] for l in got["locations"]} == {"Dallas, TX": 2, "2 Locations": 1}
    assert got["placeholderOpen"] == 1


def test_a_posting_under_two_sources_is_counted_once_per_source():
    rows = [row("wells_fargo", "R-1", employer="Wells Fargo"),
            row("wells_fargo_tx", "R-1", employer="Wells Fargo")]
    got = market(rows)
    assert got["openTotal"] == 2 and got["employers"][0]["open"] == 2


def test_the_day_each_source_first_ran_is_reported_for_the_markers():
    rows = [row("a", "1", first_run="true", first_seen="2026-10-01"),
            row("b", "1", first_run="true", first_seen="2026-10-05", last_seen="2026-10-10"),
            row("b_tx", "1", first_run="true", first_seen="2026-10-05"),
            row("a", "2", first_seen="2026-10-03")]
    assert market(rows)["sourcesAdded"] == {"2026-10-01": ["a"], "2026-10-05": ["b", "b_tx"]}


def test_empty_history_gives_no_market():
    assert market([]) is None
