"""Create an editable trapezoid using python-pptx's native freeform API."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

TRAPEZOID = [(2.0, 2.5), (4.5, 2.5), (4.0, 5.5), (2.5, 5.5)]


def add_polygon(slide, points):
    """Add a closed polygon; points are absolute slide positions in inches."""
    vertices = [(Inches(x), Inches(y)) for x, y in points]
    builder = slide.shapes.build_freeform(*vertices[0])
    builder.add_line_segments(vertices[1:], close=True)
    return builder.convert_to_shape()


def make_presentation():
    presentation = Presentation()
    properties = presentation.core_properties
    properties.title = "Freeform coordinate example"
    properties.author = "Tevinch"
    properties.last_modified_by = "Tevinch"
    properties.comments = "Editable polygon created with the native freeform API."
    properties.created = properties.modified = datetime.now(timezone.utc)
    presentation.slide_width = Inches(13.333)
    presentation.slide_height = Inches(7.5)
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    shape = add_polygon(slide, TRAPEZOID)
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(34, 105, 175)
    shape.line.color.rgb = RGBColor(15, 45, 75)
    shape.line.width = Pt(1.5)
    return presentation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", default="trapezoid.pptx", type=Path)
    args = parser.parse_args()
    presentation = make_presentation()
    presentation.save(args.output)
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()

