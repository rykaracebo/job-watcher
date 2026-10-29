import gzip
import json

from pipeline.build import build_history, replay, write_history

A = {"name": "a", "employer": "A Bank", "ats": "workday",
     "host": "a.wd1", "tenant": "a", "site": "Careers"}
B = dict(A, name="b", employer="B Bank", host="b.wd1", tenant="b")
SOURCES = {"a": A, "b": B}


def raw(*ids, title="Credit Analyst"):
    return {"jobPostings": [
        {"title": title, "externalPath": f"/job/X/Job_{i}", "locationsText": "DALLAS, TX"}
        for i in ids]}


def run(days):
    return replay(days, SOURCES)


def test_first_seen_and_last_seen():
    h = run([("2026-10-01", "a", raw("1")),
             ("2026-10-02", "a", raw("1", "2")),
             ("2026-10-03", "a", raw("1", "2"))])
    assert (h["a:1"]["first_seen"], h["a:1"]["last_seen"]) == ("2026-10-01", "2026-10-03")
    assert (h["a:2"]["first_seen"], h["a:2"]["last_seen"]) == ("2026-10-02", "2026-10-03")
    assert h["a:1"]["status"] == "open" and h["a:1"]["removed_date"] == ""


def test_first_run_flag_only_on_the_sources_first_file():
    h = run([("2026-10-01", "a", raw("1")),
             ("2026-10-02", "a", raw("1", "2")),
             ("2026-10-02", "b", raw("9"))])
    assert h["a:1"]["first_run"] is True
    assert h["a:2"]["first_run"] is False
    assert h["b:9"]["first_run"] is True      # b's own first file, not a's


def test_removed_when_source_has_a_file_and_no_longer_lists_it():
    h = run([("2026-10-01", "a", raw("1", "2")),
             ("2026-10-02", "a", raw("1"))])
    assert h["a:2"]["status"] == "removed"
    assert h["a:2"]["removed_date"] == "2026-10-02"
    assert h["a:2"]["last_seen"] == "2026-10-01"
    assert h["a:1"]["status"] == "open"


def test_failed_source_day_removes_nothing():
    # No raw file for source a on 10-02 (the fetch failed), only b has one.
    h = run([("2026-10-01", "a", raw("1")),
             ("2026-10-02", "b", raw("9"))])
    assert h["a:1"]["status"] == "open"
    assert h["a:1"]["last_seen"] == "2026-10-01"


def test_removal_is_per_source():
    h = run([("2026-10-01", "a", raw("1")), ("2026-10-01", "b", raw("9")),
             ("2026-10-02", "a", raw("1"))])
    assert h["b:9"]["status"] == "open"


def test_removed_posting_listed_again_reopens():
    h = run([("2026-10-01", "a", raw("1")),
             ("2026-10-02", "a", raw()),
             ("2026-10-03", "a", raw("1"))])
    row = h["a:1"]
    assert row["status"] == "open"
    assert row["removed_date"] == ""
    assert row["first_seen"] == "2026-10-01"
    assert row["last_seen"] == "2026-10-03"


def test_keeps_postings_outside_the_role(tmp_path):
    write_raw(tmp_path, "2026-10-01", "a", raw("1", title="Software Engineer"))
    rows = build_history(tmp_path, SOURCES)
    assert len(rows) == 1 and rows[0]["in_role"] is False


def write_raw(root, date, name, data):
    path = root / date / f"{name}.json.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as f:
        json.dump(data, f)


def test_rows_sorted_by_posting_id_and_rebuild_is_identical(tmp_path):
    write_raw(tmp_path, "2026-10-01", "b", raw("9", "3"))
    write_raw(tmp_path, "2026-10-01", "a", raw("2", "1"))
    write_raw(tmp_path, "2026-10-02", "a", raw("1"))

    rows = build_history(tmp_path, SOURCES)
    assert [r["posting_id"] for r in rows] == ["a:1", "a:2", "b:3", "b:9"]

    first, second = tmp_path / "h1.csv", tmp_path / "h2.csv"
    write_history(rows, first)
    write_history(build_history(tmp_path, SOURCES), second)
    assert first.read_bytes() == second.read_bytes()
    assert "true" in first.read_text() and "True" not in first.read_text()


def test_rule_change_applies_to_every_day(tmp_path, monkeypatch):
    write_raw(tmp_path, "2026-10-01", "a", raw("1", title="Treasury Clerk"))
    assert build_history(tmp_path, SOURCES)[0]["in_role"] is False
    monkeypatch.setattr("pipeline.build.in_role", lambda title: True)
    assert build_history(tmp_path, SOURCES)[0]["in_role"] is True
