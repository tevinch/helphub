"""Two ways to select and dispatch real msgspec Struct fields, without hashes."""

from typing import Annotated

import msgspec
from msgspec import inspect as mi


PositiveInt = Annotated[int, msgspec.Meta(gt=0)]
AtLeastTen = Annotated[int, msgspec.Meta(ge=10)]
DocumentedInt = Annotated[int, msgspec.Meta(title='Count', extra={'unit': 'items'})]


class Inventory(msgspec.Struct, forbid_unknown_fields=True):
    count: int
    positive_count: PositiveInt
    minimum_count: AtLeastTen
    enabled: bool
    ratio: float
    label: str
    numbers: list[int]
    labels: list[str]
    optional_count: int | None
    documented_count: DocumentedInt


class Change(msgspec.Struct, forbid_unknown_fields=True):
    delta: int
    positive_delta: PositiveInt
    tags: list[str]
    documented_delta: DocumentedInt
    optional_delta: int | None


# These keys are CLASSES, not descriptor instances. Both list item types share
# ListType; plain and constrained integers share IntType. Metadata stays distinct.
KIND_HANDLERS = {
    mi.IntType: lambda value: f'integer:{value}',
    mi.ListType: lambda value: f'list:{len(value)}',
}

# Ordered descriptor/handler pairs use native equality, without hashing.
# Keep the Metadata wrapper: its metadata participates in that comparison.
EXACT_TARGETS = mi.multi_type_info((int, PositiveInt, list[int], DocumentedInt))
EXACT_HANDLERS = tuple(zip(EXACT_TARGETS, (
    lambda value: f'plain integer:{value}',
    lambda value: f'positive integer:{value}',
    lambda value: f'integer list:{len(value)}',
    lambda value: f'documented integer:{value}',
)))


def select_by_kind(record: msgspec.Struct) -> list[tuple[str, str]]:
    """Dispatch by the descriptor's class, deliberately ignoring parameters."""
    info = mi.type_info(type(record))
    selected = []
    for field in info.fields:
        handler = KIND_HANDLERS.get(type(field.type))
        if handler is not None:
            selected.append((field.name, handler(getattr(record, field.name))))
    return selected


def select_exact(record: msgspec.Struct) -> list[tuple[str, str]]:
    """Dispatch by native descriptor equality for these finite, acyclic types."""
    info = mi.type_info(type(record))
    selected = []
    for field in info.fields:
        for target, handler in EXACT_HANDLERS:
            if field.type == target:
                selected.append((field.name, handler(getattr(record, field.name))))
                break
    return selected


def sample_records() -> tuple[Inventory, Change]:
    return (
        Inventory(3, 2, 10, True, 1.5, 'stock', [1, 2], ['blue'], None, 7),
        Change(-1, 4, ['new', 'sale'], 8, 9),
    )


def main() -> None:
    for record in sample_records():
        info = mi.type_info(type(record))
        print(f'{type(record).__name__}: inspected {len(info.fields)} fields')
        try:
            {info.fields[0].type}
        except TypeError as exc:
            print(f'descriptor set: {exc}')
        print('kind:', select_by_kind(record))
        print('exact:', select_exact(record))


if __name__ == '__main__':
    main()
