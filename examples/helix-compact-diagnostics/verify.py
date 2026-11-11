#!/usr/bin/env python3
"""Drive an isolated native Helix session; retain its actual terminal screens."""
import argparse
import codecs
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import signal
import shutil
import tempfile
import subprocess
import struct
import sys
import termios
import time
import tomllib

import pyte

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--helix', default='hx', help='Native Helix binary; tested with 25.07.1')
parser.add_argument('--runtime', type=Path, help='Helix runtime directory, if not beside the binary')
parser.add_argument('--output', type=Path, help='New or empty directory for retained evidence')
parser.add_argument('--omit-toggle', action='store_true', help='Negative control: expected to fail target visibility')
args = parser.parse_args()
helix = shutil.which(args.helix)
if not helix:
    parser.error('Helix binary was not found')
HELIX = Path(helix).resolve()
if not HELIX.is_file() or not os.access(HELIX, os.X_OK):
    parser.error('Helix must be an executable file')
runtime = args.runtime.resolve() if args.runtime else HELIX.parent / 'runtime'
if args.runtime and not runtime.is_dir():
    parser.error('--runtime must be a directory')
BASELINE = args.omit_toggle
RUN = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix='helix-diagnostics-'))
if RUN.exists() and (not RUN.is_dir() or any(RUN.iterdir())):
    parser.error('--output must be a new or empty directory; existing contents will not be overwritten')
RUN.mkdir(parents=True, exist_ok=True)
home = RUN / 'home'
(home / '.config/helix').mkdir(parents=True, exist_ok=True)
(home / '.cache').mkdir(exist_ok=True)
events = RUN / 'lsp-events.jsonl'
events.write_text('')
source = RUN / 'sample.fixture'
original = ''.join(f'fixture_{n:02} = ' + '.' * 30 + f'TARGET_{n:02}_TOKEN and existing content\n' for n in range(1, 31))
edit_offset = sum(len(line) for line in original.splitlines(keepends=True)[:5]) + 40
source.write_text(original)
config = RUN / 'config.toml'
preexisting = 'theme = "base16_default_dark"\n[editor]\nline-number = "relative"\ntext-width = 88\nauto-format = false\n[editor.statusline]\nright = ["diagnostics", "position"]\n[keys.normal]\nF7 = ":echo preserved-normal"\n[keys.insert]\nF7 = ":echo preserved-insert"\n'
public_fragment = ROOT / 'keymap.toml'
bindings = tomllib.loads(public_fragment.read_text())['keys']
normal_mapping = 'F8 = ' + json.dumps(bindings['normal']['F8']) + '\n'
configuration = preexisting if BASELINE else preexisting.replace('[keys.insert]', normal_mapping + '[keys.insert]')
config.write_text(configuration)
config_hash = hashlib.sha256(config.read_bytes()).hexdigest()
(home / '.config/helix/languages.toml').write_text('[[language]]\nname = "fixture"\nscope = "source.fixture"\nfile-types = ["fixture"]\nlanguage-servers = ["fixture"]\n[language-server.fixture]\ncommand = ' + json.dumps(sys.executable) + '\nargs = [' + json.dumps(str(ROOT / 'fixture_lsp.py')) + ']\n')
environment = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'XDG_CONFIG_HOME': str(home / '.config'), 'XDG_CACHE_HOME': str(home / '.cache'), 'TERM': 'xterm-256color', 'LANG': 'en_US.UTF-8', 'FIXTURE_EVENTS': str(events)}
if runtime.is_dir():
    environment['HELIX_RUNTIME'] = str(runtime)
native_version = subprocess.run([str(HELIX), '--version'], env=environment, check=True, capture_output=True, text=True).stdout.strip()
pid, descriptor = pty.fork()
if pid == 0:
    os.chdir(RUN)
    os.execve(str(HELIX), ['hx', '-vv', '--log', str(RUN / 'helix.log'), '-c', str(config), str(source)], environment)
fcntl.ioctl(descriptor, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 120, 0, 0))
screen = pyte.Screen(120, 40)
stream = pyte.Stream(screen)
decoder = codecs.getincrementaldecoder('utf-8')('replace')
raw = bytearray()
checks = []


def pump(seconds=0.3):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        ready, _, _ = select.select([descriptor], [], [], min(0.05, max(0, deadline - time.monotonic())))
        if ready:
            try:
                data = os.read(descriptor, 65536)
            except OSError:
                break
            if not data:
                break
            raw.extend(data)
            stream.feed(decoder.decode(data))


def send(keys, seconds=0.35):
    os.write(descriptor, keys.encode())
    pump(seconds)


def snapshot(name):
    text = '\n'.join(screen.display)
    (RUN / (name + '.txt')).write_text(text)
    (RUN / (name + '.json')).write_text(json.dumps({'cursor': {'x': screen.cursor.x, 'y': screen.cursor.y}, 'lines': screen.display}, indent=2))
    return text


