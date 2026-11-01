"""Create small, original DOCX inputs for the example and its tests."""

import argparse
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def element(name, **attributes):
    node = OxmlElement(f"w:{name}")
    for key, value in attributes.items():
        node.set(qn(f"w:{key}"), str(value))
    return node


def level(index, number_format, style=None):
    node = element("lvl", ilvl=index)
    node.append(element("start", val=1))
    if number_format is not None:
        node.append(element("numFmt", val=number_format))
    if style:
        node.append(element("pStyle", val=style))
    node.append(element("lvlText", val="•" if number_format == "bullet" else "%1."))
    return node


def add_abstract(document, identifier, levels):
    node = element("abstractNum", abstractNumId=identifier)
    for item in levels:
        node.append(item)
    document.part.numbering_part.element.append(node)
    return node


def add_num(document, identifier, abstract_id, override=None):
    node = element("num", numId=identifier)
    node.append(element("abstractNumId", val=abstract_id))
    if override is not None:
        node.append(override)
    document.part.numbering_part.element.append(node)
    return node


def set_numbering(paragraph, identifier=None, index=None):
    num_pr = paragraph._p.get_or_add_pPr().get_or_add_numPr()
    if index is not None:
        num_pr.append(element("ilvl", val=index))
    if identifier is not None:
        num_pr.append(element("numId", val=identifier))


def make_sample(path):
    document = Document()
    document.core_properties.author = "Tevinch"
    document.core_properties.last_modified_by = "Tevinch"
    document.core_properties.title = "List paragraph example"
    add_abstract(document, 100, [level(0, "bullet"), level(1, "bullet")])
    add_abstract(document, 101, [level(0, "decimal")])
    add_abstract(document, 102, [level(0, "custom")])
    add_abstract(document, 103, [level(0, "none")])
    add_abstract(document, 104, [level(0, None)])
    add_num(document, 100, 100)
    add_num(document, 101, 101)
    override = element("lvlOverride", ilvl=0)
    override.append(level(0, "bullet"))
    add_num(document, 102, 101, override)
    start_only = element("lvlOverride", ilvl=0)
    start_only.append(element("startOverride", val=7))
    add_num(document, 103, 101, start_only)
    add_num(document, 104, 102)
    add_num(document, 105, 103)
    add_num(document, 106, 104)

    document.add_paragraph("• A typed symbol does not establish list metadata.")
    set_numbering(document.add_paragraph("Direct bullet in Body Text.", "Body Text"), 100, 0)
    set_numbering(document.add_paragraph("Direct numbered item."), 101, 0)
    set_numbering(document.add_paragraph("Second-level bullet."), 100, 1)
    document.add_paragraph("Built-in bullet style.", "List Bullet")
    document.add_paragraph("Built-in number style.", "List Number")
    derived = document.styles.add_style("Checklist item", WD_STYLE_TYPE.PARAGRAPH)
    derived.base_style = document.styles["List Bullet"]
    document.add_paragraph("Derived bullet style.", derived)
    set_numbering(document.add_paragraph("Numbering explicitly removed.", "List Bullet"), 0)
    set_numbering(document.add_paragraph("Instance override changes decimal to bullet."), 102, 0)
    set_numbering(document.add_paragraph("A start override retains decimal format."), 103, 0)
    set_numbering(document.add_paragraph("Unresolved custom format."), 104, 0)
    set_numbering(document.add_paragraph("Missing numbering instance."), 999, 0)
    set_numbering(document.add_paragraph("Explicit format none."), 105, 0)
    set_numbering(document.add_paragraph("No unambiguous level."), 100)
    set_numbering(document.add_paragraph("Omitted format defaults to decimal."), 106, 0)
    document.save(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    make_sample(parser.parse_args().output)
