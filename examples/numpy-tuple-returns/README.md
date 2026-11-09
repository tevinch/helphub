# Four-part tuple returns in NumPy docstrings

For NumPy style, pydoclint decomposes a fixed-length `tuple[...]` annotation
into its element types. Give each returned value its own entry:

```python
Returns
-------
first : dict[str, list[int]]
    A long description can wrap onto
    another indented line.
second : dict[str, list[int]]
    The second collection.
third : dict[str, dict[str, list[int]]]
    The third collection.
fourth : dict[str, dict[str, list[int]]]
    The fourth collection.
```

The function's return annotation can remain a multiline four-element tuple.
Each entry's type must match its corresponding annotation. If the real
annotation uses `Scatter`, use `Scatter` in that entry too; `int` and
`Scatter` are different type names. The names above are documentation labels,
not a change to the returned tuple.

The complete runnable function is in [example.py](example.py). No checks
are disabled. [pyproject.toml](pyproject.toml) retains the reported options
and explicitly keeps return-type checking enabled.

Sphinx-AutoAPI extracts the module into reStructuredText. The included
[configuration](docs/conf.py) also enables `sphinx.ext.napoleon` to interpret
NumPy-style sections. These extensions handle different stages of the build.

Run from this directory with Python 3.12:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
pydoclint --config=pyproject.toml example.py
python check.py
sphinx-build -W -b html docs _build
```

Open `_build/autoapi/example/index.html` to see all four return entries and the
wrapped description. On Windows, activate with `.venv\Scripts\activate`.

Verified with Python 3.12.4, pydoclint 0.12.0, Sphinx-AutoAPI 3.9.0 and Sphinx
9.1.1. `check.py` checks the actual linter, matching tuple types and values,
three DOC203 negative controls, generated RST and the warning-as-error HTML
build. A temporary import sentinel confirms AutoAPI parses the module without
executing it. This is programmatic validation of the included example; the
requester's complete project was not available.

References: [pydoclint's stable tuple decomposition](https://github.com/jsh9/pydoclint/blob/0.12.0/pydoclint/utils/return_anno.py),
[NumPy Returns format](https://numpydoc.readthedocs.io/en/stable/format.html#returns),
[AutoAPI setup](https://sphinx-autoapi.readthedocs.io/en/latest/tutorials.html),
[NumPy-style docstrings in Sphinx](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html).

## Optional coffee

This example is free. If it helped, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
