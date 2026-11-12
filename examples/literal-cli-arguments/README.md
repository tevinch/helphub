# Keep version strings intact in Python Fire

With Python Fire 0.7.1, configure the argument parser explicitly when a parameter must keep its text. A `str` annotation alone does not select string parsing.

For the original `arg` parameter, add `decorators.SetParseFns(arg=str)` as a decorator:

```python
import fire
from fire import decorators

@decorators.SetParseFns(arg=str)
def main(arg: str):
    print(f"Hello! {type(arg)} {arg}")

if __name__ == "__main__":
    fire.Fire(main)
```

The [public parse decorator](https://github.com/google/python-fire/blob/v0.7.1/fire/decorators.py) supplies `str` with the original argument text. This applies when `arg` is passed positionally or by name.

## Run it

Download the files in this directory. With Python 3.10 or newer, create an environment and install the exact checked dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tp.py 1.10
.venv/bin/python tp.py --arg=1.10
.venv/bin/python tp.py --arg 1.10
```

Each invocation prints:

```text
Hello! <class 'str'> 1.10
```

On Windows, use `.venv\Scripts\python.exe` in place of `.venv/bin/python`.

The same function preserves `1.1`, `0010`, `True`, `None` and `1e2` as strings. It also preserves spaces and an empty string when those are supplied as one shell argument.

## Keep other parameters numeric

Use the parameter's Python name in the decorator. In [selective.py](selective.py), only `arg` has a string parser:

```python
@decorators.SetParseFns(arg=str)
def main(arg: str, count: int):
    ...
```

Run:

```sh
.venv/bin/python selective.py 1.10 2
```

It prints:

```json
{"arg": "1.10", "arg_type": "str", "count": 2, "count_type": "int"}
```

The unchanged default parser still reads `count` as an integer. `decorators.SetParseFn(str)`, used as a decorator without argument names, instead makes `str` the default parser for all supplied arguments to that function. Use the narrower configuration when only one parameter needs it.

These decorators configure Fire's CLI parsing; they do not make Python annotations enforce types on ordinary function calls.

## Why ordinary quotes did not help

The [Fire guide](https://github.com/google/python-fire/blob/v0.7.1/docs/guide.md#argument-parsing) explains that values determine the inferred types. A shell removes ordinary enclosing quotes before Fire receives the argument, so `python tp.py '1.10'` supplies the same text as `python tp.py 1.10`.

The explicit parser above works with either form. For an unchanged command without the decorator, the guide's quote-your-quotes alternative is available in a POSIX shell:

```sh
python tp.py '"1.10"'
```

Here the inner double quotes reach Fire, so its literal parser reads a Python string. This syntax was checked in zsh; shell quoting rules differ elsewhere.

Calling `str(arg)` after Fire has already converted `1.10` to `1.1` cannot restore the lost zero.

## Verification

Checked on macOS with Python 3.12.4, Fire 0.7.1 and termcolor 3.3.0:

```sh
.venv/bin/python -m unittest discover -v
```

The three tests run 15 actual CLI processes. They check the exact original output, all three argument forms, literal-like strings, spaces, an empty string, and selective parsing beside a numeric parameter. Removing the explicit parser reproduces the original float output; making every parameter a string fails the numeric-parameter check.

These are scripted checks of the supplied examples. Windows and the original application have not been tested.

## Optional coffee

If this saved you some time, a coffee is welcome, but entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`

