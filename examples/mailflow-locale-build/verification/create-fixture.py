#!/usr/bin/env python3
"""Create complete English test markers under locale code da, not a translation."""
import json
from pathlib import Path
import sys


def mark(value):
    if isinstance(value, dict):
        return {key: mark(item) for key, item in value.items()}
    if not isinstance(value, str):
        raise ValueError('expected native locale string')
    return 'Danish test: ' + value


source, destination = map(Path, sys.argv[1:])
if destination.exists():
    raise SystemExit('fixture destination already exists')
destination.write_text(json.dumps(mark(json.loads(source.read_text(encoding='utf8'))),
                                  ensure_ascii=True, indent=2) + '\n', encoding='utf8')
