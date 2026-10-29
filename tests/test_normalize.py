from pipeline.normalize import COLUMNS, normalize

WF = {"name": "wells_fargo", "employer": "Wells Fargo", "ats": "workday",
      "host": "wf.wd1", "tenant": "wf", "site": "WellsFargoJobs"}

WORKDAY_RAW = {
    "total": 2,
    "jobPostings": [
        {
            "title": "Credit Analyst",
            "externalPath": "/job/DALLAS-TX/Credit-Analyst_R-581608",
            "locationsText": "DALLAS, TX",
            "postedOn": "Posted Today",
            "bulletFields": ["R-581608"],
        },
        {
            "title": "Roving Personal Banker",
            "externalPath": "/job/SEDONA-AZ/Roving-Personal-Banker_R-584703",
            "locationsText": "2 Locations",
            "postedOn": "Posted 3 Days Ago",
            "bulletFields": ["R-584703"],
        },
    ],
}


def test_workday_maps_every_posting_to_common_columns():
    rows = normalize(WF, WORKDAY_RAW)
    assert len(rows) == 2
    assert all(list(r) == COLUMNS for r in rows)
    assert rows[0] == {
        "posting_id": "wells_fargo:R-581608",
        "source": "wells_fargo",
        "source_id": "R-581608",
        "employer": "Wells Fargo",
        "title": "Credit Analyst",
        "location": "DALLAS, TX",
        "department": "",
        "posted_date": "",
        "url": "https://wf.wd1.myworkdayjobs.com/WellsFargoJobs"
               "/job/DALLAS-TX/Credit-Analyst_R-581608",
    }


def test_workday_keeps_postings_outside_the_role():
    titles = [r["title"] for r in normalize(WF, WORKDAY_RAW)]
    assert "Roving Personal Banker" in titles


def test_workday_posting_without_title_is_kept_with_empty_title():
    raw = {"jobPostings": [{"externalPath": "/job/X/Mystery_R-1"}]}
    rows = normalize(WF, raw)
    assert len(rows) == 1
    assert rows[0]["title"] == "" and rows[0]["location"] == ""


def test_workday_empty_board():
    assert normalize(WF, {"total": 0, "jobPostings": []}) == []
