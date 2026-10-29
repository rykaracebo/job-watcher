"""Build data/history.csv from the raw files alone.

The history is a pure replay of data/raw/, day by day, so running the build
again gives the same file and a rule change applies to every day.

    python -m pipeline.build
"""
import csv
import gzip
import json
from pathlib import Path

import yaml

from pipeline.normalize import normalize
from pipeline.title_rule import in_role

HISTORY_COLUMNS = [
    "posting_id", "source", "source_id", "employer", "title", "location",
    "department", "posted_date", "url", "in_role", "first_run", "first_seen",
    "last_seen", "status", "removed_date",
]


def raw_files(raw_dir):
    """Yield (date, source_name, path) in date order, then source order."""
    raw_dir = Path(raw_dir)
    found = [(day.name, f.name[:-len(".json.gz")], f)
             for day in raw_dir.iterdir() if day.is_dir()
             for f in day.glob("*.json.gz")]
    return sorted(found, key=lambda t: (t[0], t[1]))


def replay(days, sources):
    """days: iterable of (date, source_name, raw_json) in date order.

    Returns the history rows (dicts), keyed by posting_id, in no set order.
    """
    history = {}
    first_file_of = {}
    for date, name, raw in days:
        source = sources.get(name)
        if source is None:
            continue                      # source no longer in sources.yaml
        first_run = first_file_of.setdefault(name, date) == date
        listed = {}
        for row in normalize(source, raw):
            listed[row["posting_id"]] = row   # one row per posting per file

        for pid, row in listed.items():
            old = history.get(pid)
            if old is None:
                history[pid] = dict(row, first_run=first_run, first_seen=date,
                                    last_seen=date, status="open", removed_date="")
            else:
                old.update(row)           # latest title, location, url
                old["last_seen"] = date
                old["status"], old["removed_date"] = "open", ""

        for pid, old in history.items():
            if old["source"] == name and old["status"] == "open" and pid not in listed:
                old["status"], old["removed_date"] = "removed", date
    return history


def build_history(raw_dir, sources):
    def days():
        for date, name, path in raw_files(raw_dir):
            with gzip.open(path, "rt", encoding="utf-8") as f:
                yield date, name, json.load(f)

    history = replay(days(), sources)
    rows = []
    for pid in sorted(history):
        row = history[pid]
        row["in_role"] = in_role(row["title"])
        rows.append(row)
    return rows


def _fmt(value):
    return str(value).lower() if isinstance(value, bool) else value


def write_history(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, HISTORY_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: _fmt(row[c]) for c in HISTORY_COLUMNS})


def load_sources(path="sources.yaml"):
    with open(path, encoding="utf-8") as f:
        return {s["name"]: s for s in yaml.safe_load(f)["sources"]}


if __name__ == "__main__":
    rows = build_history("data/raw", load_sources())
    write_history(rows, "data/history.csv")
    print(f"Wrote data/history.csv: {len(rows)} postings")
