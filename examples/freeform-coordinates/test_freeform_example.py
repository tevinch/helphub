"""Saved-file acceptance for the native python-pptx freeform example."""

from fractions import Fraction
from io import BytesIO
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches

from freeform_example import add_polygon, make_presentation

EMU_PER_INCH = 914400
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def saved_geometry(presentation):
    """Read the saved file independently; map path vertices into slide EMUs."""
    stream = BytesIO()
    presentation.save(stream)
    stream.seek(0)
    reopened = Presentation(stream)
    stream.seek(0)
    with ZipFile(stream) as package:
        xml = ET.fromstring(package.read("ppt/slides/slide1.xml"))

    shapes = []
    for shape in xml.findall(".//p:sp", NS):
        path = shape.find("p:spPr/a:custGeom/a:pathLst/a:path", NS)
        if path is None:
            continue
        transform = shape.find("p:spPr/a:xfrm", NS)
        offset = transform.find("a:off", NS)
        extent = transform.find("a:ext", NS)
        left, top = int(offset.get("x")), int(offset.get("y"))
        width, height = int(extent.get("cx")), int(extent.get("cy"))
        path_width, path_height = int(path.get("w")), int(path.get("h"))
        vertices = []
        operations = []
        for operation in path:
            operations.append(operation.tag.rsplit("}", 1)[-1])
            point = operation.find("a:pt", NS)
            if point is not None:
                vertices.append((
                    Fraction(left) + Fraction(int(point.get("x")) * width, path_width),
                    Fraction(top) + Fraction(int(point.get("y")) * height, path_height),
                ))
        shapes.append({
            "vertices": vertices, "operations": operations,
            "box": (left, top, width, height),
        })
    return reopened, shapes


class FreeformAcceptance(unittest.TestCase):
    def test_exact_requested_trapezoid_survives_save_and_reopen(self):
        reopened, shapes = saved_geometry(make_presentation())
        self.assertEqual(len(reopened.slides), 1)
        self.assertEqual(len(reopened.slides[0].shapes), 1)
        self.assertEqual(reopened.slides[0].shapes[0].shape_type, MSO_SHAPE_TYPE.FREEFORM)
        self.assertEqual(len(shapes), 1)
        self.assertEqual(shapes[0]["vertices"], [
            (1828800, 2286000), (4114800, 2286000),
            (3657600, 5029200), (2286000, 5029200),
        ])
        self.assertEqual(shapes[0]["box"], (1828800, 2286000, 2286000, 2743200))
        self.assertEqual(shapes[0]["operations"], ["moveTo", "lnTo", "lnTo", "lnTo", "close"])
        for x, y in shapes[0]["vertices"]:
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x, reopened.slide_width)
            self.assertLessEqual(y, reopened.slide_height)

    def test_fractional_triangle_uses_absolute_endpoints(self):
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        add_polygon(slide, [(0.125, 0.375), (2.375, 0.625), (1.125, 1.875)])
        _, shapes = saved_geometry(presentation)
        self.assertEqual(shapes[0]["vertices"], [
            (114300, 342900), (2171700, 571500), (1028700, 1714500),
        ])
        self.assertEqual(shapes[0]["operations"], ["moveTo", "lnTo", "lnTo", "close"])

    def test_repeated_polygons_keep_their_positions_and_existing_content(self):
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        text = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(4), Inches(0.5))
        text.text = "Keep this existing content"
        add_polygon(slide, [(1, 1), (2, 1), (1.5, 2)])
        add_polygon(slide, [(4.25, 3.125), (5.25, 3.125), (4.75, 4.125)])
        reopened, shapes = saved_geometry(presentation)
        self.assertEqual(len(reopened.slides[0].shapes), 3)
        self.assertEqual(reopened.slides[0].shapes[0].text, "Keep this existing content")
        self.assertEqual(shapes[0]["vertices"], [
            (914400, 914400), (1828800, 914400), (1371600, 1828800),
        ])
        self.assertEqual(shapes[1]["vertices"], [
            (3886200, 2857500), (4800600, 2857500), (4343400, 3771900),
        ])

    def test_command_writes_a_readable_presentation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "custom-name.pptx"
            process = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("freeform_example.py")), str(output)],
                check=True, capture_output=True, text=True,
            )
            self.assertIn(str(output), process.stdout)
            self.assertTrue(output.is_file())
            reopened = Presentation(output)
            _, shapes = saved_geometry(reopened)
            self.assertEqual(shapes[0]["vertices"][0], (1828800, 2286000))
            self.assertEqual(len(shapes[0]["vertices"]), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)

