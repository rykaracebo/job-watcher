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


JPM = {"name": "jpmorgan", "employer": "JPMorgan Chase", "ats": "oracle",
       "host": "jpmc.fa.oraclecloud.com", "site": "CX_1001"}


def test_oracle_maps_to_common_columns():
    raw = {"jobPostings": [{"Id": "210787939", "Title": "Credit Analyst",
                            "PostedDate": "2026-11-03", "JobFamily": "Credit Risk",
                            "PrimaryLocation": "Dallas, TX, United States"}]}
    assert normalize(JPM, raw) == [{
        "posting_id": "jpmorgan:210787939", "source": "jpmorgan", "source_id": "210787939",
        "employer": "JPMorgan Chase", "title": "Credit Analyst",
        "location": "Dallas, TX, United States", "department": "Credit Risk",
        "posted_date": "2026-11-03",
        "url": "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210787939",
    }]


def test_oracle_null_fields_become_empty_strings():
    rows = normalize(JPM, {"jobPostings": [{"Id": 5, "Title": "X", "PrimaryLocation": None,
                                            "JobFamily": None, "PostedDate": None}]})
    assert rows[0]["source_id"] == "5"
    assert (rows[0]["location"], rows[0]["department"], rows[0]["posted_date"]) == ("", "", "")


KKR = {"name": "kkr", "employer": "KKR", "ats": "greenhouse", "token": "stage"}


def test_greenhouse_maps_to_common_columns():
    raw = {"jobPostings": [{"id": 7650001, "title": "Analyst, Insurance",
                            "location": {"name": "Dallas, Texas, United States"},
                            "first_published": "2026-10-20T14:03:11-04:00",
                            "absolute_url": "https://kkr.com/jobs?gh_jid=7650001"}]}
    assert normalize(KKR, raw) == [{
        "posting_id": "kkr:7650001", "source": "kkr", "source_id": "7650001",
        "employer": "KKR", "title": "Analyst, Insurance",
        "location": "Dallas, Texas, United States", "department": "",
        "posted_date": "2026-10-20", "url": "https://kkr.com/jobs?gh_jid=7650001",
    }]


def test_greenhouse_without_location_or_date():
    rows = normalize(KKR, {"jobPostings": [{"id": 1, "title": "T", "location": None,
                                            "first_published": None}]})
    assert rows[0]["location"] == "" and rows[0]["posted_date"] == ""


GS = {"name": "goldman", "employer": "Goldman Sachs", "ats": "goldman"}


def test_goldman_maps_to_common_columns_and_joins_locations():
    raw = {"jobPostings": [{
        "roleId": "184072_GS_EARLY_CAREER", "jobTitle": "Credit Analyst",
        "division": "Asset Management",
        "locations": [{"city": "Dallas", "state": "TX", "country": "United States"},
                      {"city": "New York", "state": "NY", "country": "United States"}],
        "externalSource": {"sourceId": "184072"}}]}
    assert normalize(GS, raw) == [{
        "posting_id": "goldman:184072_GS_EARLY_CAREER", "source": "goldman",
        "source_id": "184072_GS_EARLY_CAREER", "employer": "Goldman Sachs",
        "title": "Credit Analyst",
        "location": "Dallas, TX, United States; New York, NY, United States",
        "department": "Asset Management", "posted_date": "",
        "url": "https://higher.gs.com/roles/184072",
    }]


def test_goldman_posting_with_no_locations():
    rows = normalize(GS, {"jobPostings": [{"roleId": "9_GS", "jobTitle": "T",
                                           "locations": [], "externalSource": None}]})
    assert rows[0]["location"] == "" and rows[0]["url"].endswith("/roles/9_GS")


def test_workday_location_falls_back_to_bullet_fields():
    raw = {"jobPostings": [{
        "title": "Financial Analyst",
        "externalPath": "/job/Saint-Petersburg/Financial-Analyst_R-0013339",
        "bulletFields": ["Saint Petersburg, Florida - United States", "R-0013339"]}]}
    assert normalize(WF, raw)[0]["location"] == "Saint Petersburg, Florida - United States"


def test_workday_requisition_id_alone_is_not_a_location():
    raw = {"jobPostings": [{"title": "X", "externalPath": "/job/A/X_R-1",
                            "bulletFields": ["R-1"]}]}
    assert normalize(WF, raw)[0]["location"] == ""
