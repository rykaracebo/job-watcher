"""Open the daily GitHub Issue and close the previous one.

    python -m pipeline.issue

Reads data/history.csv and data/status.json (the run date is the UTC date in
status.json) and talks to GitHub through the `gh` CLI, which authenticates
with the GH_TOKEN environment variable in Actions.

One issue per day, titled with the date. A second run on the same day updates
that day's issue instead of creating a duplicate. Every other open
date-titled issue is closed, so only one is open at a time.
"""
import csv
import json
import re
import subprocess

DATE_TITLE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SECTION_BUDGET = 28_000      # characters per list; GitHub caps a body at 65,536


def _line(row):
    title = row["title"].replace("[", "(").replace("]", ")") or "(no title)"
    place = f" · {row['location']}" if row["location"] else ""
    return f"- [{title}]({row['url']}) · {row['employer']}{place}"


def _section(heading, rows, budget=SECTION_BUDGET):
    """A heading and a bulleted list; in-role postings come first.

    If the list does not fit in `budget` characters, the rest is summarized
    as a count (the full list is always in data/history.csv).
    """
    rows = sorted(rows, key=lambda r: (r["in_role"] != "true", r["employer"], r["title"]))
    lines, used = [], 0
    for row in rows:
        line = _line(row)
        if used + len(line) + 1 > budget:
            break
        lines.append(line)
        used += len(line) + 1
    out = [f"## {heading} ({len(rows)})", ""]
    out += lines or ["None."]
    if len(lines) < len(rows):
        out += ["", f"_{len(rows) - len(lines)} more not shown; see data/history.csv._"]
    return "\n".join(out)


def build_body(rows, date):
    """Issue body: new and removed postings for `date`. Rows are history rows."""
    new = [r for r in rows if r["first_seen"] == date and r["first_run"] != "true"]
    removed = [r for r in rows if r["removed_date"] == date]
    return "\n\n".join([
        "In-role postings are listed first.",
        _section("New postings", new),
        _section("Removed postings", removed),
    ]) + "\n"


def sync_issue(date, body, gh):
    """Create or update the issue titled `date`; close other date-titled issues.

    gh: callable taking a list of CLI arguments and returning stdout.
    """
    issues = json.loads(gh(["issue", "list", "--state", "all", "--limit", "200",
                            "--json", "number,title,state"]))
    today = next((i for i in issues if i["title"] == date), None)
    if today is None:
        gh(["issue", "create", "--title", date, "--body", body])
    else:
        gh(["issue", "edit", str(today["number"]), "--body", body])
        if today["state"] != "OPEN":
            gh(["issue", "reopen", str(today["number"])])
    for issue in issues:
        if (issue["state"] == "OPEN" and issue["title"] != date
                and DATE_TITLE.match(issue["title"])):
            gh(["issue", "close", str(issue["number"])])


def _gh(args):
    return subprocess.run(["gh", *args], check=True, capture_output=True,
                          text=True).stdout


def main():
    with open("data/status.json", encoding="utf-8") as f:
        date = json.load(f)["run_time"][:10]
    with open("data/history.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    sync_issue(date, build_body(rows, date), _gh)
    print(f"Issue {date} is up to date")


if __name__ == "__main__":
    main()