def expect(name, condition, detail=None):
    checks.append({'name': name, 'passed': bool(condition), 'detail': detail})
    if not condition:
        snapshot('failure')
        raise AssertionError(name + ': ' + str(detail))


def protocol():
    return [json.loads(line) for line in events.read_text().splitlines() if line]


def wait_for(predicate, timeout=10):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        pump(0.1)
    return False


try:
    expect('native didOpen and diagnostics were emitted', wait_for(lambda: any(e['kind'] == 'publishDiagnostics' for e in protocol())))
    pump(0.7)
    for option in ['end-of-line-diagnostics', 'inline-diagnostics.cursor-line', 'inline-diagnostics.other-lines']:
        send(':get ' + option + '\r')
        text = snapshot('precondition-' + option)
        expect(option + ' starts disabled', '"disable"' in text.splitlines()[-1], text.splitlines()[-1])
    send(':config-reload\r')
    for option in ['end-of-line-diagnostics', 'inline-diagnostics.cursor-line', 'inline-diagnostics.other-lines']:
        send(':get ' + option + '\r')
        text = snapshot('reloaded-' + option)
        expect(option + ' remains disabled after reload', '"disable"' in text.splitlines()[-1], text.splitlines()[-1])
    send(':hsplit\r')
    send(':goto 6\r')
    send('40l')
    before = snapshot('01-legacy-split')
    expect('legacy overlay is shown in split', 'LONG_FILE_WARNING' in before)
    expect('target token is covered by legacy overlay', 'TARGET_06_TOKEN' not in before)
    cursor_before = (screen.cursor.x, screen.cursor.y)
    send('\x1b[19~')
    hidden = snapshot('02-compact-split')
    expect('temporary presentation reveals the target token', 'TARGET_06_TOKEN' in hidden)
    expect('the old multiline overlay disappears', not re.search(r'LONG_FILE_WARNING r\d+ line 02', hidden))
    expect('native cursor stays at the same position', (screen.cursor.x, screen.cursor.y) == cursor_before, {'before': cursor_before, 'after': (screen.cursor.x, screen.cursor.y)})
    send(' d')
    picker = snapshot('03-diagnostic-picker')
    expect('all active diagnostics remain in picker', all(code in picker for code in ['FILE_WARNING', 'LOCAL_ERROR', 'LOCAL_INFO']))
    send('\x1b')
    expect('closing the picker retains the editing position', (screen.cursor.x, screen.cursor.y) == cursor_before)
    send('rX')
    send(':w\r')
    first = source.read_text()
    expect('a real first edit at the covered position was saved', first == original[:edit_offset] + 'X' + original[edit_offset + 1:])
    expect('first change and save reached the LSP', wait_for(lambda: any(e['kind'] == 'savedText' and e['payload']['text'] == first for e in protocol())))
    send('\x1b[19~')
    restored = snapshot('04-restored-legacy')
    expect('second action restores the updated diagnostic presentation', 'LONG_FILE_WARNING r1 line 02' in restored)
    send('\x1b[19~')
    send('rY')
    send(':w\r')
    second = source.read_text()
    expect('a repeated real edit at the same position was saved', second == original[:edit_offset] + 'Y' + original[edit_offset + 1:])
    expect('second change and save reached the LSP', wait_for(lambda: any(e['kind'] == 'savedText' and e['payload']['text'] == second for e in protocol())))
    send('\x1b[19~')
    final = snapshot('05-repeated-restored')
    expect('repeat restores the next updated diagnostic presentation', 'LONG_FILE_WARNING r2 line 02' in final)
    expect('all other source bytes are retained', first.replace('X', original.splitlines()[5][40]) == original and second.replace('Y', original.splitlines()[5][40]) == original)
    expect('runtime changes leave configuration unchanged', hashlib.sha256(config.read_bytes()).hexdigest() == config_hash)
    send(':get text-width\r')
    expect('unrelated editor option stays 88', '88' in snapshot('06-preserved-option').splitlines()[-1])
    send('\x1b[18~')
    expect('the existing F7 binding remains', 'preserved-normal' in snapshot('07-preserved-binding').splitlines()[-1])
    kinds = [e['kind'] for e in protocol()]
    expect('independent protocol operation counts', all(kinds.count(k) >= n for k, n in [('textDocument/didOpen', 1), ('textDocument/didChange', 2), ('textDocument/didSave', 2), ('publishDiagnostics', 3)]), {k: kinds.count(k) for k in set(kinds)})
finally:
    try:
        send(':qa!\r', 0.3)
    except OSError:
        pass
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        child, status = os.waitpid(pid, os.WNOHANG)
        if child:
            break
        time.sleep(0.1)
    else:
        os.kill(pid, signal.SIGTERM)
        os.waitpid(pid, 0)
    os.close(descriptor)
    (RUN / 'terminal-output.ansi').write_bytes(raw)
    (RUN / 'checks.json').write_text(json.dumps(checks, indent=2))
    report = {'nativeVersion': native_version, 'omitToggle': BASELINE, 'checks': checks, 'artifacts': str(RUN)}
    (RUN / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
