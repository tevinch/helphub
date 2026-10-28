#!/usr/bin/env python3
"""Place explicitly mapped extras beside existing Igir game folders. Python 3.10+."""
import argparse
import json
from pathlib import Path
import shutil
import sys

KINDS = frozenset('dlc hack manual mod patch update demo translation prototype walkthrough soundtrack cheat screenshot'.split())

def component(value, label):
    if not isinstance(value, str) or not value or value in ('.', '..') or any(c in value for c in '/\\\0') or Path(value).is_absolute():
        raise ValueError(f'{label} must be one nonempty directory name')
    return value

def inside(path, root):
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f'path leaves its root: {path}')
    return resolved

def same_bytes(left, right):
    if left.stat().st_size != right.stat().st_size:
        return False
    with left.open('rb') as a, right.open('rb') as b:
        while True:
            first, second = a.read(65536), b.read(65536)
            if first != second:
                return False
            if not first:
                return True

def prepare(manifest, output):
    manifest = manifest.resolve(strict=True)
    output = output.resolve(strict=True)
    if not output.is_dir():
        raise ValueError('output must be an existing directory')
    rows = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise ValueError('manifest must be a JSON array')
    plan, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'source', 'platform', 'game', 'kind'}:
            raise ValueError('each entry needs exactly source, platform, game, kind')
        platform, game, kind = (component(row[key], key) for key in ('platform', 'game', 'kind'))
        if kind not in KINDS:
            raise ValueError(f'unsupported kind: {kind}')
        source_name = row['source']
        if not isinstance(source_name, str) or not source_name or Path(source_name).is_absolute() or '\\' in source_name:
            raise ValueError('source must be a relative path within the manifest directory')
        source = inside(manifest.parent / source_name, manifest.parent)
        if not source.is_file():
            raise ValueError(f'source is not a file: {source}')
        game_dir = inside(output / platform / game, output)
        if not game_dir.is_dir():
            raise ValueError(f'game folder must already exist from Igir: {game_dir}')
        target = inside(game_dir / kind / source.name, output)
        if target in seen:
            raise ValueError(f'duplicate target: {target}')
        seen.add(target)
        if target.exists():
            if not target.is_file() or not same_bytes(target, source):
                raise ValueError(f'different existing target; nothing copied: {target}')
            action = 'unchanged'
        else:
            if not target.parent.exists() and target.parent.parent != game_dir:
                raise ValueError(f'invalid target directory: {target.parent}')
            if target.parent.exists() and not target.parent.is_dir():
                raise ValueError(f'target parent is not a directory: {target.parent}')
            action = 'copy'
        plan.append(dict(source=str(source), target=str(target), action=action))
    return plan

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('output', type=Path, help='existing roms root containing platform/game folders')
    parser.add_argument('--apply', action='store_true', help='copy after the complete manifest passes preflight')
    args = parser.parse_args()
    try:
        plan = prepare(args.manifest, args.output)
        if args.apply:
            for item in plan:
                if item['action'] == 'unchanged':
                    continue
                target = Path(item['target'])
                target.parent.mkdir(exist_ok=True)
                # Exclusive creation refuses a target that appeared after preflight.
                created = False
                try:
                    with target.open('xb') as destination:
                        created = True
                        with Path(item['source']).open('rb') as source:
                            shutil.copyfileobj(source, destination)
                except BaseException:
                    if created:
                        target.unlink(missing_ok=True)
                    raise
        print(json.dumps(plan, indent=2))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
