#!/usr/bin/env python3
"""Independently decode the complete exported files with Python's CSV reader."""
import csv
from pathlib import Path
import sys

output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('output')
checked = 0
for name in ['us-first', 'gb-first', 'gb-repeat', 'us-repeat', 'us-empty', 'us-no-header']:
    us = name.startswith('us-')
    header = ['Vehicle, name', 'Speed', 'Notes', 'Observed on'] if us else ['Vehicle name', 'Speed', 'Remarks', 'Observation date']
    expected = [] if name == 'us-no-header' else [header]
    if name != 'us-empty':
        expected += [
            ['Bus 🚍, "Express"\r\nLine 2', '1234.5', '(missing)', '11/30/2026' if us else '30/11/2026'],
            ['Shuttle; blue', '7.25', 'Keep "quotes", commas; and\nnewlines', '12/1/2026' if us else '01/12/2026'],
        ]
    path = output / (name + '.csv')
    with path.open(encoding='utf8', newline='') as handle:
        actual = list(csv.reader(handle, delimiter=',' if us else ';', strict=True))
    assert actual == expected, (name, actual, expected)
    raw = path.read_bytes()
    assert raw.endswith(b'\r\n') and not raw.startswith(b'\xef\xbb\xbf'), name
    if name != 'us-empty':
        assert b'""Express""' in raw and '🚍'.encode() in raw, name
    checked += 1
assert checked == 6
print('PASS: independent Python CSV parsing verified every header and field in all 6 complete exports.')
