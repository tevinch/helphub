"""Filesystem acceptance tests for the small placement example."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('place_extras.py')

class PlacementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='extras tests ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'roms'
        for platform in ('gb', 'gba'):
            (self.root / platform / 'Shared Title').mkdir(parents=True)
        (self.base / 'notes.txt').write_text('owned sample\n')
        self.rows = [dict(source='notes.txt', platform='gb', game='Shared Title', kind='manual')]
        self.manifest = self.base / 'extras.json'

    def run_helper(self, apply=False):
        self.manifest.write_text(json.dumps(self.rows))
        return subprocess.run([sys.executable, str(SCRIPT), str(self.manifest), str(self.root)] + (['--apply'] if apply else []), text=True, capture_output=True)

    def target(self):
        return self.root / 'gb' / 'Shared Title' / 'manual' / 'notes.txt'

    def test_apply_places_actual_bytes_and_repeat_skips(self):
        r = self.run_helper(True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.target().read_bytes(), (self.base/'notes.txt').read_bytes())
        stamp = self.target().stat().st_mtime_ns
        r = self.run_helper(True)
        self.assertEqual(json.loads(r.stdout)[0]['action'], 'unchanged')
        self.assertEqual(self.target().stat().st_mtime_ns, stamp)

    def test_default_plan_does_not_create_directory(self):
        r = self.run_helper()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)[0]['action'], 'copy')
        self.assertFalse(self.target().parent.exists())

    def test_same_title_different_platform_is_explicit(self):
        self.rows[0]['platform'] = 'gba'
        self.assertEqual(self.run_helper(True).returncode, 0)
        self.assertFalse(self.target().exists())
        self.assertTrue((self.root/'gba'/'Shared Title'/'manual'/'notes.txt').is_file())

    def test_conflict_preflight_makes_no_earlier_copy(self):
        self.target().parent.mkdir()
        self.target().write_text('existing different\n')
        self.rows.insert(0, dict(source='notes.txt', platform='gba', game='Shared Title', kind='manual'))
        self.assertNotEqual(self.run_helper(True).returncode, 0)
        self.assertFalse((self.root/'gba'/'Shared Title'/'manual').exists())
        self.assertEqual(self.target().read_text(), 'existing different\n')

    def test_missing_game_is_not_invented(self):
        self.rows[0]['game'] = 'Missing'
        self.assertNotEqual(self.run_helper(True).returncode, 0)
        self.assertFalse((self.root/'gb'/'Missing').exists())

    def test_invalid_components_fail_without_writes(self):
        for key, value in [('kind','unknown'),('kind','../manual'),('platform','../gb'),('game','/tmp'),('game','a\\b'),('game','..')]:
            with self.subTest(key=key, value=value):
                old=self.rows[0][key];self.rows[0][key]=value
                self.assertNotEqual(self.run_helper(True).returncode, 0)
                self.rows[0][key]=old
        self.assertFalse(self.target().parent.exists())

    def test_source_escape_and_duplicate_fail(self):
        original = self.manifest
        mapping = self.base/'mapping'; mapping.mkdir()
        self.manifest = mapping/'extras.json'
        self.rows[0]['source'] = '../notes.txt'  # Exists and is readable outside the manifest directory.
        self.assertNotEqual(self.run_helper(True).returncode, 0)
        self.manifest = original
        self.rows[0]['source'] = 'notes.txt'
        self.rows.append(dict(self.rows[0]))
        self.assertNotEqual(self.run_helper(True).returncode, 0)
        self.assertFalse(self.target().parent.exists())

    def test_symlink_escape_is_refused(self):
        outside=self.base/'outside';outside.mkdir()
        (self.root/'gb'/'Shared Title'/'manual').symlink_to(outside, target_is_directory=True)
        self.assertNotEqual(self.run_helper(True).returncode, 0)
        self.assertFalse((outside/'notes.txt').exists())

    def test_multichunk_identical_then_last_byte_conflict(self):
        payload = b'owned sample text\n' * 20000
        (self.base/'notes.txt').write_bytes(payload)
        self.assertEqual(self.run_helper(True).returncode, 0)
        self.assertEqual(json.loads(self.run_helper(True).stdout)[0]['action'], 'unchanged')
        self.target().write_bytes(payload[:-1] + b'!')
        self.assertNotEqual(self.run_helper(True).returncode, 0)
        self.assertEqual(self.target().read_bytes(), payload[:-1] + b'!')

    def test_source_symlink_escape_is_refused(self):
        mapping = self.base/'mapping'; mapping.mkdir()
        (mapping/'linked.txt').symlink_to(self.base/'notes.txt')
        self.manifest = mapping/'extras.json'
        self.rows[0]['source'] = 'linked.txt'
        self.assertNotEqual(self.run_helper(True).returncode, 0)
        self.assertFalse(self.target().parent.exists())

    def test_unlisted_existing_file_is_preserved(self):
        self.target().parent.mkdir();other=self.target().parent/'my notes.txt';other.write_text('keep me\n')
        self.assertEqual(self.run_helper(True).returncode,0)
        self.assertEqual(other.read_text(),'keep me\n')

if __name__ == '__main__':
    unittest.main()
