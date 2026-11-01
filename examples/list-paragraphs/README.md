# Find bullet paragraphs in a DOCX

A paragraph can be a bullet item while its paragraph style is Body Text, Normal or another ordinary style. The list format is stored separately: `w:numPr` identifies a numbering instance and level, and the instance points to the definition containing `w:numFmt`.

This Python example reads that metadata and returns `bullet`, `ordered`, `none` or `unknown`. It does not save or rewrite the input file.

Use Python 3.10 or later and python-docx 1.2.0:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python fixtures.py sample.docx
python list_marker.py sample.docx --bullets-only
python check.py
```

The generated sample contains five confirmed bullet paragraphs, at zero-based indices `1, 3, 4, 6, 8`. It also includes ordinary text beginning with a typed bullet, numbered paragraphs, explicitly removed numbering and unresolved definitions. All sample text is original and generated locally.

For an existing file:

```sh
python list_marker.py "my document.docx" --bullets-only --no-text
```

Without `--bullets-only`, the JSON includes every top-level paragraph so you can inspect `unknown` results. Text is included by default; `--no-text` omits it. Missing or unreadable DOCX input produces an error on stderr and exit status 2. The input path is never written to.

Use the function in your own script:

```python
from docx import Document
from list_marker import list_marker

document = Document("my document.docx")
for index, paragraph in enumerate(document.paragraphs):
    marker = list_marker(paragraph)
    if marker.kind == "bullet":
        print(index, paragraph.text)
    elif marker.kind == "unknown":
        print(index, marker.reason)
```

For the direct Body Text bullet in the generated sample, the CLI returns:

```json
{
  "index": 1,
  "kind": "bullet",
  "num_id": 100,
  "level": 0,
  "num_format": "bullet",
  "reason": "Resolved numbering format metadata",
  "text": "Direct bullet in Body Text."
}
```

`num_id` identifies a numbering instance, not a bullet type. Different instances can share a definition; a single instance can contain levels with different formats.

The resolver supports direct paragraph numbering, `numId` inherited through paragraph styles, an unambiguous `w:pStyle` level association, and an explicit paragraph level combined with an inherited number. `numId="0"` removes numbering. A full instance `w:lvlOverride/w:lvl` replaces the base level; a `w:startOverride` alone only changes the counter and keeps its format. A selected level with no `w:numFmt` defaults to decimal.

`ordered` currently covers `decimal`, `decimalZero`, `upperRoman`, `lowerRoman`, `upperLetter`, `lowerLetter`, `ordinal`, `cardinalText` and `ordinalText`. Other formats, picture bullets, linked numbering styles, missing or ambiguous references, and style-level `ilvl` without an explicit paragraph level return `unknown`. When no explicit level or unique style association is available, the example also returns `unknown`. `none` means no paragraph or inherited numbering, explicit removal, or `numFmt="none"`; it does not inspect typed symbols in the text.

This is a bounded metadata classifier, not a Word numbering renderer. It does not calculate displayed numbers, bullet glyphs, indentation, visibility or layout. It scans `Document.paragraphs`, which does not traverse table cells, headers, footnotes, text boxes or paragraphs inside revision marks. Handling those containers or other numbering formats requires extending the example deliberately.

The resolver uses private XML objects (`paragraph._p`, style elements and the numbering part) because python-docx 1.2.0 does not expose this classification as a high-level property. The dependency is pinned, and the tests read real saved DOCX packages. Recheck the XML access when upgrading python-docx.

The seven native tests cover the generated input after saving and reloading, style inheritance, direct overrides, full-level and start-only instance overrides, suppression, unsupported definitions, a missing numbering part, unchanged input bytes, JSON output, errors, and a run from a fresh source copy in a path containing spaces. No Microsoft Word or LibreOffice installation is needed to run the example or tests.

References: [python-docx Document API](https://python-docx.readthedocs.io/en/latest/api/document.html), [paragraph style API](https://python-docx.readthedocs.io/en/latest/api/text.html#docx.text.paragraph.Paragraph.style), [numbering instances and suppression](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.numberingid?view=openxml-3.0.1), [level overrides](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.leveloverride?view=openxml-3.0.1), [number formats](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.numberingformat?view=openxml-3.0.1), and [paragraph-style level compatibility](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/6a8f14ff-df90-4154-9bc9-e0e88ae5e641).

## Optional coffee

This example is free. If it saved you time, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
