# Label hourly precipitation intervals

For Meteostat's hourly `prcp` convention, **2.4 mm at 05:00 refers to the preceding hour, 04:00–05:00**. It is an accumulated amount, rather than the rainfall at a single instant.

The [maintainer's parameter description](https://github.com/meteostat/meteostat/issues/62) explicitly calls hourly `prcp` the precipitation total of the previous hour. The [current station API documentation](https://dev.meteostat.net/api/stations/hourly) calls it a one-hour total without spelling out that boundary; it documents UTC as the default timezone. The current stable Python library, [2.1.5](https://github.com/meteostat/meteostat/releases/tag/v2.1.5), likewise [defaults hourly queries to UTC](https://github.com/meteostat/meteostat/blob/v2.1.5/meteostat/api/hourly.py).

Keep the original observation timestamp and rainfall value together. Add interval columns when you need explicit labels; do not move rainfall to the next row or shift instantaneous variables such as temperature.

## Run the example

Download `example.py` and `check.py` into the same directory. Use Python 3.11 or newer; there are no extra packages or network requests.

```sh
python3 example.py
python3 check.py
```

The sample uses the three rows in the question, treating their timestamps as UTC:

```csv
time,interval_start,interval_end,prcp
2024-01-05 04:00:00,2024-01-05 03:00:00+00:00,2024-01-05 04:00:00+00:00,0
2024-01-05 05:00:00,2024-01-05 04:00:00+00:00,2024-01-05 05:00:00+00:00,2.4
2024-01-05 06:00:00,2024-01-05 05:00:00+00:00,2024-01-05 06:00:00+00:00,1.8
```

For existing records, copy `with_intervals` from `example.py` or import it:

```python
from example import with_intervals

rows = [{"time": "2024-01-05 05:00:00", "prcp": 2.4, "temp": 7.1}]
labelled = with_intervals(rows)
print(labelled[0])
```

It returns new row dictionaries and preserves all original fields, including `time`, `prcp` and `temp`. Missing rainfall (`None` or `NaN`) remains missing. Gaps remain gaps: a row at 07:00 still labels 06:00–07:00 even if the 06:00 row is absent. Midnight correctly reaches into the previous date. Existing `interval_start` or `interval_end` fields cause an error, so they are not overwritten.

## Scope and checks

Use this recipe on **hourly UTC records before aggregation**. Timestamps without an offset are interpreted as UTC, which requires a response requested with `tz=UTC` or the API's UTC default. `Z` and `+00:00` timestamps are also accepted. Nonzero offsets are rejected. A timestamp string alone cannot reveal that a response used a custom local timezone; request UTC before using this example. This avoids guessing around repeated or missing local hours during daylight saving changes.

The interval labels describe the intended hourly convention. They do not establish the exact physical sampling window, quality or source of every observation. For example, [NOAA's ISD-Lite documentation](https://noaa-isd-pds.s3.amazonaws.com/isd-lite/isd-lite-technical-document.pdf) describes selecting observations near the hour and using a modified hourly timestamp. Keep provider provenance when precise measurement timing matters. The recipe does not recompute rainfall, align other providers, fill gaps or derive daily totals.

Checked with Python 3.12.4 on macOS: the complete CSV output, the exact 05:00/2.4 mm interval, unchanged input and extra fields, missing/NaN values, gaps, midnight/year boundary, accepted UTC timestamps, and rejection of local offsets and existing interval columns. Temporary variants that moved the boundary forward, omitted the start column or changed missing rainfall to zero failed the checks. These are programmatic sample checks; they do not validate remote weather observations.

## Optional coffee

If this saved you some time, a coffee is welcome, but entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
