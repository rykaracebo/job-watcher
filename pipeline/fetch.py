"""Fetch every source and save what it returns to data/raw/<date>/<source>.json.gz.

One source failing never stops the run: it is recorded as ok=False and writes
no raw file that day.
"""
import gzip
import json
import time
from pathlib import Path

import requests

PAGE_SIZE = 20          # Workday rejects larger pages
MAX_PAGES = 600         # safety stop (12,000 postings)
RETRIES = 3
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "job-watcher/1.0 (personal job-search project)",
}


def _request(send, *args, **kwargs):
    for attempt in range(RETRIES):
        try:
            r = send(*args, headers=HEADERS, timeout=30, **kwargs)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if attempt == RETRIES - 1:
                raise
            time.sleep(2 ** attempt)


def _post(session, url, body):
    return _request(session.post, url, json=body)


def _get(session, url, params=None):
    return _request(session.get, url, params=params)


STATE_FACETS = {"locationRegionStateProvince", "State_or_Province"}


def _find_state_facet(facets, state):
    """Walk the facet tree for a state facet value, e.g. Texas.

    Tenants differ: Wells Fargo nests it under locationMainGroup, Citi lists
    State_or_Province at the top level.
    """
    for facet in facets:
        if facet.get("facetParameter") in STATE_FACETS:
            for v in facet.get("values", []):
                if v.get("descriptor") == state:
                    return {facet["facetParameter"]: [v["id"]]}
        found = _find_state_facet(
            [v for v in facet.get("values", []) if "facetParameter" in v], state)
        if found:
            return found
    return None


def _state_facet(first_page, state):
    found = _find_state_facet(first_page.get("facets", []), state)
    if not found:
        raise ValueError(f"State facet {state!r} not found")
    return found


def fetch_workday(source, session):
    url = (f"https://{source['host']}.myworkdayjobs.com/wday/cxs/"
           f"{source['tenant']}/{source['site']}/jobs")
    search = source.get("search", "")
    facets = {}
    if source.get("state"):
        probe = _post(session, url, {"appliedFacets": {}, "limit": 1, "offset": 0,
                                     "searchText": search})
        facets = _state_facet(probe, source["state"])

    postings, seen, total = [], set(), None
    for page in range(MAX_PAGES):
        data = _post(session, url, {"appliedFacets": facets, "limit": PAGE_SIZE,
                                    "offset": page * PAGE_SIZE, "searchText": search})
        total = data.get("total", total)
        batch = data.get("jobPostings", [])
        # Skip entries without a path: no way to build an id or link for them.
        new = [p for p in batch
               if p.get("externalPath") and p["externalPath"] not in seen]
        # Empty page = end of board. No new postings = Workday wrapped past
        # its ~2,000-result window back to page one.
        if not new:
            break
        seen.update(p["externalPath"] for p in new)
        postings.extend(new)
    return {"total": total, "jobPostings": postings}


ORACLE_PAGE = 200       # Oracle accepts up to 200 per page


def fetch_oracle(source, session):
    """Oracle Recruiting Cloud (HCM) candidate-experience REST API.

    The optional search term goes into the finder string, so it cannot
    contain a comma.
    """
    url = f"https://{source['host']}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    keyword = source.get("search", "")
    postings, seen, total = [], set(), None
    for page in range(MAX_PAGES):
        finder = (f"findReqs;siteNumber={source['site']},limit={ORACLE_PAGE},"
                  f"offset={page * ORACLE_PAGE},keyword={keyword},"
                  "sortBy=POSTING_DATES_DESC")
        item = _get(session, url, {"onlyData": "true", "expand": "requisitionList",
                                  "finder": finder})["items"][0]
        total = item.get("TotalJobsCount", total)
        new = [p for p in item.get("requisitionList", []) if p["Id"] not in seen]
        if not new:
            break
        seen.update(p["Id"] for p in new)
        postings.extend(new)
    return {"total": total, "jobPostings": postings}


def fetch_greenhouse(source, session):
    """Greenhouse job board API: one request returns every posting."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{source['token']}/jobs"
    jobs = _get(session, url)["jobs"]
    return {"total": len(jobs), "jobPostings": jobs}


GOLDMAN_URL = "https://api-higher.gs.com/gateway/api/v1/graphql"
GOLDMAN_PAGE = 100
GOLDMAN_QUERY = """query GetRoles($searchQueryInput: RoleSearchQueryInput!) {
  roleSearch(searchQueryInput: $searchQueryInput) {
    totalCount
    items { roleId jobTitle division locations { city state country }
            externalSource { sourceId } }
  }
}"""


def fetch_goldman(source, session):
    """Goldman Sachs' careers site (higher.gs.com) GraphQL API."""
    postings, seen, total = [], set(), None
    for page in range(MAX_PAGES):
        body = {"operationName": "GetRoles", "query": GOLDMAN_QUERY, "variables": {
            "searchQueryInput": {
                "page": {"pageSize": GOLDMAN_PAGE, "pageNumber": page},
                "sort": {"sortStrategy": "RELEVANCE", "sortOrder": "DESC"},
                "filters": [], "searchTerm": source.get("search", ""),
                "experiences": ["PROFESSIONAL", "EARLY_CAREER", "CAMPUS"]}}}
        data = _post(session, GOLDMAN_URL, body)
        if data.get("errors"):
            raise ValueError(data["errors"][0]["message"])
        result = data["data"]["roleSearch"]
        total = result.get("totalCount", total)
        new = [p for p in result["items"] if p["roleId"] not in seen]
        if not new:
            break
        seen.update(p["roleId"] for p in new)
        postings.extend(new)
    return {"total": total, "jobPostings": postings}


FETCHERS = {"workday": fetch_workday, "oracle": fetch_oracle,
            "greenhouse": fetch_greenhouse, "goldman": fetch_goldman}


def write_raw(raw_dir, date, name, data):
    path = Path(raw_dir) / date / f"{name}.json.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(data, f, sort_keys=True)
    tmp.replace(path)


def fetch_all(sources, date, raw_dir="data/raw"):
    """Fetch each source; return one result per source: name, ok, count, error."""
    session = requests.Session()
    results = []
    for source in sources:
        try:
            data = FETCHERS[source["ats"]](source, session)
            write_raw(raw_dir, date, source["name"], data)
            results.append({"name": source["name"], "ok": True,
                            "count": len(data["jobPostings"])})
        except Exception as e:  # a failed source must not stop the run
            results.append({"name": source["name"], "ok": False, "count": 0,
                            "error": f"{type(e).__name__}: {e}"})
    return results
