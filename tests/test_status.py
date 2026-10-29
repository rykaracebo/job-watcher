import gzip

from pipeline.status import build_status


def touch_raw(root, date, name="a"):
    path = root / date / f"{name}.json.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as f:
        f.write("{}")


def row(**kw):
    base = {"status": "open", "first_seen": "2026-10-01", "first_run": False,
            "removed_date": ""}
    return dict(base, **kw)


def test_counts_follow_the_definitions(tmp_path):
    touch_raw(tmp_path, "2026-10-01")
    touch_raw(tmp_path, "2026-10-03")
    rows = [
        row(),                                                    # old, open
        row(first_seen="2026-10-03"),                             # new today
        row(first_seen="2026-10-03", first_run=True),             # first run: not new
        row(status="removed", removed_date="2026-10-03"),         # removed today
        row(status="removed", removed_date="2026-10-02"),         # removed earlier
    ]
    results = [{"name": "a", "ok": True, "count": 3},
               {"name": "b", "ok": False, "count": 0, "error": "boom"}]
    s = build_status(rows, results, "2026-10-03T06:00:00Z", "2026-10-03", tmp_path)

    assert s["first_run_date"] == "2026-10-01"
    assert s["days_with_success"] == 2
    assert s["open"] == 3
    assert s["new_today"] == 1
    assert s["removed_today"] == 1
    assert s["sources"] == results


def test_no_raw_folder_yet(tmp_path):
    s = build_status([], [], "t", "2026-10-01", tmp_path / "missing")
    assert (s["first_run_date"], s["days_with_success"]) == ("", 0)


def test_day_with_no_raw_file_does_not_count(tmp_path):
    touch_raw(tmp_path, "2026-10-01")
    (tmp_path / "2026-10-02").mkdir()          # every source failed that day
    s = build_status([], [], "t", "2026-10-02", tmp_path)
    assert s["days_with_success"] == 1
