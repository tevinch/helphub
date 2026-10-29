"""Add preceding-hour labels to Meteostat hourly rows requested in UTC."""

from collections.abc import Iterable, Mapping
import csv
from datetime import datetime, timedelta, timezone
import sys


def with_intervals(rows: Iterable[Mapping]) -> list[dict]:
    """Copy UTC rows, keeping their original time, rainfall and other fields.

    Use only for the default UTC response (tz=UTC), before any aggregation.
    A timestamp without an offset is interpreted as UTC. Explicit nonzero
    offsets are rejected; this recipe does not interpret local wall times.
    """
    result = []
    for row in rows:
        if "interval_start" in row or "interval_end" in row:
            raise ValueError("Interval columns already exist; keep or rename them first")
        if "prcp" not in row:
            raise ValueError("Each hourly row must include prcp, even when it is missing")
        if not isinstance(row["time"], str):
            raise TypeError("The time field must be a timestamp string")
        end = datetime.fromisoformat(row["time"])
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        elif end.utcoffset() != timedelta(0):
            raise ValueError("Use a UTC response (tz=UTC), not local wall times")
        start = end - timedelta(hours=1)
        result.append({
            **row,
            "interval_start": start.isoformat(sep=" "),
            "interval_end": end.isoformat(sep=" "),
        })
    return result


def main() -> None:
    rows = [
        {"time": "2024-01-05 04:00:00", "prcp": 0},
        {"time": "2024-01-05 05:00:00", "prcp": 2.4},
        {"time": "2024-01-05 06:00:00", "prcp": 1.8},
    ]
    writer = csv.DictWriter(
        sys.stdout, fieldnames=["time", "interval_start", "interval_end", "prcp"],
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(with_intervals(rows))


if __name__ == "__main__":
    main()
