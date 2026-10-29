"""Write data/status.json describing the latest run."""
import json
from pathlib import Path


def build_status(rows, results, run_time, date, raw_dir="data/raw"):
    """rows: history rows. results: per-source fetch results for this run."""
    raw_dir = Path(raw_dir)
    days = raw_dir.iterdir() if raw_dir.is_dir() else []
    dates = sorted(d.name for d in days
                   if d.is_dir() and any(d.glob("*.json.gz")))
    return {
        "run_time": run_time,
        "first_run_date": dates[0] if dates else "",
        "days_with_success": len(dates),
        "open": sum(r["status"] == "open" for r in rows),
        "new_today": sum(r["first_seen"] == date and not r["first_run"] for r in rows),
        "removed_today": sum(r["removed_date"] == date for r in rows),
        "sources": [
            {k: v for k, v in r.items() if k in ("name", "ok", "count", "error")}
            for r in results
        ],
    }


def write_status(status, path="data/status.json"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
