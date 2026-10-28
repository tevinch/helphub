# Compare TexSoup nodes from the same parse

When two `TexNode` objects refer to the same parsed LaTeX expression, compare their underlying expression objects:

```python
same_expression = first.expr is second.expr
```

TexSoup creates fresh `TexNode` wrappers during navigation. In the [original question](https://github.com/alvinwan/TexSoup/issues/192), these two paths return different wrappers around the same expression:

```python
textit = soup.find("textit")
other = textit.parent.children[1]

assert textit is not other
assert textit.expr is other.expr
```

Use `is` here. `first.expr == second.expr` compares rendered content, so it also matches two different `\textit{same}` commands. Wrapper hashes do not identify their underlying expression.

## Run the complete example

Run with Python 3.12. The example uses the published TexSoup 0.3.3 wheel, pinned by SHA256, with no additional dependencies.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.txt
.venv/bin/python example.py
.venv/bin/python check.py
```

On Windows, use `.venv\Scripts\python.exe` in place of `.venv/bin/python`.

The example parses the question's document, reaches the italic command through both paths, compares them, and changes its text. Both wrappers then show the edit in the same serialized document:

```text
Same wrapper: False
Same parsed expression: True
Value through the other wrapper: updated
Serialized document contains the edit: True
Repeated equal commands share an expression: False
Separately parsed documents share an expression: False
```

The six checks run the example and exercise equal commands in one document, separately parsed identical documents, different documents with equal local content and offsets, nested paths, shared edits, and the original-position limitation. Verified with Python 3.12.4 and TexSoup 0.3.3 using scripted checks.

## Scope

This identifies the same expression object within a live parse. Parsing the same source again creates different expression objects. The comparison is not a persistent identifier or a way to match nodes across saved files, processes, or reparses.

Two wrappers for the same expression see edits to that expression. A wrapper may still reference an expression after it has been removed or replaced, so identity alone does not prove that it remains in a document or has the same current parent. Retain the document/tree association in your own application when that matters.

Do not use `(position, content)` as a substitute: different documents can have identical local positions and content. TexSoup's `position` records the original source offset and is not updated after tree edits, as the [API reference](https://texsoup.alvinwan.com/docs/data.html#TexSoup.data.TexNode.position) explains. See also the implementation of [node navigation and expression equality](https://github.com/alvinwan/TexSoup/blob/c62684b119e2c43e307b0122f92cbd1151d0c968/TexSoup/data.py).

## Optional coffee

If this example saves you some time, you're welcome to buy me a coffee. It's entirely optional; the example remains free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
