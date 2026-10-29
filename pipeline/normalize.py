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
        rows.append(_row(source, source_id, source["employer"], p["title"],
                         location=p.get("locationsText", ""), url=url))
    return rows


NORMALIZERS = {"workday": normalize_workday}


def normalize(source, raw):
    return NORMALIZERS[source["ats"]](source, raw)
