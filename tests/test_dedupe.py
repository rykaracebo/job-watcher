"""Tests for dedupe.js (Browse page). Runs the real file under node."""
import json
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def node(expr, **data):
    script = ("const d = require('./dedupe.js'); const input = JSON.parse(process.argv[1]);"
              f"console.log(JSON.stringify({expr}));")
    out = subprocess.run(["node", "-e", script, json.dumps(data)],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def row(source, source_id="R-1", employer="Wells Fargo", location="5 Locations",
        first_seen="2026-10-29"):
    return {"posting_id": f"{source}:{source_id}", "source": source, "source_id": source_id,
            "employer": employer, "location": location, "first_seen": first_seen,
            "title": "Credit Analyst"}


def dedupe(*rows):
    return node("d.dedupePostings(input.rows)", rows=list(rows))


def test_a_posting_in_both_sources_is_shown_once():
    out = dedupe(row("wells_fargo"), row("wells_fargo_tx", first_seen="2026-11-04"))
    assert len(out) == 1
    assert out[0]["copy_ids"] == ["wells_fargo:R-1", "wells_fargo_tx:R-1"]
    assert out[0]["in_texas"] is True


def test_keeps_the_earliest_first_seen_date():
    out = dedupe(row("wells_fargo_tx", first_seen="2026-11-04"), row("wells_fargo"))
    assert out[0]["first_seen"] == "2026-10-29"
    assert out[0]["posting_id"] == "wells_fargo:R-1"


def test_prefers_the_texas_copys_location_on_conflict():
    out = dedupe(row("wells_fargo", location="DALLAS, TX / NEW YORK, NY"),
                 row("wells_fargo_tx", location="DALLAS, TX"))
    assert out[0]["location"] == "DALLAS, TX"


def test_an_empty_texas_location_does_not_erase_the_national_one():
    out = dedupe(row("wells_fargo", location="DALLAS, TX"), row("wells_fargo_tx", location=""))
    assert out[0]["location"] == "DALLAS, TX"


def test_a_posting_with_no_texas_copy_is_unchanged_and_not_in_texas():
    out = dedupe(row("wells_fargo", location="NEW YORK, NY"))
    assert out[0]["location"] == "NEW YORK, NY"
    assert out[0]["in_texas"] is False and out[0]["copy_ids"] == ["wells_fargo:R-1"]


def test_a_posting_only_in_the_texas_source_is_kept():
    out = dedupe(row("truist_tx", employer="Truist", location="Plano, TX"))
    assert len(out) == 1 and out[0]["in_texas"] is True


def test_same_id_at_different_employers_stays_separate():
    out = dedupe(row("wells_fargo", source_id="R-1"), row("truist", source_id="R-1", employer="Truist"))
    assert len(out) == 2


def test_different_ids_at_one_employer_stay_separate():
    out = dedupe(row("wells_fargo", source_id="R-1"), row("wells_fargo", source_id="R-2"))
    assert len(out) == 2


def test_a_star_saved_on_either_copy_shows_on_the_merged_row():
    for saved in ("wells_fargo:R-1", "wells_fargo_tx:R-1"):
        assert node("d.isShortlisted(d.dedupePostings(input.rows)[0], new Set(input.stars))",
                    rows=[row("wells_fargo"), row("wells_fargo_tx")], stars=[saved]) is True
    assert node("d.isShortlisted(d.dedupePostings(input.rows)[0], new Set(input.stars))",
                rows=[row("wells_fargo"), row("wells_fargo_tx")], stars=["other:R-9"]) is False


def test_unstarring_clears_every_copy_and_starring_saves_one_id():
    expr = ("(() => { const r = d.dedupePostings(input.rows)[0]; const s = new Set(input.stars);"
            "d.toggleShortlist(r, s); return [...s]; })()")
    rows = [row("wells_fargo"), row("wells_fargo_tx")]
    assert node(expr, rows=rows, stars=["wells_fargo:R-1", "wells_fargo_tx:R-1", "keep:1"]) == ["keep:1"]
    assert node(expr, rows=rows, stars=[]) == ["wells_fargo:R-1"]
