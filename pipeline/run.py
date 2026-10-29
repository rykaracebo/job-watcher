"""One daily run: fetch -> build history -> write status.

    python -m pipeline.run

The date is the UTC date of the moment it runs. A second run on the same day
replaces that day's raw files and rebuilds, so each day counts once.
"""
from datetime import datetime, timezone

from pipeline.build import build_history, load_sources, write_history
from pipeline.fetch import fetch_all
from pipeline.status import build_status, write_status


def main():
    now = datetime.now(timezone.utc)
    date = now.strftime("%Y-%m-%d")
    sources = load_sources()

    results = fetch_all(list(sources.values()), date)
    for r in results:
        print(f"{'ok  ' if r['ok'] else 'FAIL'} {r['name']}: {r['count']} {r.get('error', '')}")

    rows = build_history("data/raw", sources)
    write_history(rows, "data/history.csv")
    status = build_status(rows, results, now.strftime("%Y-%m-%dT%H:%M:%SZ"), date)
    write_status(status)
    print(f"{date}: {status['open']} open, {status['new_today']} new, "
          f"{status['removed_today']} removed, {status['days_with_success']} day(s)")


if __name__ == "__main__":
    main()
