# Check CSV expressions before constructing RDF

A failed `BIND` can leave its variable unbound while the query still succeeds. A `CONSTRUCT` then omits any triple that needs that variable. If it is the subject, an entire source record can disappear from the intended graph.

This small example keeps a CSV record locator and the original arguments in a diagnostic `SELECT`. A Python runner stops before constructing output when `IRI` or `STRLANG` has no result. After you correct the input, it runs the actual `CONSTRUCT`. The input file is never edited, and an existing output file is never replaced.

This addresses the current conversion workflow in [this question](https://github.com/SPARQL-Anything/sparql.anything/issues/712). It does **not** make the engine throw an exception for each expression error or add generic language-tag validation.

## Run the example

Requirements: Python 3.10+, Java 21+, and the official **SPARQL Anything 1.3.0 CLI**. Download `sparql-anything-v1.3.0.jar` from the [official release](https://github.com/SPARQL-Anything/sparql.anything/releases/tag/v1.3.0). No source build or extra Python packages are needed.

The runner checks the jar's published SHA-256:

```text
0855bc869a35f83c4a97a5d31ca65e9f4ff16fd9c5a4f619ad7a7bd508053414
```

From this example's directory, set the local jar location and run:

```sh
export SPARQL_ANYTHING_JAR=/path/to/sparql-anything-v1.3.0.jar
python3 convert.py --jar "$SPARQL_ANYTHING_JAR" --input fixtures/invalid.csv --output invalid.ttl
```

The command exits **2**, reports both failures, and creates no `invalid.ttl`:

```json
{"status":"rejected","records_checked":4,"issues":[
  {"record":2,"function":"IRI","arguments":["some space"]},
  {"record":3,"function":"STRLANG","arguments":["Missing language",""]}
]}
```

`record` is the **one-based data-record position**, excluding the header. It is not a physical line number: a quoted cell can span several lines. The sample's fourth record contains such a cell.

Correct the values in your own copy, or use the included corrected fixture:

```sh
python3 convert.py --jar "$SPARQL_ANYTHING_JAR" --input fixtures/corrected.csv --output corrected.ttl
```

This exits **0** with `{"status":"written","records_checked":4}`. `corrected.ttl` contains all four intended subjects and their exact labels, including the comma, accented text, and quoted newline. Configuration, file, or engine failures exit **1**. Choose a new output path for another run. Use `--java /path/to/java` if Java 21+ is not on your PATH.

## Why a separate SELECT helps

The core pattern in [preflight.rq](preflight.rq) is:

```sparql
BIND(IRI(?source_subject) AS ?subject)
BIND(STRLANG(?source_text, ?source_lang) AS ?label)
BIND(BOUND(?subject) AS ?subject_ok)
BIND(BOUND(?label) AS ?label_ok)
```

It selects the source fields and `fx:cardinal(?slot)` along with these results. The source fields are `OPTIONAL`, so their absence cannot remove a row before the check. There is no filter discarding failed rows and no placeholder subject merging different bad records into one resource.

The runner checks that the native SELECT returned every input record, in order, with all original field values. It reports the original arguments for each unbound expression. Only an entirely successful preflight runs [construct.rq](construct.rq), using the same temporary snapshot of the input. It completes the graph before creating the destination file.

A detailed `COALESCE` fallback can be useful in a **diagnostic** result. Reusing one `<bad-URL>` in the production graph can merge unrelated bad rows, and replacing an invalid label with ordinary text changes the intended RDF. Keeping the diagnostics separate lets you repair the source deliberately instead.

## Important boundaries

- This is a concrete recipe for UTF-8 CSV with exactly the three headers `subject,text,lang` and the two expressions above. Adapt both queries and their checks together for another mapping. It is not a validator for arbitrary SPARQL queries.
- `BOUND` detects evaluation failure; it does not prove data quality. In the tested 1.3.0 release, `IRI("some space")` and `STRLANG("foo", "")` are unbound, but `STRLANG("foo", "English")` succeeds as `"foo"@english`. Do not use this check as BCP 47 syntax, registered-language, or application-policy validation. Validate those requirements separately. [The language-validation discussion](https://github.com/SPARQL-Anything/sparql.anything/issues/465) concerns a separate enhancement.
- An empty or relative subject string may resolve against the query's explicit `BASE <https://example.org/>`; this example does not reject every undesirable subject. Set the base and add your own explicit mapping requirements before adopting it for other data.
- The native CSV settings and header names are intentionally fixed here. Other delimiters, null-string settings, slicing, remote sources, and very large conversions need their own acceptance checks. The runner holds the input, diagnostics and completed graph in memory and gives each CLI operation 60 seconds.
- The destination filesystem must support creating a hard link within its directory; an unsupported operation is reported as an error without replacing an existing file.
- RDF graphs deduplicate identical triples. `records_checked` counts input records, not distinct output triples. Tests cover two identical records producing one RDF triple.
- Validation used the real local CLI and independently reloaded the resulting RDF with its parser. This is scripted software validation; it is not confirmation from the original requester or their production data.

The behavior follows the [SPARQL BIND rules](https://www.w3.org/TR/sparql11-query/#bind) and [CONSTRUCT template rules](https://www.w3.org/TR/sparql11-query/#construct). See the official [CSV configuration](https://github.com/SPARQL-Anything/sparql.anything/blob/v1.3.0/docs/formats/CSV.md), [slot cardinal function](https://github.com/SPARQL-Anything/sparql.anything/blob/v1.3.0/docs/FUNCTIONS_AND_MAGIC_PROPERTIES.md#fxcardinal), and [CLI guide](https://github.com/SPARQL-Anything/sparql.anything/blob/v1.3.0/docs/CLI.md).

## Check the complete operation

```sh
export JAVA=java
python3 -m unittest -v
```

Keep `SPARQL_ANYTHING_JAR` set as above. The tests use the real CLI to check invalid diagnostics, corrected graph contents, Unicode and multiline cells, duplicate records, UTF-8 BOM input, existing files and symlinks, malformed records, a missing preflight result, and an actual engine failure. Runtime files are not included in this folder.

## Optional coffee

If this example saves you some time, you're welcome to buy me a coffee. It's entirely optional; the example remains free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
