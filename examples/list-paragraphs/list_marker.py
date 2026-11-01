"""Classify supported top-level paragraph numbering without changing a DOCX."""

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from zipfile import BadZipFile

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.ns import qn
from lxml.etree import XMLSyntaxError

# Other numbering formats deliberately remain unknown in this small example.
ORDERED_FORMATS = frozenset({
    "decimal", "decimalZero", "upperRoman", "lowerRoman", "upperLetter",
    "lowerLetter", "ordinal", "cardinalText", "ordinalText",
})


@dataclass(frozen=True)
class ListMarker:
    kind: str
    num_id: int | None = None
    level: int | None = None
    num_format: str | None = None
    reason: str = ""


class UnsupportedNumbering(ValueError):
    """The metadata does not identify one supported numbering format."""


def _children(parent, name):
    return [] if parent is None else parent.findall(qn(f"w:{name}"))


def _child(parent, name):
    matches = _children(parent, name)
    if len(matches) > 1:
        raise UnsupportedNumbering(f"Duplicate {name} elements")
    return matches[0] if matches else None


def _value(parent, name):
    child = _child(parent, name)
    if child is None:
        return None
    value = child.get(qn("w:val"))
    if value is None:
        raise UnsupportedNumbering(f"Missing {name} value")
    return value


def _integer(value, label, maximum=None):
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise UnsupportedNumbering(f"Invalid {label}") from None
    if result < 0 or (maximum is not None and result > maximum):
        raise UnsupportedNumbering(f"Invalid {label}")
    return result


def _style_chain(paragraph):
    # Use IDs, not translated display names such as "List Bullet".
    style = paragraph.style
    requested = _value(_child(paragraph._p, "pPr"), "pStyle")
    if requested is not None and (style is None or style.style_id != requested):
        raise UnsupportedNumbering("Paragraph style reference is missing")
    result, seen = [], set()
    while style is not None:
        if style.style_id in seen:
            raise UnsupportedNumbering("Cyclic paragraph style inheritance")
        seen.add(style.style_id)
        result.append(style)
        based_on = _value(style.element, "basedOn")
        parent = style.base_style
        if based_on is not None and (parent is None or parent.style_id != based_on):
            raise UnsupportedNumbering("Base style reference is missing")
        style = parent
    return result


def _matching(parent, name, attribute, identifier):
    matches = [
        node for node in _children(parent, name)
        if node.get(qn(f"w:{attribute}")) == str(identifier)
    ]
    if len(matches) != 1:
        raise UnsupportedNumbering(f"Missing or duplicate {name} {identifier}")
    return matches[0]


def _selected_level(number, abstract, index):
    overrides = [
        node for node in _children(number, "lvlOverride")
        if node.get(qn("w:ilvl")) == str(index)
    ]
    if len(overrides) > 1:
        raise UnsupportedNumbering("Duplicate level overrides")
    if overrides:
        replacement = _child(overrides[0], "lvl")
        if replacement is not None:
            if replacement.get(qn("w:ilvl")) != str(index):
                raise UnsupportedNumbering("Override level does not match its index")
            return replacement
        # startOverride changes the counter, not the format.
    return _matching(abstract, "lvl", "ilvl", index)


def list_marker(paragraph):
    """Return bullet/ordered/none/unknown for a supported Paragraph.

    This reads python-docx 1.2.0's XML objects. It does not calculate displayed
    numbers or glyphs. Inspect ``reason`` when the result is ``unknown``.
    """
    num_id = index = num_format = None
    try:
        direct = _child(_child(paragraph._p, "pPr"), "numPr")
        raw_num = _value(direct, "numId")
        raw_level = _value(direct, "ilvl")
        if raw_num is not None:
            num_id = _integer(raw_num, "numId")
            if num_id == 0:
                return ListMarker("none", 0, reason="numId 0 suppresses numbering")

        styles = _style_chain(paragraph) if raw_num is None or raw_level is None else []
        style_properties = [
            _child(_child(style.element, "pPr"), "numPr") for style in styles
        ]
        if raw_num is None:
            for properties in style_properties:
                inherited = _value(properties, "numId")
                if inherited is not None:
                    num_id = _integer(inherited, "style numId")
                    break
        if num_id is None:
            if raw_level is not None or any(p is not None for p in style_properties) or direct is not None:
                raise UnsupportedNumbering("Numbering properties have no resolved numId")
            return ListMarker("none", reason="No paragraph or inherited numbering")
        if num_id == 0:
            return ListMarker("none", 0, reason="Inherited numId 0 suppresses numbering")
        if raw_level is not None:
            index = _integer(raw_level, "ilvl", 8)

        # Avoid DocumentPart.numbering_part: its lazy getter can try to create a
        # missing part. A classifier only reads existing relationships.
        try:
            numbering = paragraph.part.part_related_by(RT.NUMBERING).element
        except KeyError:
            raise UnsupportedNumbering("Numbering part is missing") from None
        number = _matching(numbering, "num", "numId", num_id)
        abstract_id = _integer(_value(number, "abstractNumId"), "abstractNumId")
        abstract = _matching(numbering, "abstractNum", "abstractNumId", abstract_id)
        if _child(abstract, "numStyleLink") is not None or _child(abstract, "styleLink") is not None:
            raise UnsupportedNumbering("Linked numbering styles are outside this example")

        if index is None:
            if any(_child(properties, "ilvl") is not None for properties in style_properties):
                raise UnsupportedNumbering("Style-level ilvl compatibility is outside this example")
            style_ids = {style.style_id for style in styles}
            candidates = set()
            for source in [*_children(abstract, "lvl"), *_children(number, "lvlOverride")]:
                candidate = _integer(source.get(qn("w:ilvl")), "level index", 8)
                selected = _selected_level(number, abstract, candidate)
                if _value(selected, "pStyle") in style_ids:
                    candidates.add(candidate)
            if len(candidates) != 1:
                raise UnsupportedNumbering("No unique level associated with the paragraph style")
            index = candidates.pop()

        selected = _selected_level(number, abstract, index)
        if _child(selected, "lvlPicBulletId") is not None:
            raise UnsupportedNumbering("Picture bullets are outside this example")
        format_element = _child(selected, "numFmt")
        num_format = _value(selected, "numFmt") if format_element is not None else "decimal"
        if format_element is not None and format_element.get(qn("w:format")) is not None:
            raise UnsupportedNumbering("Custom number format strings are outside this example")
        if num_format == "bullet":
            kind = "bullet"
        elif num_format == "none":
            kind = "none"
        elif num_format in ORDERED_FORMATS:
            kind = "ordered"
        else:
            raise UnsupportedNumbering("Number format is outside the supported subset")
        return ListMarker(kind, num_id, index, num_format, "Resolved numbering format metadata")
    except UnsupportedNumbering as error:
        return ListMarker("unknown", num_id, index, num_format, str(error))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--bullets-only", action="store_true", help="Return only confirmed bullet formats")
    parser.add_argument("--no-text", action="store_true", help="Omit paragraph text")
    options = parser.parse_args(argv)
    try:
        document = Document(options.document)
    except (OSError, PackageNotFoundError, BadZipFile, XMLSyntaxError, KeyError, ValueError) as error:
        print(f"Cannot read DOCX: {error}", file=sys.stderr)
        return 2
    rows = []
    for index, paragraph in enumerate(document.paragraphs):
        marker = list_marker(paragraph)
        if options.bullets_only and marker.kind != "bullet":
            continue
        row = {"index": index, **asdict(marker)}
        if not options.no_text:
            row["text"] = paragraph.text
        rows.append(row)
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
