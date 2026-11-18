# Selecting msgspec Struct fields

To check which Struct fields have selected types, first decide what a match means:

- **Kind:** any integer descriptor, including constrained integers; or any list descriptor, regardless of its item type.
- **Exact descriptor value:** the inspected constraint, item-type and metadata values must compare equal.

Both operations work without hashing descriptor instances. This example uses Python 3.10+ and pins `msgspec==0.22.0`. The public `msgspec.inspect` API is **experimental** and may change between releases.

## Run

From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
.venv/bin/python example.py
.venv/bin/python -m unittest -v
```

The example inspects two actual Structs and dispatches handlers using their field values:

```text
Inventory: inspected 10 fields
descriptor set: unhashable type: 'IntType'
kind: [('count', 'integer:3'), ('positive_count', 'integer:2'), ('minimum_count', 'integer:10'), ('numbers', 'list:2'), ('labels', 'list:1')]
exact: [('count', 'plain integer:3'), ('positive_count', 'positive integer:2'), ('numbers', 'integer list:2'), ('documented_count', 'documented integer:7')]
Change: inspected 5 fields
descriptor set: unhashable type: 'IntType'
kind: [('delta', 'integer:-1'), ('positive_delta', 'integer:4'), ('tags', 'list:2')]
exact: [('delta', 'plain integer:-1'), ('positive_delta', 'positive integer:4'), ('documented_delta', 'documented integer:8')]
```

## Dispatch by kind

`field.type` is a descriptor **instance**, such as `IntType(gt=0, ...)`. For broad classification, use its descriptor class:

```python
from msgspec import inspect as mi

handlers = {
    mi.IntType: lambda value: f"integer:{value}",
    mi.ListType: lambda value: f"list:{len(value)}",
}

for field in mi.type_info(type(record)).fields:
    handler = handlers.get(type(field.type))
    if handler is not None:
        print(field.name, handler(getattr(record, field.name)))
```

These dictionary keys are classes, which are hashable. Plain `int` and `Annotated[int, Meta(gt=0)]` both produce `IntType` instances. `bool` produces a separate `BoolType`; it does not enter the integer handler. Likewise, `list[int]` and `list[str]` both use the list handler. If subclass matching is desired, an `isinstance(field.type, mi.IntType)` check is another option.

Metadata wrappers stay distinct here. An annotation with a title or extra metadata produces `Metadata(type=..., ...)`, so it does not enter the integer handler. Unwrapping `.type` would be a deliberate change to this kind-based policy; this example leaves the wrapper intact.

## Match exact descriptor values

For membership, use a tuple or list:

```python
wanted = mi.multi_type_info((int, PositiveInt, list[int], DocumentedInt))
selected_names = [
    field.name
    for field in mi.type_info(Inventory).fields
    if field.type in wanted
]
# ['count', 'positive_count', 'numbers', 'documented_count']
```

For dispatch, `select_exact` in [example.py](example.py) uses an ordered tuple of `(descriptor, handler)` pairs and compares `field.type == target`. The first matching handler runs. Both forms use native value equality and require no descriptor hashes.

In these examples, plain `int` differs from `Meta(gt=0)`, and `Meta(gt=0)` differs from `Meta(ge=10)`. `list[int]` differs from `list[str]`. The metadata wrapper and its metadata dictionaries also participate in equality. The optional integer fields have `UnionType` descriptors and do not match the selected integer targets. Float, string and boolean fields are also excluded.

“Exact” means equality of the **inspected descriptor values**, not equivalence of arbitrary Python annotations or schemas. The example covers finite, acyclic descriptors. It makes no guarantee for recursive schemas or arbitrary user-defined metadata equality. Selection scans the targets: with F fields and T targets, there can be F × T comparisons, plus the cost of comparing each descriptor. It does not provide constant-time exact lookup.

## Why the set fails

In 0.22.0, the public `Type` base is an ordinary, mutable `msgspec.Struct`. With the default field-value equality, mutable Structs are unhashable; `frozen=True` can add a value hash when every field is hashable. The inspected `IntType` instance in this example consequently raises `TypeError` when used as a set element or dictionary key. This describes the observed mechanics; it does not establish the maintainers' reason for choosing that API.

The selectors classify declared annotations; they do not validate runtime values. Handlers read values after a descriptor matches.

The example leaves the dependency and model settings intact. Its tests check both Structs' selected field names and handler results, repeat selection with fresh introspection, preserve annotations and existing values, round-trip JSON, and retain positive-integer and `forbid_unknown_fields=True` validation. Verification used scripted tests on Python 3.12.4 with msgspec 0.22.0; other Python versions were not tested. An application's own schema still needs its own checks.

Official sources for the pinned release: [inspection guide](https://github.com/msgspec/msgspec/blob/0.22.0/docs/inspect.rst), [public descriptors](https://github.com/msgspec/msgspec/blob/0.22.0/src/msgspec/inspect.py), and [Struct equality and freezing](https://github.com/msgspec/msgspec/blob/0.22.0/docs/structs.rst).

## Optional coffee

This example is free to use. If it saves you time, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
