"""Six small consumers of ijson's existing public interfaces."""
import json
import os
import tempfile
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

import httpx
import ijson
import requests


def active_rows(source, *, ndjson=False):
    """Filter/transform one record at a time; source must return binary data."""
    events = ijson.parse(source, multiple_values=ndjson)
    prefix = "" if ndjson else "item"
    for row in ijson.items(events, prefix):
        if row["status"] == "active":
            yield {"id": row["id"], "name": row["name"]}


def write_array(rows, target):
    """Publish a JSON array only when its input iterator finishes successfully."""
    target = Path(target)
    descriptor, temporary = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        count = 0
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write("[")
            for row in rows:
                if count:
                    output.write(",\n")
                output.write(json.dumps(row, ensure_ascii=False, allow_nan=False))
                count += 1
            output.write("]\n")
        os.replace(temporary, target)
        return count
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_active(source, target, *, ndjson=False):
    return write_array(active_rows(source, ndjson=ndjson), target)


def ndjson_rows(source):
    """Each complete top-level JSON value is one result; newlines are whitespace."""
    return ijson.items(source, "", multiple_values=True)


class GraphQLError(ValueError):
    """An errors.item value occurred in this example's GraphQL envelope."""


def graphql_rows(source):
    """Dispatch disjoint data.item/errors.item paths in one native event pass.

    The example schema is {"data": [...], "errors": [...]} with optional arrays.
    This is not a general GraphQL response/schema implementation. Use floats for
    JSON export; exact-decimal applications need a Decimal-aware output policy.
    """
    builder = None
    depth = 0
    destination = None
    for prefix, event, value in ijson.parse(source, use_float=True):
        if builder is not None:
            builder.event(event, value)
            if event in ("start_map", "start_array"):
                depth += 1
            elif event in ("end_map", "end_array"):
                depth -= 1
            if depth:
                continue
            value = builder.value
            builder = None
        elif prefix in ("data.item", "errors.item"):
            destination = prefix
            if event in ("start_map", "start_array"):
                builder = ijson.ObjectBuilder()
                builder.event(event, value)
                depth = 1
                continue
        else:
            continue
        if destination == "errors.item":
            raise GraphQLError(value)
        yield value


def write_graphql(source, target):
    # A late errors array discards staged data instead of publishing partial data.
    return write_array(graphql_rows(source), target)


def string_event_lengths(source):
    """Observe complete string events, not fragments of a string."""
    return [len(value) for _, event, value in ijson.parse(source) if event == "string"]


def text_chunks(source):
    """Consume the controllable alternative {"chunks": [small strings, ...]}."""
    for piece in ijson.items(source, "chunks.item"):
        if not isinstance(piece, str):
            raise ValueError("Every chunks item must be a string")
        yield piece


def statistics(source, *, ndjson=False):
    """Keep numeric aggregate state; Decimal uses the caller's decimal context."""
    rows = ndjson_rows(source) if ndjson else ijson.items(source, "item")
    count, total, minimum, maximum = 0, 0, None, None
    for row in rows:
        value = row["value"]
        if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
            raise ValueError("value must be a JSON number")
        count += 1
        total += value
        minimum = value if minimum is None else min(minimum, value)
        maximum = value if maximum is None else max(maximum, value)
    return {
        "count": count, "sum": total, "min": minimum, "max": maximum,
        "mean": Decimal(total) / count if count else None,
    }


@contextmanager
def http_chunks(url, client):
    """Stream bytes with explicit timeouts and no automatic redirect following."""
    if client == "requests":
        with requests.Session() as session:
            session.trust_env = False
            with session.get(url, stream=True, timeout=(3, 5), allow_redirects=False) as response:
                if 300 <= response.status_code < 400:
                    raise ValueError("Redirects are not followed by this example")
                response.raise_for_status()
                yield response.iter_content(chunk_size=4096)
    elif client == "httpx":
        with httpx.Client(timeout=5, follow_redirects=False, trust_env=False) as session:
            with session.stream("GET", url) as response:
                response.raise_for_status()
                yield response.iter_bytes(chunk_size=4096)
    else:
        raise ValueError("client must be requests or httpx")


def download_active(url, target, *, client="requests", attempts=2):
    """Restart a failed read from byte zero; only a complete result replaces target.

    Use this for a replayable GET snapshot. It does not resume a live stream,
    append output across attempts, or make external side effects exactly once.
    """
    if attempts < 1:
        raise ValueError("attempts must be positive")
    retryable = (
        requests.ConnectionError, requests.Timeout,
        requests.exceptions.ChunkedEncodingError, httpx.TransportError,
        ijson.JSONError,
    )
    for attempt in range(attempts):
        try:
            with http_chunks(url, client) as chunks:
                return write_active(ijson.from_iter(chunks), target)
        except retryable:
            if attempt + 1 == attempts:
                raise
