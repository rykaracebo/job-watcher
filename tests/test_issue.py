import json

from pipeline.issue import build_body, sync_issue

DATE = "2026-10-03"


def row(**kw):
    base = {"title": "Credit Analyst", "url": "https://x/1", "employer": "Acme",
            "location": "Dallas, Texas", "in_role": "true", "first_run": "false",
            "first_seen": "2026-10-01", "removed_date": ""}
    return dict(base, **kw)


class FakeGh:
    """Records gh calls; `issues` is what `gh issue list` returns."""

    def __init__(self, issues):
        self.issues, self.calls = issues, []

    def __call__(self, args):
        self.calls.append(args)
        return json.dumps(self.issues) if args[1] == "list" else ""

    def verbs(self):
        return [c[1] for c in self.calls]


def test_body_lists_new_and_removed_with_links():
    rows = [
        row(title="New One", url="https://x/new", first_seen=DATE),
        row(title="Gone One", url="https://x/gone", removed_date=DATE),
        row(title="Old", url="https://x/old"),
        row(title="First Run", first_seen=DATE, first_run="true"),
    ]
    body = build_body(rows, DATE)
    assert "## New postings (1)" in body and "[New One](https://x/new)" in body
    assert "## Removed postings (1)" in body and "[Gone One](https://x/gone)" in body
    assert "Old" not in body and "First Run" not in body


def test_body_on_a_quiet_day_still_has_both_sections():
    body = build_body([row()], DATE)
    assert "## New postings (0)" in body and "## Removed postings (0)" in body
    assert body.count("None.") == 2


def test_in_role_postings_come_first_and_brackets_are_escaped():
    rows = [row(title="Zeta Teller", in_role="false", first_seen=DATE),
            row(title="Analyst [II]", first_seen=DATE)]
    body = build_body(rows, DATE)
    assert body.index("Analyst (II)") < body.index("Zeta Teller")


def test_a_huge_day_is_cut_to_fit_and_says_so():
    rows = [row(title=f"Job {i}", first_seen=DATE, url="https://x/" + "a" * 200)
            for i in range(1000)]
    body = build_body(rows, DATE)
    assert len(body) < 65_000
    assert "more not shown" in body


def test_first_run_of_the_day_creates_the_issue():
    gh = FakeGh([])
    sync_issue(DATE, "body", gh)
    assert gh.verbs() == ["list", "create"]


def test_second_run_updates_instead_of_duplicating():
    gh = FakeGh([{"number": 7, "title": DATE, "state": "OPEN"}])
    sync_issue(DATE, "body", gh)
    assert gh.verbs() == ["list", "edit"]


def test_previous_open_issues_are_closed_and_others_left_alone():
    gh = FakeGh([
        {"number": 7, "title": DATE, "state": "OPEN"},
        {"number": 6, "title": "2026-10-02", "state": "OPEN"},
        {"number": 5, "title": "2026-10-01", "state": "CLOSED"},
        {"number": 4, "title": "Fix the thing", "state": "OPEN"},
    ])
    sync_issue(DATE, "body", gh)
    closed = [c[2] for c in gh.calls if c[1] == "close"]
    assert closed == ["6"]


def test_a_closed_issue_for_today_is_reopened():
    gh = FakeGh([{"number": 7, "title": DATE, "state": "CLOSED"}])
    sync_issue(DATE, "body", gh)
    assert gh.verbs() == ["list", "edit", "reopen"]
