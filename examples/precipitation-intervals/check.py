"""Run the sample and check its interval labels using only the standard library."""

import csv
import importlib.util
import io
import math
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
EXAMPLE = HERE / "example.py"
assert EXAMPLE.is_file(), "example.py must provide the runnable interval sample"
spec = importlib.util.spec_from_file_location("interval_example", EXAMPLE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with_intervals = module.with_intervals


def expect_error(rows, error):
    try:
        with_intervals(rows)
    except error:
        return
    raise AssertionError(f"Expected {error.__name__} for {rows!r}")


# These are literal expected outputs of the original three-row example.
run = subprocess.run(
    [sys.executable, str(EXAMPLE)], capture_output=True, text=True, check=True
)
assert run.stderr == "", run.stderr
reader = csv.DictReader(io.StringIO(run.stdout))
assert reader.fieldnames == ["time", "interval_start", "interval_end", "prcp"]
assert list(reader) == [
    {"time": "2024-01-05 04:00:00", "prcp": "0",
     "interval_start": "2024-01-05 03:00:00+00:00",
     "interval_end": "2024-01-05 04:00:00+00:00"},
    {"time": "2024-01-05 05:00:00", "prcp": "2.4",
     "interval_start": "2024-01-05 04:00:00+00:00",
     "interval_end": "2024-01-05 05:00:00+00:00"},
    {"time": "2024-01-05 06:00:00", "prcp": "1.8",
     "interval_start": "2024-01-05 05:00:00+00:00",
     "interval_end": "2024-01-05 06:00:00+00:00"},
], "Each rainfall value must remain at its original time, with a preceding hour"
print("PASS: original three rows, complete CSV output and 05:00 -> 04:00-05:00 / 2.4 mm")

# Shifting records or changing an instantaneous field breaks this check.
source = [
    {"time": "2024-01-05 05:00:00", "prcp": "2.400", "temp": 7.1},
    {"time": "2024-01-05 07:00:00", "prcp": None, "temp": 8.2},
]
result = with_intervals(source)
assert source == [
    {"time": "2024-01-05 05:00:00", "prcp": "2.400", "temp": 7.1},
    {"time": "2024-01-05 07:00:00", "prcp": None, "temp": 8.2},
]
assert len(result) == 2, "Do not fill gaps"
assert result[0] is not source[0] and result[1] is not source[1]
assert result[0] == {
    "time": "2024-01-05 05:00:00", "prcp": "2.400", "temp": 7.1,
    "interval_start": "2024-01-05 04:00:00+00:00",
    "interval_end": "2024-01-05 05:00:00+00:00",
}
assert result[1] == {
    "time": "2024-01-05 07:00:00", "prcp": None, "temp": 8.2,
    "interval_start": "2024-01-05 06:00:00+00:00",
    "interval_end": "2024-01-05 07:00:00+00:00",
}, "A gap must not stretch the next one-hour accumulation or become zero"
assert math.isnan(with_intervals([
    {"time": "2024-01-05 08:00:00", "prcp": float("nan")}
])[0]["prcp"])
assert with_intervals([]) == []
print("PASS: original records/fields, missing/NaN values and gaps preserved")

assert with_intervals([{"time": "2024-01-01 00:00:00", "prcp": 3}])[0] == {
    "time": "2024-01-01 00:00:00", "prcp": 3,
    "interval_start": "2023-12-31 23:00:00+00:00",
    "interval_end": "2024-01-01 00:00:00+00:00",
}
for time in ("2024-01-05T05:00:00Z", "2024-01-05T05:00:00+00:00"):
    row = with_intervals([{"time": time, "prcp": 2.4}])[0]
    assert row["time"] == time
    assert row["interval_start"] == "2024-01-05 04:00:00+00:00"
    assert row["interval_end"] == "2024-01-05 05:00:00+00:00"
print("PASS: midnight/year boundary and explicit UTC offsets")

for time in ("2024-10-27T02:00:00+02:00", "2024-10-27T02:00:00+01:00"):
    expect_error([{"time": time, "prcp": 1}], ValueError)
expect_error([{"time": "not-a-time", "prcp": 1}], ValueError)
expect_error([{"time": 123, "prcp": 1}], TypeError)
expect_error([{"time": "2024-01-05 05:00:00"}], ValueError)
for key in ("interval_start", "interval_end"):
    existing = {"time": "2024-01-05 05:00:00", "prcp": 2.4, key: "keep"}
    expect_error([existing], ValueError)
    assert existing[key] == "keep"
print("PASS: custom local offsets, malformed records and existing output fields rejected")
print("All checks passed. These checks verify sample arithmetic, not station observation quality.")
