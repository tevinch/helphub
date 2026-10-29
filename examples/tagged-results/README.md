# Round-trip flat tagged dataclass results

With `dataclass-wizard==1.0.0`, use a dataclass field annotated as `ResErr | ResOk` to select the tagged branch. The container can stay inside the application: the JSON you send and receive can remain a flat object.

Using the `Container(res: Res)` from the question, the two native operations are:

```python
payload = dw.asdict(Container(res=result))['res']
restored = dw.fromdict(Container, {'res': payload}).res
```

For `ResErr(item_id='Q0001', msg='err')`, the payload is:

```json
{"item_id": "Q0001", "msg": "err", "__tag__": "ResErr"}
```

Loading it through the second expression gives a `ResErr` with the original values. A payload tagged `ResOk` gives a `ResOk`. The outer `res` key is used only for the native conversion; it is absent from the transmitted JSON.

## Run the complete example

Download `example.py` and `check.py` into the same directory. Create a virtual environment with Python 3.10 or newer, then install the pinned library:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install dataclass-wizard==1.0.0
.venv/bin/python example.py
.venv/bin/python check.py
```

On Windows, use `.venv\Scripts\python.exe` in place of `.venv/bin/python`.

`example.py` defines both result dataclasses and their tags. It emits four JSON lines: both branches make a complete flat-dictionary → JSON → dictionary → typed-result round trip, then repeat in the same process. Each line includes the flat `wire` payload, `restored_type` and restored field values.

The example uses the [documented dataclass-field union pattern](https://dcw.ritviknag.com/en/latest/common_use_cases/dataclasses_in_union_types.html). The native container is a small consumer-side dataclass; the library is unchanged.

## What the direct calls mean

In 1.0.0, `asdict(..., cls=...)` and `fromdict(cls, ...)` expect a dataclass class. `ResErr | ResOk` is a union annotation, so passing it directly as the root `cls` produces the reported `UnionType` error. The union annotation belongs on `Container.res` in this recipe.

For the plain dataclasses in this example, standalone `dw.asdict(ResErr(...))` still omits the tag. Changing the tag configuration from `LoadMeta` to `DumpMeta` also does not add it to that standalone output in 1.0.0. Serializing the union field gives the native union serializer the context it needs to add the tag. Extracting `['res']` then keeps the wire format flat.

The library's normal conversion and unknown-key settings continue to apply. Missing or unknown tags fail native union loading. A tag naming the wrong branch fails when that branch's required fields are absent; the tag is the branch selector, rather than an independent guarantee about the payload's meaning.

## Verification

Checked on macOS with Python 3.12.4, `dataclass-wizard` 1.0.0 and `typing-extensions` 4.15.0. Python 3.13, used in the original report, has not been run here.

`check.py` runs the complete example in a fresh process and compares all four output records with literal expected payloads, types and values. It separately observes all four actual JSON decoding calls, checks that model values and input dictionaries are unchanged, and exercises missing/unknown tags and wrong-branch required fields. Direct root-union calls reproduce the original errors.

Temporary variants that omitted the load container, flat-value extraction or tag failed the checks. A variant that skipped the JSON round trip still printed the same values, but failed the independent decoding check. These are programmatic checks of the example, rather than confirmation from the original application.

References: [dataclass-wizard 1.0.0 release metadata](https://pypi.org/pypi/dataclass-wizard/1.0.0/json), [union types and tags](https://dcw.ritviknag.com/en/latest/common_use_cases/dataclasses_in_union_types.html), [Meta settings](https://dcw.ritviknag.com/en/latest/common_use_cases/meta.html).

## Optional coffee

If this saved you some time, a coffee is welcome, but entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
