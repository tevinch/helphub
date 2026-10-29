"""Check the complete native tagged-result recipe with dataclass-wizard 1.0.0."""

from copy import deepcopy
from contextlib import redirect_stdout
import io
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
assert (HERE / 'example.py').is_file(), 'example.py must contain the runnable recipe'
assert version('dataclass-wizard') == '1.0.0', 'Use the pinned dataclass-wizard 1.0.0'
import example as sample
from dataclass_wizard.errors import MissingFields, ParseError


run = subprocess.run(
    [sys.executable, str(HERE / 'example.py')],
    text=True, capture_output=True, check=True,
)
assert run.stderr == '', run.stderr
output = [json.loads(line) for line in run.stdout.splitlines()]
expected = [
    {
        'round': 1, 'wire': {'item_id': 'Q0001', 'msg': 'err', '__tag__': 'ResErr'},
        'restored_type': 'ResErr', 'restored': {'item_id': 'Q0001', 'msg': 'err'},
    },
    {
        'round': 1, 'wire': {'item_id': 'Q0002', 'item': 'ok', '__tag__': 'ResOk'},
        'restored_type': 'ResOk', 'restored': {'item_id': 'Q0002', 'item': 'ok'},
    },
    {
        'round': 2, 'wire': {'item_id': 'Q0001', 'msg': 'err', '__tag__': 'ResErr'},
        'restored_type': 'ResErr', 'restored': {'item_id': 'Q0001', 'msg': 'err'},
    },
    {
        'round': 2, 'wire': {'item_id': 'Q0002', 'item': 'ok', '__tag__': 'ResOk'},
        'restored_type': 'ResOk', 'restored': {'item_id': 'Q0002', 'item': 'ok'},
    },
]
assert output == expected, 'Both branches must complete flat JSON round trips twice'
print('PASS: complete sample output, flat tagged JSON and exact restored branches in two rounds')

# Observe real JSON decoding calls separately, so skipping the wire round trip fails.
decoded_inputs = []
def observe_json(frame, event, argument):
    if (event == 'call' and frame.f_globals.get('__name__') == 'json'
            and frame.f_code.co_name == 'loads'):
        decoded_inputs.append(frame.f_locals['s'])

previous_profile = sys.getprofile()
try:
    sys.setprofile(observe_json)
    with redirect_stdout(io.StringIO()):
        sample.main()
finally:
    sys.setprofile(previous_profile)
assert [json.loads(text) for text in decoded_inputs] == [
    {'item_id': 'Q0001', 'msg': 'err', '__tag__': 'ResErr'},
    {'item_id': 'Q0002', 'item': 'ok', '__tag__': 'ResOk'},
    {'item_id': 'Q0001', 'msg': 'err', '__tag__': 'ResErr'},
    {'item_id': 'Q0002', 'item': 'ok', '__tag__': 'ResOk'},
], 'All four flat payloads must actually pass through JSON decoding'
print('PASS: all four real JSON decoding operations independently observed')

# Exercise the same native boundary using fresh objects and payload dictionaries.
for obj, literal in (
    (sample.ResErr('Q0001', 'err'), {'item_id': 'Q0001', 'msg': 'err', '__tag__': 'ResErr'}),
    (sample.ResOk('Q0002', 'ok'), {'item_id': 'Q0002', 'item': 'ok', '__tag__': 'ResOk'}),
):
    before = deepcopy(obj)
    wire = sample.dw.asdict(sample.Container(res=obj))['res']
    assert wire == literal and 'res' not in wire
    assert obj == before
    payload = json.loads(json.dumps(wire))
    payload_before = deepcopy(payload)
    restored = sample.dw.fromdict(sample.Container, {'res': payload}).res
    assert type(restored) is type(obj) and restored == before
    assert payload == payload_before and wire == literal
print('PASS: original dataclass values and incoming flat dictionaries remain unchanged')

# These failures are native behavior, not additional validation supplied by this recipe.
for payload, error in (
    ({'item_id': 'Q0001', 'msg': 'err'}, ParseError),
    ({'item_id': 'Q0001', 'msg': 'err', '__tag__': 'Other'}, ParseError),
    ({'item_id': 'Q0001', 'msg': 'err', '__tag__': 'ResOk'}, MissingFields),
    ({'item_id': 'Q0002', 'item': 'ok', '__tag__': 'ResErr'}, MissingFields),
):
    before = deepcopy(payload)
    try:
        sample.dw.fromdict(sample.Container, {'res': payload})
    except error:
        pass
    else:
        raise AssertionError(f'Expected native {error.__name__} for {payload!r}')
    assert payload == before
print('PASS: missing/unknown tags and tags naming a branch with missing required fields reject')

flat = {'item_id': 'Q0001', 'msg': 'err', '__tag__': 'ResErr'}
for operation in (
    lambda: sample.dw.fromdict(sample.Res, flat),
    lambda: sample.dw.asdict(sample.ResErr('Q0001', 'err'), cls=sample.Res),
):
    try:
        operation()
    except TypeError as error:
        assert "types.UnionType" in str(error), str(error)
    else:
        raise AssertionError('Direct UnionType root calls remain unsupported in 1.0.0')
print('PASS: omitting the native container causes the original UnionType errors')
print('All checks passed with dataclass-wizard 1.0.0.')
