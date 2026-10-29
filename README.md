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

## Rebuild the history from the raw files

```
python -m pipeline.build
```

This reads only `data/raw/` and `sources.yaml` and rewrites `data/history.csv`.
Running it twice produces the same file.

## Sources

All sources use Workday's public JSON endpoint.

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

Workday returns at most 2,000 postings for one query and wraps back to the
first page past that. Boards bigger than that are narrowed server-side: JLL
uses the search term **`analyst`**, and Citi uses Workday's State filter set to
**Texas**. Both are set in `sources.yaml`.

## Title rule (`in_role`)

A posting is in role when its title matches an include pattern and no exclude
pattern. Exclusions win.

- **Include:** financial analyst, finance analyst, credit analyst, credit
  underwriter, underwriting analyst, FP&A, risk analyst, portfolio analyst,
  investment banking analyst, real estate finance, commercial / corporate / ABL
  banking analyst, private equity or M&A analyst.
- **Exclude:** senior, principal, director, VP / vice president, managing
  director, head, lead, manager, and sales or client-facing titles (financial
  advisor, financial representative, relationship manager, sales, business
  development).

The rule lives in `pipeline/title_rule.py` and is covered by
`tests/test_title_rule.py`. Every posting is kept in the history whether or not
it is in role; `in_role` is just a column.

## Files

| Path | What it does |
|---|---|
| `sources.yaml` | The employers and how to reach each job board |
| `pipeline/fetch.py` | Calls each source and saves the raw JSON |
| `pipeline/normalize.py` | Converts each ATS's postings to the common columns |
| `pipeline/title_rule.py` | The `in_role` title rule |
| `pipeline/build.py` | Builds `data/history.csv` from the raw files |
| `pipeline/status.py` | Builds `data/status.json` |
| `pipeline/run.py` | One daily run: fetch, build, status |
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
