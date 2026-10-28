"""Check a real prepared snapshot, offline inference, and refusal before loading."""

import hashlib
import json
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

import snapshot


class SnapshotChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = Path(SNAPSHOT_DIRECTORY)
        cls.lock = json.loads(Path(__file__).with_name("snapshot.json").read_text())

    def test_complete_offline_inference_twice_preserves_every_file(self):
        import stanza
        before = {str(p.relative_to(self.directory)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.directory.rglob("*") if p.is_file()}
        lock_before = Path(__file__).with_name("snapshot.json").read_bytes()
        with patch.object(stanza, "Pipeline", wraps=stanza.Pipeline) as constructed, \
             patch.object(socket.socket, "connect", side_effect=RuntimeError("connect denied")), \
             patch.object(socket.socket, "connect_ex", side_effect=RuntimeError("connect_ex denied")):
            with socket.socket() as probe:
                with self.assertRaisesRegex(RuntimeError, "connect denied"):
                    probe.connect(("127.0.0.1", 9))
                with self.assertRaisesRegex(RuntimeError, "connect_ex denied"):
                    probe.connect_ex(("127.0.0.1", 9))
            first = snapshot.run(self.directory, "A small test. Another sentence!")
            second = snapshot.run(self.directory, "A small test. Another sentence!")
            third = snapshot.run(self.directory, "Different input?")
        self.assertEqual(constructed.call_count, 3)
        for call in constructed.call_args_list:
            self.assertIsNone(call.kwargs["download_method"])
            self.assertIsNone(call.kwargs["package"])
            self.assertEqual(call.kwargs["processors"], {"tokenize": "ewt_nocharlm", "mwt": "ewt"})
            self.assertFalse(call.kwargs["use_gpu"])
        self.assertEqual(first, [["A", "small", "test", "."], ["Another", "sentence", "!"]])
        self.assertEqual(second, first)
        self.assertEqual(third, [["Different", "input", "?"]])
        after = {str(p.relative_to(self.directory)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.directory.rglob("*") if p.is_file()}
        self.assertEqual(after, before)
        self.assertEqual(Path(__file__).with_name("snapshot.json").read_bytes(), lock_before)

    def test_every_model_matches_the_independent_resources_md5(self):
        resources = json.loads((self.directory / "resources.json").read_bytes())
        for processor, name in self.lock["processors"].items():
            data = (self.directory / "en" / processor / (name + ".pt")).read_bytes()
            self.assertEqual(hashlib.md5(data).hexdigest(), resources["en"][processor][name]["md5"])

    def test_missing_and_tampered_files_are_rejected(self):
        for name in self.lock["files"]:
            for missing in (False, True):
                with self.subTest(name=name, missing=missing), tempfile.TemporaryDirectory() as tmp:
                    folder = Path(tmp) / "copy"
                    shutil.copytree(self.directory, folder)
                    target = folder / name
                    if missing:
                        target.unlink()
                    else:
                        data = bytearray(target.read_bytes())
                        data[0] ^= 1
                        target.chmod(0o600)
                        target.write_bytes(data)
                    with self.assertRaises(ValueError):
                        snapshot.verify(folder)

    def test_damaged_model_is_refused_before_pipeline_construction(self):
        import stanza
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "copy"
            shutil.copytree(self.directory, folder)
            (folder / "en/tokenize/ewt_nocharlm.pt").unlink()
            called = []
            def forbidden_loader(*args, **kwargs):
                called.append(True)
                raise AssertionError("Pipeline was reached before verification")
            with patch.object(stanza, "Pipeline", forbidden_loader):
                with self.assertRaises(ValueError):
                    snapshot.run(folder, "A test.")
            self.assertEqual(called, [])

    def test_prepare_refuses_existing_destination_without_changing_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "existing"
            folder.mkdir()
            marker = folder / "keep.txt"
            marker.write_text("keep")
            with self.assertRaises(FileExistsError):
                snapshot.prepare(folder)
            self.assertEqual(marker.read_text(), "keep")
            self.assertEqual(list(folder.iterdir()), [marker])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python check.py SNAPSHOT_DIRECTORY")
    SNAPSHOT_DIRECTORY = sys.argv.pop()
    unittest.main(verbosity=2)
