# Fuzzy picker

A small Textual picker: type part of a label, move through the matches, and return the selected value to your Python code. It uses the supported `Matcher`, `Input`, `OptionList`, and `App.exit` APIs.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python picker.py
```

On Windows, activate with `.venv\Scripts\activate` instead. Run the example in an interactive terminal. You can also supply labels as arguments:

```sh
python picker.py README.md docs/guide.md tests/check.py
```

Type `rd` to match `README.md` without needing adjacent letters. Up/Down moves through the results while the search input keeps focus. Enter chooses the highlighted result; clicking also chooses it. Escape cancels. If nothing matches, Enter leaves the picker open so you can edit the query.

For an existing application, give each item a label and its original value:

```python
from picker import Choice, Picker

selected = Picker([
    Choice("README.md", "docs/README.md"),
    Choice("README.md", "package/README.md"),
    Choice("Release notes", "CHANGELOG.md"),
]).run()

if selected is not None:
    print(f"Selected: {selected}")
```

Matching is case-insensitive and ranked by Textual's fuzzy score. Ties retain source order. Different values appear beside their labels, so two `README.md` entries remain distinguishable. Each option keeps its original record index as its ID; selecting a filtered row returns that record's value. Labels and values render as literal text, including square brackets.

This example covers a single choice from a small in-memory list. Filtering runs on each input change. It does not read files or execute the selected value.

Run the checks:

```sh
python check.py
```

The six checks use actual Textual Pilot interactions for typing, ranked filtering, duplicate labels, navigation, no-match recovery, cancellation, empty input, Unicode and mouse selection. Checked with Textual 8.2.8, Rich 15.0.0 and Python 3.12.4. The terminal driver was also exercised in a scripted PTY session: `rd`, Down, Enter returned `package/README.md`.

Official references: [fuzzy matching](https://textual.textualize.io/api/fuzzy/), [OptionList](https://textual.textualize.io/widgets/option_list/), [Input](https://textual.textualize.io/widgets/input/), [returning a value](https://textual.textualize.io/guide/app/#returning-a-value).

## Optional coffee

This example is free. If it saved you time, buying me a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
