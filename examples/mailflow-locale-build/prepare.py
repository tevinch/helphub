#!/usr/bin/env python3
"""Register a caller-supplied Danish locale in MailFlow's native frontend."""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding='utf8'), object_pairs_hook=unique_object)


def leaves(value, prefix=''):
    if not isinstance(value, dict):
        raise ValueError(f'expected an object at {prefix or "root"}')
    result = {}
    for key, item in value.items():
        name = f'{prefix}.{key}' if prefix else key
        if isinstance(item, dict):
            result.update(leaves(item, name))
        elif isinstance(item, str) and item.strip():
            result[name] = item
        else:
            raise ValueError(f'expected a nonempty string at {name}')
    return result


def placeholders(text):
    return sorted({match.strip().lstrip('-').strip().split(',')[0].strip()
                   for match in re.findall(r'\{\{(.*?)\}\}', text)})


def validate(english, translated):
    original = leaves(english)
    supplied = leaves(translated)
    if set(original) != set(supplied):
        missing = sorted(set(original) - set(supplied))
        extra = sorted(set(supplied) - set(original))
        raise ValueError(f'locale keys differ: missing={missing}; extra={extra}')
    for key, text in original.items():
        if placeholders(text) != placeholders(supplied[key]):
            raise ValueError(f'placeholder names differ at {key}')
    return len(original)


def insert_registration(text, anchor, addition, conflict):
    matches = re.findall(conflict, text, re.MULTILINE)
    if text.count(anchor) != 1 or len(matches) > 1 or text.count(addition) > 1:
        raise ValueError('unrecognized or conflicting locale registration; inspect the source before editing')
    if text.count(addition) == 1 and len(matches) == 1:
        return text
    if matches:
        raise ValueError('conflicting locale registration; inspect the source before editing')
    return text.replace(anchor, anchor + addition, 1)


def prepare(source, supplied, check_only=False):
    locale_dir = source / 'frontend/src/locales'
    count = validate(read_json(locale_dir / 'en.json'), read_json(supplied))
    locale_bytes = supplied.read_bytes()
    destination = locale_dir / 'da.json'
    if destination.exists() and destination.read_bytes() != locale_bytes:
        raise ValueError('existing da.json differs; keep a copy and review it instead of overwriting it')
    loader = source / 'frontend/src/i18n.js'
    menu = source / 'frontend/src/components/AdminPanel.jsx'
    changes = {
        loader: insert_registration(loader.read_bytes().decode('utf8'),
                                    'const LOCALES = {\n',
                                    "  da: () => import('./locales/da.json'),\n", r'^\s*da\s*:',),
        menu: insert_registration(menu.read_bytes().decode('utf8'),
                                  'const LANGUAGES = [\n',
                                  "  { code: 'da', nativeName: 'Danish' },\n", r"code\s*:\s*['\"]da['\"]"),
    }
    if check_only:
        return count
    pending = {path: contents.encode('utf8') for path, contents in changes.items()}
    pending[destination] = locale_bytes
    snapshots = {path: path.read_bytes() if path.exists() else None for path in pending}
    temporaries = []
    try:
        for path, contents in pending.items():
            if snapshots[path] == contents:
                continue
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                temporary = Path(handle.name)
                temporaries.append(temporary)
                handle.write(contents)
            os.chmod(temporary, path.stat().st_mode & 0o777 if path.exists() else 0o644)
            os.replace(temporary, path)
    except OSError:
        for path, old in snapshots.items():
            if old is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(old)
        raise
    finally:
        for temporary in temporaries:
            temporary.unlink(missing_ok=True)
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='MailFlow source checkout root')
    parser.add_argument('locale', type=Path, help='your complete Danish JSON translation')
    parser.add_argument('--check', action='store_true', help='validate without writing')
    args = parser.parse_args()
    try:
        count = prepare(args.source.resolve(), args.locale.resolve(), args.check)
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')
    print(f'{"Validated" if args.check else "Registered"} da: {count} translation strings. English was kept unchanged.')


if __name__ == '__main__':
    main()
