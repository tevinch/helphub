# Streaming JSON recipes

Filter a large JSON array into a file, read JSON Lines, select two response branches, and calculate statistics without collecting every record. These examples use the existing public interfaces in [ijson 3.6.0](https://github.com/ICRAR/ijson/tree/v3.6.0).

## Run

Use Python 3.10 or newer. From this directory:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --index-url https://pypi.org/simple --only-binary=:all: -r requirements.txt
python -c "import ijson; print(ijson.__version__, ijson.backend)"
IJSON_BACKEND=yajl2_c python -m unittest -v
python demo.py sample-output
```

The demo requires a new directory and refuses to overwrite an existing one. It writes 10,000 generated records incrementally, produces two files containing the same 5,000 active records, and prints statistics plus the string and response-branch examples. Tests use temporary files and a loopback HTTP server; they make no external HTTP requests.

The complete cookbook was checked with Python 3.10.9 on macOS, ijson 3.6.0's official `yajl2_c` wheel, Requests 2.34.2 and HTTPX 0.28.1: all 21 tests pass. The backend check should print `3.6.0 yajl2_c`; the explicit test command fails if that backend is unavailable instead of silently selecting another one.

An additional run with `IJSON_BACKEND=python python -m unittest -v` passed the same 21 functional checks, including preserved output after failed downloads. On that backend, interrupted HTTP reads also emitted an upstream cleanup diagnostic, `Exception ignored ... IncompleteJSONError: Incomplete string lexeme`. The examples do not suppress it or patch the parser. Quiet interrupted-HTTP behavior is verified here only for `yajl2_c`.

`recipes.py` contains the consumers. The inputs below follow the small schemas shown here; these examples do not validate an arbitrary application schema.

## 1. Stream an HTTP response and restart a failed download

```python
from recipes import download_active

# A replayable JSON snapshot with the array schema in section 2:
count = download_active(feed_url, "active.json", client="requests", attempts=2)
# The same consumer also accepts client="httpx".
```

Both clients keep the response open while `ijson.from_iter()` reads decoded bytes. Requests uses `stream=True` and `iter_content()`; HTTPX uses `stream()` and `iter_bytes()`. Both have timeouts, disable automatic redirects, and disable environment-provided proxies and implicit credentials. TLS verification remains enabled.

A transport or JSON parsing failure starts a new GET, parser, and temporary output from byte zero. Only a fully parsed result replaces the destination. A failed second attempt leaves any earlier destination intact. HTTP status errors and redirects are reported without retrying them. An unchanged input snapshot is the application's responsibility: the successful attempt's contents become the result.

This is appropriate for a replayable GET snapshot. It does not resume an arbitrary byte offset or a live event stream. Do not put payments, messages, database writes, or other externally visible effects inside a retried record loop and assume they run once. The file replacement provides publication isolation, not a power-loss durability guarantee.

The HTTP test deliberately disconnects after the first active record has been parsed, then serves the complete response. It checks the two actual requests, parsed records on each attempt, exact final output, temporary-file cleanup, and failure preservation for both clients. UTF-8 characters cross transport chunks.

## 2. Filter, transform, and write a JSON array

Input:

```json
[{"id":1,"status":"active","name":"Café"},{"id":2,"status":"inactive","name":"Lin"}]
```

```python
from recipes import write_active

with open("rows.json", "rb") as source:
    count = write_active(source, "active.json")
```

Result:

```json
[{"id":1,"name":"Café"}]
```

`active_rows()` explicitly chains `ijson.parse(source)` into `ijson.items(events, "item")`, then applies the predicate and transformation. `write_array()` serializes one selected record at a time. It holds a parser buffer and individual records, rather than the complete document. An invalid tail prevents publication even if earlier records were valid. Empty and all-inactive arrays produce `[]`.

`write_array()` expects values accepted by Python's `json.dumps()`. If your selected fields contain `Decimal`, choose an explicit number-encoding policy instead of silently turning numbers into strings. The shown transformation selects integer/string identifiers and names.

## 3. Inspect `data` and `errors` in one pass

This recipe follows the example envelope from the [multiple-prefix usage discussion](https://github.com/ICRAR/ijson/issues/109): optional `data` and `errors` arrays at the root.

```python
from recipes import write_graphql

with open("response.json", "rb") as source:
    write_graphql(source, "data.json")
```

`graphql_rows()` reads one `ijson.parse()` event stream and uses public `ijson.ObjectBuilder` to reconstruct a matching `data.item` or `errors.item`. Nested arrays and objects within each item are supported. It does not invoke `items()` repeatedly on a shared iterator, which would consume the stream before the next query.

Any `errors.item` raises `GraphQLError`. `write_graphql()` stages the entire output, so an error after `data` also leaves the destination intact. Empty `errors` does not fail. Directly consuming `graphql_rows()` can yield data before a later error; use the file consumer when those results must remain unpublished until the envelope has finished.

The paths are fixed and disjoint, and follow ijson's dot-separated prefix semantics. This is a response-shape example, not a general GraphQL client or multi-prefix API. Real GraphQL APIs often use an object under `data`; select the actual array path for your schema. The recipe uses `use_float=True` so ordinary numeric values can be exported with `json.dumps()`. This has Python float precision and ijson's documented overflow limits. For exact decimal data, retain ijson's default `Decimal` values and use an encoder that preserves numeric decimals.

## 4. Process NDJSON / JSON Lines

```python
from recipes import ndjson_rows, write_active

with open("rows.jsonl", "rb") as source:
    for row in ndjson_rows(source):
        print(row["id"])

with open("rows.jsonl", "rb") as source:
    write_active(source, "active-lines.json", ndjson=True)
```

`ijson.items(source, "", multiple_values=True)` selects complete top-level values. The empty prefix is intentional. Newlines count as whitespace; this option also accepts adjacent top-level JSON values, so it is not a validator requiring exactly one value per physical line. Missing `multiple_values=True` rejects the second record. A truncated final record is reported instead of discarded.

## 5. Understand the single-string limit

`basic_parse()` and `parse()` emit a complete Python string for a JSON string token. A smaller `buf_size` changes input reads; it does not split that token into string-fragment events. `items()` also constructs each selected item in full. Memory therefore depends on the largest token/item, parser buffers, and the consumer's retained state.

`string_event_lengths()` demonstrates this on one moderate string: the demo's 20,480-character value arrives as one string event. It is an observation example, not a bounded-memory collector for an unlimited number of strings.

If you control the producer, use a sequence of bounded chunks or store the large value separately:

```json
{"chunks":["Caf","é ","雨"]}
```

```python
from recipes import text_chunks

with open("chunks.json", "rb") as source, open("text.txt", "w", encoding="utf-8") as output:
    for piece in text_chunks(source):
        output.write(piece)
```

This changes the input format and preserves the pieces' order; it is not a workaround that splits an existing giant token. If an unchangeable JSON document contains a single string larger than available memory, these ijson interfaces cannot provide a constant-memory solution. That requires different framing or a parser interface exposing string fragments.

## 6. Calculate running statistics

Input records contain a numeric `value`:

```python
from recipes import statistics

with open("rows.json", "rb") as source:
    result = statistics(source)

with open("rows.jsonl", "rb") as source:
    result = statistics(source, ndjson=True)
```

The consumer retains count, sum, minimum, and maximum. Non-integer JSON numbers remain `Decimal`; the mean uses the current decimal context. Empty input arrays return count/sum `0` and `None` for min/max/mean. Boolean, string, and null `value` fields are rejected.

The suite checks exact results for positive/negative integers and decimals, bounded reads, and a first result before EOF. Its allocation check compares 10,000 and 100,000 small records with `tracemalloc`; it checks Python allocations on the tested backends, not total native RSS or performance on a 10 GB document. It makes no universal constant-memory or throughput claim.

## References and license

- [Official usage, event chaining, options, HTTP adapters and backend guidance](https://github.com/ICRAR/ijson/blob/v3.6.0/README.rst)
- [Public ObjectBuilder export](https://github.com/ICRAR/ijson/blob/v3.6.0/src/ijson/__init__.py)
- [ObjectBuilder event contract](https://github.com/ICRAR/ijson/blob/v3.6.0/src/ijson/common.py)

These example files are available under the repository's MIT license. Dependencies retain their own licenses.

## Optional coffee

These examples are free. If they saved you time, a coffee is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
