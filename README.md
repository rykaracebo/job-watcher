# Job Watcher

[![tests](https://github.com/rykaracebo/job-watcher/actions/workflows/tests.yml/badge.svg)](https://github.com/rykaracebo/job-watcher/actions/workflows/tests.yml)

A tool that watches the job market every day. It pulls the open positions at a
set of finance employers, compares them with the day before, records what is
new and what is gone, and publishes the result.

**Role watched:** entry-level financial / credit analyst, with a focus on
Dallas-Fort Worth.

## How it works

1. GitHub Actions runs `python -m pipeline.run` once a day.
2. Each source's job board is requested as JSON (no login, no HTML scraping)
   and saved to `data/raw/<date>/<source>.json.gz`. A source that fails writes
   no file that day and the run continues.
3. `data/history.csv` is rebuilt from the raw files alone, so a change to a
   rule applies to every day of history.
4. `data/status.json` describes the latest run.
5. The data files are committed to the repository.
6. `python -m pipeline.issue` opens an Issue titled with the date that lists
   the new and removed postings, and closes the previous day's issue. A second
   run on the same day updates that day's issue.

## Rebuild the history from the raw files

```
python -m pipeline.build
```

This reads only `data/raw/` and `sources.yaml` and rewrites `data/history.csv`.
Running it twice produces the same file.

## Sources

Every source returns JSON to a request with no login. Four applicant tracking
systems are used: Workday, Oracle Recruiting Cloud, Greenhouse, and Goldman
Sachs' own careers API (a GraphQL endpoint behind higher.gs.com).

| Source | Employer | ATS | Notes |
|---|---|---|---|
| wells_fargo | Wells Fargo | Workday | |
| citi | Citi | Workday | Texas only (see below) |
| truist | Truist | Workday | |
| capital_one | Capital One | Workday | |
| td | TD | Workday | |
| santander | Santander | Workday | |
| fidelity | Fidelity | Workday | |
| blackstone | Blackstone | Workday | |
| jll | JLL | Workday | Search term: `analyst` |
| att | AT&T | Workday | |
| bofa | Bank of America | Workday | Search term: `analyst` |
| fifth_third | Fifth Third (absorbed Comerica) | Workday | |
| texas_capital | Texas Capital Bank | Workday | |
| frost | Frost Bank | Workday | |
| raymond_james | Raymond James | Workday | |
| jpmorgan | JPMorgan Chase | Oracle Recruiting Cloud | Search term: `analyst` (7,000+ postings) |
| gm_financial | GM Financial | Oracle Recruiting Cloud | |
| kkr | KKR | Greenhouse | Board token `stage` |
| goldman | Goldman Sachs | Goldman careers API | |

Boards with more than 5,000 postings must be requested with a search term:
JPMorgan (7,110 postings) uses **`analyst`**. Workday also returns at most
2,000 postings for one query and wraps back to the first page past that, so
large Workday boards are narrowed server-side too: JLL and Bank of America use
the search term **`analyst`**, and Citi uses Workday's State filter set to
**Texas**. All of this is set in `sources.yaml`.

## Title rule (`in_role`)

A posting is in role when its title matches an include pattern and no exclude
pattern. Exclusions win.

- **Include:** financial analyst, finance analyst, credit analyst, credit
  underwriter, underwriting analyst, FP&A (also "financial planning and
  analysis"), risk analyst, portfolio analyst, investment banking analyst, real
  estate finance, commercial / corporate / ABL banking analyst, private equity
  or M&A analyst, and Credit Officer I.
  - A finance function next to "analyst" counts in either order: "Valuation
    Analyst", "Finance Reporting Analyst", "Analyst, Risk", "Analyst,
    Alternative Investments". "Associate Analyst" counts only with a function.
  - A full-time "Analyst Program" counts when its title names a finance
    function (for example the Commercial Real Estate Full-Time Analyst Program).
  - A plain "Associate" does not count in investment banking, private equity or
    M&A, where it is a post-MBA title. Credit Officer II and above are left out
    as too experienced for entry level.
- **Exclude:** senior, principal, director, VP / vice president, AVP, managing
  director, head, lead, manager; sales or client-facing titles (financial
  advisor, financial representative, relationship manager, relationship,
  relations, client, sales, business development); and internships (intern,
  internship, summer, co-op).

The rule lives in `pipeline/title_rule.py` and is covered by
`tests/test_title_rule.py`, which has a test for every title added or excluded
and checks that no sales or client term gets through the word-order rule. Every
posting is kept in the history whether or not it is in role; `in_role` is just
a column, so a change to the rule applies to every day of history on the next
build.

## Files

| Path | What it does |
|---|---|
| `sources.yaml` | The employers and how to reach each job board |
| `pipeline/fetch.py` | Calls each source (one fetcher per ATS) and saves the raw JSON |
| `pipeline/normalize.py` | Converts each ATS's postings to the common columns |
| `pipeline/title_rule.py` | The `in_role` title rule |
| `pipeline/build.py` | Builds `data/history.csv` from the raw files |
| `pipeline/status.py` | Builds `data/status.json` |
| `pipeline/run.py` | One daily run: fetch, build, status |
| `pipeline/issue.py` | Opens the day's GitHub Issue (new and removed postings) and closes the previous one |
| `tests/` | pytest suite: normalizers, title rule, history logic, fetcher, status |
| `data/raw/<date>/<source>.json.gz` | What each source returned that day |
| `data/history.csv` | One row per posting ever seen |
| `data/status.json` | Result of the latest run |
| `.github/workflows/daily.yml` | Daily scheduled run, commits the data |
| `.github/workflows/tests.yml` | Runs pytest on every push |

## Run locally

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
python -m pipeline.run
```
