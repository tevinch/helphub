"""Native DOCX and command-line checks. Run with python check.py."""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn

from fixtures import add_abstract, add_num, element, level, make_sample, set_numbering
from list_marker import list_marker

HERE = Path(__file__).resolve().parent


class ListParagraphChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="list paragraphs ")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.path = self.directory / "sample document.docx"
        make_sample(self.path)

    def round_trip(self, document):
        path = self.directory / "extra.docx"
        document.save(path)
        return Document(path)

    def cli(self, *arguments, cwd=HERE):
        return subprocess.run(
            [sys.executable, "list_marker.py", *map(str, arguments)],
            cwd=cwd, capture_output=True, text=True, check=False,
        )

    def test_saved_document_direct_and_inherited_numbering(self):
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        document = Document(self.path)
        expected = [
            ("none", None, None, None),
            ("bullet", 100, 0, "bullet"),
            ("ordered", 101, 0, "decimal"),
            ("bullet", 100, 1, "bullet"),
            ("bullet", 1, 0, "bullet"),
            ("ordered", 5, 0, "decimal"),
            ("bullet", 1, 0, "bullet"),
            ("none", 0, None, None),
            ("bullet", 102, 0, "bullet"),
            ("ordered", 103, 0, "decimal"),
            ("unknown", 104, 0, "custom"),
            ("unknown", 999, 0, None),
            ("none", 105, 0, "none"),
            ("unknown", 100, None, None),
            ("ordered", 106, 0, "decimal"),
        ]
        actual = [list_marker(paragraph) for paragraph in document.paragraphs]
        self.assertEqual(
            [(item.kind, item.num_id, item.level, item.num_format) for item in actual],
            expected,
        )
        self.assertEqual(document.paragraphs[1].style.name, "Body Text")
        self.assertTrue(all(item.reason for item in actual))
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)

    def test_direct_level_can_override_style_and_inherit_its_num_id(self):
        document = Document()
        style = document.styles.add_style("Two levels", WD_STYLE_TYPE.PARAGRAPH)
        add_abstract(document, 100, [level(0, "bullet", style.style_id), level(1, "decimal")])
        add_num(document, 100, 100)
        style.element.get_or_add_pPr().append(element("numPr"))
        style.element.pPr.numPr.append(element("numId", val=100))
        paragraph = document.add_paragraph("Inherited number, explicit level", style)
        set_numbering(paragraph, index=1)
        result = list_marker(self.round_trip(document).paragraphs[0])
        self.assertEqual((result.kind, result.num_id, result.level), ("ordered", 100, 1))

    def test_missing_part_and_reference_do_not_create_or_mutate_xml(self):
        document = Document()
        set_numbering(document.add_paragraph("Unresolved numbering"), 100, 0)
        for key, relation in list(document.part.rels.items()):
            if relation.reltype == RT.NUMBERING:
                del document.part.rels[key]
        document = self.round_trip(document)
        before = document.part.element.xml
        self.assertEqual(list_marker(document.paragraphs[0]).kind, "unknown")
        self.assertFalse(any(r.reltype == RT.NUMBERING for r in document.part.rels.values()))
        self.assertEqual(document.part.element.xml, before)
        other = Document()
        add_num(other, 100, 888)
        set_numbering(other.add_paragraph("Missing abstract definition"), 100, 0)
        self.assertEqual(list_marker(self.round_trip(other).paragraphs[0]).kind, "unknown")

    def test_unsupported_and_ambiguous_definitions_are_unknown(self):
        document = Document()
        picture_level = level(0, "bullet")
        picture_level.append(element("lvlPicBulletId", val=1))
        add_abstract(document, 100, [picture_level])
        linked = add_abstract(document, 101, [level(0, "bullet")])
        linked.append(element("numStyleLink", val="LinkedNumbering"))
        add_abstract(document, 102, [level(0, "bullet"), level(0, "decimal")])
        for identifier in (100, 101, 102):
            add_num(document, identifier, identifier)
            set_numbering(document.add_paragraph("Unsupported metadata"), identifier, 0)
        set_numbering(document.add_paragraph("Invalid level"), 100, 9)
        style = document.styles.add_style("Ambiguous levels", WD_STYLE_TYPE.PARAGRAPH)
        add_abstract(document, 103, [level(0, "bullet", style.style_id), level(1, "decimal", style.style_id)])
        add_num(document, 103, 103)
        style.element.get_or_add_pPr().append(element("numPr"))
        style.element.pPr.numPr.append(element("numId", val=103))
        document.add_paragraph("Ambiguous style mapping", style)
        explicit = document.styles.add_style("Style with level", WD_STYLE_TYPE.PARAGRAPH)
        explicit.base_style = document.styles["List Bullet"]
        explicit.element.get_or_add_pPr().append(element("numPr"))
        explicit.element.pPr.numPr.append(element("ilvl", val=0))
        document.add_paragraph("Style-level compatibility varies", explicit)
        document = self.round_trip(document)
        self.assertEqual([list_marker(p).kind for p in document.paragraphs], ["unknown"] * 6)

    def test_full_override_is_replacement_and_suppression_wins(self):
        document = Document()
        add_abstract(document, 100, [level(0, "bullet")])
        override = element("lvlOverride", ilvl=0)
        override.append(level(0, None))
        add_num(document, 100, 100, override)
        set_numbering(document.add_paragraph("Replacement defaults to decimal"), 100, 0)
        paragraph = document.add_paragraph("Suppressed despite invalid level", "List Bullet")
        set_numbering(paragraph, 0, 9)
        document = self.round_trip(document)
        first, second = map(list_marker, document.paragraphs)
        self.assertEqual((first.kind, first.num_format), ("ordered", "decimal"))
        self.assertEqual(second.kind, "none")

    def test_cli_outputs_text_filter_and_read_only_json(self):
        before = self.path.read_bytes()
        result = self.cli(self.path)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)
        self.assertEqual(len(rows), 15)
        self.assertEqual(rows[1]["text"], "Direct bullet in Body Text.")
        self.assertEqual(rows[1]["kind"], "bullet")
        self.assertEqual(rows[0]["kind"], "none")
        filtered = self.cli(self.path, "--bullets-only", "--no-text")
        self.assertEqual(filtered.returncode, 0, filtered.stderr)
        bullets = json.loads(filtered.stdout)
        self.assertEqual([row["index"] for row in bullets], [1, 3, 4, 6, 8])
        self.assertTrue(all("text" not in row and row["kind"] == "bullet" for row in bullets))
        self.assertEqual(self.path.read_bytes(), before)

    def test_cli_missing_corrupt_and_fresh_source_copy(self):
        corrupt = self.directory / "broken.docx"
        corrupt.write_text("This is not a ZIP package.", encoding="utf-8")
        for path in [self.directory / "missing.docx", corrupt]:
            result = self.cli(path)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("Cannot read DOCX", result.stderr)
        fresh = self.directory / "fresh source"
        fresh.mkdir()
        for name in ("list_marker.py", "fixtures.py"):
            shutil.copyfile(HERE / name, fresh / name)
        sample = fresh / "fresh sample.docx"
        generated = subprocess.run([sys.executable, "fixtures.py", str(sample)], cwd=fresh, capture_output=True, text=True)
        self.assertEqual(generated.returncode, 0, generated.stderr)
        result = self.cli(sample, "--bullets-only", cwd=fresh)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row["index"] for row in json.loads(result.stdout)], [1, 3, 4, 6, 8])


if __name__ == "__main__":
    unittest.main(verbosity=2)
