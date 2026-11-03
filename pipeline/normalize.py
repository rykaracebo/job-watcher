"""Convert each ATS's raw postings into one common set of columns."""

COLUMNS = [
    "posting_id", "source", "source_id", "employer", "title", "location",
    "department", "posted_date", "url",
]


def _row(source, source_id, employer, title, location="", department="",
         posted_date="", url=""):
    return {
        "posting_id": f"{source['name']}:{source_id}",
        "source": source["name"],
        "source_id": source_id,
        "employer": employer,
        "title": title,
        "location": location,
        "department": department,
        "posted_date": posted_date,
        "url": url,
    }


def normalize_workday(source, raw):
    """Workday list postings. The path ends in _<requisition id>.

    postedOn is relative text ("Posted Today"), not a date, so posted_date
    stays empty. Multi-location postings only say "N Locations" in the list.
    """
    rows = []
    for p in raw.get("jobPostings", []):
        path = p["externalPath"]
        source_id = path.rsplit("/", 1)[-1].rsplit("_", 1)[-1]
        url = f"https://{source['host']}.myworkdayjobs.com/{source['site']}{path}"
        rows.append(_row(source, source_id, source["employer"], p.get("title", ""),
                         location=p.get("locationsText", ""), url=url))
    return rows


def normalize_oracle(source, raw):
    """Oracle Recruiting Cloud postings. PostedDate is a real YYYY-MM-DD date."""
    rows = []
    for p in raw.get("jobPostings", []):
        url = (f"https://{source['host']}/hcmUI/CandidateExperience/en/sites/"
               f"{source['site']}/job/{p['Id']}")
        rows.append(_row(source, str(p["Id"]), source["employer"], p.get("Title", ""),
                         location=p.get("PrimaryLocation") or "",
                         department=p.get("JobFamily") or "",
                         posted_date=p.get("PostedDate") or "", url=url))
    return rows


def normalize_greenhouse(source, raw):
    """Greenhouse postings. first_published is an ISO timestamp; keep its date."""
    rows = []
    for p in raw.get("jobPostings", []):
        rows.append(_row(source, str(p["id"]), source["employer"], p.get("title", ""),
                         location=(p.get("location") or {}).get("name", ""),
                         posted_date=(p.get("first_published") or "")[:10],
                         url=p.get("absolute_url", "")))
    return rows


def _goldman_place(loc):
    return ", ".join(x for x in (loc.get("city"), loc.get("state"), loc.get("country")) if x)


def normalize_goldman(source, raw):
    """Goldman roles. Several locations are joined with '; '."""
    rows = []
    for p in raw.get("jobPostings", []):
        place = "; ".join(_goldman_place(l) for l in p.get("locations") or [])
        sid = (p.get("externalSource") or {}).get("sourceId") or p["roleId"]
        rows.append(_row(source, p["roleId"], source["employer"], p.get("jobTitle", ""),
                         location=place, department=p.get("division") or "",
                         url=f"https://higher.gs.com/roles/{sid}"))
    return rows


NORMALIZERS = {"workday": normalize_workday, "oracle": normalize_oracle,
               "greenhouse": normalize_greenhouse, "goldman": normalize_goldman}


def normalize(source, raw):
    return NORMALIZERS[source["ats"]](source, raw)
