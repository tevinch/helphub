"""Run with JAVA and SPARQL_ANYTHING_JAR pointing to the local runtime."""
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
JAVA = os.environ.get("JAVA", "java")
JAR = Path(os.environ["SPARQL_ANYTHING_JAR"]).resolve()


class ConversionTests(unittest.TestCase):
    def run_conversion(self, source, output, folder=HERE):
        return subprocess.run(
            [sys.executable, str(folder / "convert.py"), "--java", JAVA,
             "--jar", str(JAR), "--input", str(source), "--output", str(output)],
            text=True, capture_output=True, timeout=90,
        )

    def read_graph(self, output):
        query = 'SELECT ?s ?label WHERE { ?s <urn:example:label> ?label } ORDER BY ?s'
        result = subprocess.run(
            [JAVA, "-jar", str(JAR), "-l", str(output), "-q", query, "-f", "JSON"],
            text=True, capture_output=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return [(b["s"]["value"], b["label"]["value"], b["label"].get("xml:lang", "").lower())
                for b in json.loads(result.stdout)["results"]["bindings"]]

    def test_corrected_input_completes_the_actual_graph(self):
        # Losing either subject or a multiline/Unicode label must fail this test.
        with tempfile.TemporaryDirectory() as temp:
            source = HERE / "fixtures/corrected.csv"
            original = source.read_bytes()
            output = Path(temp) / "result.ttl"
            result = self.run_conversion(source, output)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout), {"status": "written", "records_checked": 4})
            self.assertEqual(self.read_graph(output), [
                ("https://example.org/empty", "Missing language", "en"),
                ("https://example.org/ok", "Café, ready", "en"),
                ("https://example.org/space", "Skipped", "en"),
                ("https://example.org/two", "Line one\nLine two", "en-us"),
            ])
            self.assertEqual(source.read_bytes(), original)

    def test_english_is_bound_and_is_not_a_language_validation_failure(self):
        # BOUND must not be presented as registered-language validation.
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.csv"
            source.write_text("subject,text,lang\nhttps://example.org/ok,foo,English\n")
            output = Path(temp) / "result.ttl"
            result = self.run_conversion(source, output)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.read_graph(output), [("https://example.org/ok", "foo", "english")])

    def test_missing_preflight_records_cannot_be_treated_as_success(self):
        # If the essential SELECT did not produce every row, do not construct.
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "example"
            shutil.copytree(HERE, copy, ignore=shutil.ignore_patterns("__pycache__"))
            (copy / "preflight.rq").write_text("SELECT ?record WHERE { FILTER(false) }")
            output = Path(temp) / "result.ttl"
            result = self.run_conversion(HERE / "fixtures/corrected.csv", output, copy)
            self.assertEqual(result.returncode, 1)
            self.assertIn("every CSV record", json.loads(result.stdout)["message"])
            self.assertFalse(output.exists())

    def test_existing_output_and_source_alias_are_preserved(self):
        # Replacing a user's existing data would violate the no-clobber contract.
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.csv"
            source.write_bytes((HERE / "fixtures/corrected.csv").read_bytes())
            original = source.read_bytes()
            output = Path(temp) / "result.ttl"
            output.write_bytes(b"existing output")
            for destination in (source, output):
                result = self.run_conversion(source, destination)
                self.assertEqual(result.returncode, 1)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(output.read_bytes(), b"existing output")

    def test_dangling_output_symlink_is_not_followed(self):
        # Resolving this symlink must not create a different destination file.
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "target.ttl"
            output = Path(temp) / "link.ttl"
            output.symlink_to(target)
            result = self.run_conversion(HERE / "fixtures/corrected.csv", output)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertTrue(output.is_symlink())
            self.assertFalse(target.exists())

    def test_engine_failure_does_not_leave_an_output(self):
        # A successful preflight cannot turn a later failed CONSTRUCT into success.
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "example"
            shutil.copytree(HERE, copy, ignore=shutil.ignore_patterns("__pycache__"))
            (copy / "construct.rq").write_text("This is not SPARQL")
            output = Path(temp) / "result.ttl"
            result = self.run_conversion(HERE / "fixtures/corrected.csv", output, copy)
            self.assertEqual(result.returncode, 1)
            self.assertIn("SPARQL Anything failed", json.loads(result.stdout)["message"])
            self.assertFalse(output.exists())

    def test_bom_and_duplicate_records_keep_their_values(self):
        # Native graph deduplication is not an omitted input record.
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.csv"
            source.write_text("subject,text,lang\nhttps://example.org/ok,foo,en\nhttps://example.org/ok,foo,en\n", encoding="utf-8-sig")
            original = source.read_bytes()
            output = Path(temp) / "result.ttl"
            result = self.run_conversion(source, output)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["records_checked"], 2)
            self.assertEqual(self.read_graph(output), [("https://example.org/ok", "foo", "en")])
            self.assertEqual(source.read_bytes(), original)

    def test_malformed_schema_or_record_does_not_leave_an_output(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.csv"
            for text in ("subject,text,text\nx,a,b\n", "subject,text,lang\nx,a\n", "subject,text,lang\nx,a,en,extra\n", "subject,text,lang\n"):
                with self.subTest(text=text):
                    source.write_text(text)
                    output = Path(temp) / "result.ttl"
                    result = self.run_conversion(source, output)
                    self.assertEqual(result.returncode, 1)
                    self.assertFalse(output.exists())

    def test_invalid_expressions_name_records_and_do_not_create_a_graph(self):
        # Omitting native preflight would return success and lose records 2 and 3.
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.csv"
            source.write_bytes((HERE / "fixtures/invalid.csv").read_bytes())
            original = source.read_bytes()
            output = Path(temp) / "result.ttl"
            result = self.run_conversion(source, output)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('"issues"', result.stdout,
                          "The conversion must report actual record diagnostics")
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "rejected")
            self.assertEqual(report["records_checked"], 4)
            self.assertEqual(report["issues"], [
                {"record": 2, "function": "IRI", "arguments": ["some space"]},
                {"record": 3, "function": "STRLANG", "arguments": ["Missing language", ""]},
            ])
            self.assertFalse(output.exists())
            self.assertEqual(source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
