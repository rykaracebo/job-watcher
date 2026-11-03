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


class JsonSession:
    """Answers get/post with whatever `answer(kwargs)` returns."""

    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def _reply(self, kwargs):
        self.calls.append(kwargs)
        body = self.answer(kwargs)
        return type("R", (), {"raise_for_status": lambda s: None,
                              "json": lambda s: body})()

    def get(self, url, params=None, headers=None, timeout=None):
        return self._reply({"url": url, "params": params})

    def post(self, url, json=None, headers=None, timeout=None):
        return self._reply({"url": url, "json": json})


ORACLE = {"name": "o", "employer": "O", "ats": "oracle",
          "host": "o.fa.oraclecloud.com", "site": "CX_1", "search": "analyst"}


def oracle_answer(n):
    def answer(kw):
        finder = dict(p.split("=") for p in kw["params"]["finder"].split(";")[1].split(","))
        off, lim = int(finder["offset"]), int(finder["limit"])
        ids = range(off, min(off + lim, n))
        return {"items": [{"TotalJobsCount": n,
                           "requisitionList": [{"Id": str(i), "Title": f"J{i}"} for i in ids]}]}
    return answer


def test_oracle_pages_through_every_posting_with_the_search_term():
    session = JsonSession(oracle_answer(450))
    data = fetch.fetch_oracle(ORACLE, session)
    assert len(data["jobPostings"]) == 450 and data["total"] == 450
    assert "keyword=analyst" in session.calls[0]["params"]["finder"]
    assert "siteNumber=CX_1" in session.calls[0]["params"]["finder"]


def test_oracle_empty_board():
    assert fetch.fetch_oracle(ORACLE, JsonSession(oracle_answer(0)))["jobPostings"] == []


def test_greenhouse_returns_every_job():
    src = {"name": "g", "employer": "G", "ats": "greenhouse", "token": "tok"}
    session = JsonSession(lambda kw: {"jobs": [{"id": 1}, {"id": 2}]})
    data = fetch.fetch_greenhouse(src, session)
    assert data == {"total": 2, "jobPostings": [{"id": 1}, {"id": 2}]}
    assert session.calls[0]["url"].endswith("/boards/tok/jobs")


def goldman_answer(n):
    def answer(kw):
        page = kw["json"]["variables"]["searchQueryInput"]["page"]
        ids = range(page["pageNumber"] * page["pageSize"],
                    min((page["pageNumber"] + 1) * page["pageSize"], n))
        return {"data": {"roleSearch": {"totalCount": n,
                                        "items": [{"roleId": f"{i}_GS"} for i in ids]}}}
    return answer


def test_goldman_pages_until_empty():
    src = {"name": "gs", "employer": "GS", "ats": "goldman"}
    data = fetch.fetch_goldman(src, JsonSession(goldman_answer(250)))
    assert len(data["jobPostings"]) == 250 and data["total"] == 250


def test_goldman_graphql_error_fails_the_source():
    import pytest
    src = {"name": "gs", "employer": "GS", "ats": "goldman"}
    session = JsonSession(lambda kw: {"errors": [{"message": "Validation Exception."}]})
    with pytest.raises(ValueError, match="Validation Exception"):
        fetch.fetch_goldman(src, session)
