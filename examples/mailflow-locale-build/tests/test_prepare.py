import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LocalePreparation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'frontend/src/locales').mkdir(parents=True)
        (self.root / 'frontend/src/components').mkdir()
        self.english = {'login': {'title': 'Welcome', 'greeting': 'Hello {{name}}'}, 'nested': {'count_one': '{{count}} item', 'count_other': '{{count}} items'}}
        self.locale = {'login': {'title': 'Danish test: Welcome', 'greeting': 'Danish test: Hello {{name}}'}, 'nested': {'count_one': 'Danish test: {{count}} item', 'count_other': 'Danish test: {{count}} items'}}
        self.en = self.root / 'frontend/src/locales/en.json'
        self.en.write_text(json.dumps(self.english), encoding='utf8')
        (self.root / 'frontend/src/i18n.js').write_text("const LOCALES = {\n  de: () => import('./locales/de.json'),\n};\n", encoding='utf8')
        (self.root / 'frontend/src/components/AdminPanel.jsx').write_text("const LANGUAGES = [\n  { code: 'en', nativeName: 'English' },\n];\n", encoding='utf8')
        self.input = self.root / 'translated.json'
        self.input.write_text(json.dumps(self.locale, indent=2) + '\n', encoding='utf8')

    def tearDown(self):
        self.temp.cleanup()

    def run_prepare(self):
        return subprocess.run([sys.executable, str(ROOT / 'prepare.py'), str(self.root), str(self.input)], text=True, capture_output=True)

    def source_snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in (self.root / 'frontend').rglob('*') if p.is_file()}

    def test_registers_supplied_file_without_changing_english_and_is_repeatable(self):
        before_en = self.en.read_bytes()
        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / 'frontend/src/locales/da.json').read_bytes(), self.input.read_bytes())
        self.assertEqual(self.en.read_bytes(), before_en)
        first = self.source_snapshot()
        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.source_snapshot(), first)

    def test_missing_key_fails_before_writing(self):
        del self.locale['login']['title']
        self.input.write_text(json.dumps(self.locale))
        before = self.source_snapshot()
        result = self.run_prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('keys', result.stderr)
        self.assertEqual(self.source_snapshot(), before)

    def test_lost_placeholder_fails_before_writing(self):
        self.locale['login']['greeting'] = 'Danish test: Hello'
        self.input.write_text(json.dumps(self.locale))
        before = self.source_snapshot()
        result = self.run_prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('placeholder', result.stderr)
        self.assertEqual(self.source_snapshot(), before)

    def test_duplicate_json_key_fails_before_writing(self):
        self.input.write_text('{"login":{},"login":{}}')
        before = self.source_snapshot()
        result = self.run_prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('duplicate', result.stderr)
        self.assertEqual(self.source_snapshot(), before)

    def test_existing_different_locale_is_preserved(self):
        (self.root / 'frontend/src/locales/da.json').write_text('{"keep":"existing translation"}')
        before = self.source_snapshot()
        result = self.run_prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('existing', result.stderr)
        self.assertEqual(self.source_snapshot(), before)

    def test_unrecognized_registration_layout_is_preserved(self):
        (self.root / 'frontend/src/i18n.js').write_text('export const locales = {};\n')
        before = self.source_snapshot()
        result = self.run_prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('registration', result.stderr)
        self.assertEqual(self.source_snapshot(), before)

    def test_existing_exact_line_does_not_hide_conflicting_registration(self):
        loader = self.root / 'frontend/src/i18n.js'
        loader.write_text("const LOCALES = {\n  da: () => import('./locales/da.json'),\n  da: () => import('./other.json'),\n};\n")
        before = self.source_snapshot()
        result = self.run_prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('registration', result.stderr)
        self.assertEqual(self.source_snapshot(), before)

    def test_existing_line_without_expected_anchor_is_preserved(self):
        loader = self.root / 'frontend/src/i18n.js'
        loader.write_text("export const other = {\n  da: () => import('./locales/da.json'),\n};\n")
        before = self.source_snapshot()
        result = self.run_prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('registration', result.stderr)
        self.assertEqual(self.source_snapshot(), before)


if __name__ == '__main__':
    unittest.main()
