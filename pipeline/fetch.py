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


def _post(session, url, body):
    for attempt in range(RETRIES):
        try:
            r = session.post(url, json=body, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if attempt == RETRIES - 1:
                raise
            time.sleep(2 ** attempt)


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


FETCHERS = {"workday": fetch_workday}


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
