import gzip
import json

from pipeline import fetch
from pipeline.fetch import _find_state_facet, fetch_all, fetch_workday

SOURCE = {"name": "x", "employer": "X", "ats": "workday",
          "host": "x.wd1", "tenant": "x", "site": "Careers"}


def posting(n):
    return {"title": f"Job {n}", "externalPath": f"/job/A/Job-{n}_R-{n}"}


class FakeSession:
    """Serves a board of `n` postings in pages like Workday does."""

    def __init__(self, n, wrap_at=None):
        self.n, self.wrap_at, self.calls = n, wrap_at, 0

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls += 1
        offset = json["offset"]
        if self.wrap_at is not None and offset >= self.wrap_at:
            offset -= self.wrap_at          # Workday wraps back to page one
        ids = range(offset, min(offset + json["limit"], self.n))
        body = {"total": self.n, "jobPostings": [posting(i) for i in ids]}
        return type("R", (), {"raise_for_status": lambda s: None,
                              "json": lambda s: body})()


def test_fetches_every_page_until_empty():
    data = fetch_workday(SOURCE, FakeSession(45))
    assert len(data["jobPostings"]) == 45
    assert data["total"] == 45


def test_stops_when_workday_wraps_to_page_one():
    data = fetch_workday(SOURCE, FakeSession(10_000, wrap_at=60))
    assert len(data["jobPostings"]) == 60


def test_state_facet_nested_under_group():
    facets = [{"facetParameter": "locationMainGroup", "values": [
        {"facetParameter": "locationRegionStateProvince", "descriptor": "State",
         "values": [{"descriptor": "Texas", "id": "tx1"}]}]}]
    assert _find_state_facet(facets, "Texas") == {
        "locationRegionStateProvince": ["tx1"]}


def test_state_facet_at_top_level():
    facets = [{"facetParameter": "State_or_Province",
               "values": [{"descriptor": "Texas", "id": "tx2"}]}]
    assert _find_state_facet(facets, "Texas") == {"State_or_Province": ["tx2"]}


def test_failed_source_is_recorded_and_does_not_stop_the_run(tmp_path, monkeypatch):
    def fake_fetch(source, session):
        if source["name"] == "bad":
            raise RuntimeError("blocked")
        return {"total": 1, "jobPostings": [posting(1)]}

    monkeypatch.setitem(fetch.FETCHERS, "workday", fake_fetch)
    sources = [dict(SOURCE, name="bad"), dict(SOURCE, name="good")]
    results = fetch_all(sources, "2026-10-29", tmp_path)

    assert [(r["name"], r["ok"], r["count"]) for r in results] == [
        ("bad", False, 0), ("good", True, 1)]
    assert "blocked" in results[0]["error"]
    assert not (tmp_path / "2026-10-29" / "bad.json.gz").exists()
    with gzip.open(tmp_path / "2026-10-29" / "good.json.gz", "rt") as f:
        assert json.load(f)["jobPostings"] == [posting(1)]
