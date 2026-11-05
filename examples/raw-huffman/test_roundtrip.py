"""Exercise the compiled file round trip, with an independent raw decoder."""
import pathlib
import random
import subprocess
import sys
import tempfile
import unittest
import zlib


PROGRAM = pathlib.Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 else None


class RoundTripTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.directory = pathlib.Path(self.workspace.name)

    def run_program(self, *paths):
        return subprocess.run([str(PROGRAM), *map(str, paths)], capture_output=True,
                              text=True, timeout=20)

    def assert_round_trip(self, payload, name="input.bin"):
        source = self.directory / name
        packed = self.directory / "packed.deflate"
        restored = self.directory / "restored.bin"
        source.write_bytes(payload)
        result = self.run_program(source, packed, restored)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(packed.is_file(), "CLI did not create compressed output")
        self.assertTrue(restored.is_file(), "CLI did not create restored output")
        self.assertEqual(source.read_bytes(), payload, "input was modified")
        self.assertEqual(restored.read_bytes(), payload, "round trip lost bytes")
        raw = packed.read_bytes()
        self.assertGreater(len(raw), 0, "even empty input needs a finished stream")
        decoder = zlib.decompressobj(wbits=-15)
        self.assertEqual(decoder.decompress(raw) + decoder.flush(), payload)
        self.assertTrue(decoder.eof, "raw DEFLATE stream was not finished")
        self.assertEqual(decoder.unused_data, b"")
        self.assertEqual(decoder.unconsumed_tail, b"")
        self.assertIn("verified", result.stdout)
        return result, raw

    def test_empty_file_finishes_a_raw_stream(self):
        self.assert_round_trip(b"")

    def test_one_byte_and_short_filename(self):
        self.assert_round_trip(b"x", "a")

    def test_445_byte_text_and_path_with_spaces(self):
        text = (b"Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 8)[:445]
        self.assertEqual(len(text), 445)
        self.assert_round_trip(text, "input with spaces")

    def test_binary_with_nuls_and_all_byte_values(self):
        self.assert_round_trip(bytes(range(256)) * 3)

    def test_many_input_and_output_chunks(self):
        self.assert_round_trip(random.Random(1370).randbytes(524_317))

    def test_repetitive_input_uses_huffman_strategy(self):
        payload = b"a" * 131_071
        _, raw = self.assert_round_trip(payload)
        # Default DEFLATE matches repeated strings and is tiny. Huffman-only
        # emits literals, so this distinguishes the requested strategy by its
        # actual output, without depending on byte-identical library versions.
        self.assertGreater(len(raw), len(payload) // 16)
        self.assertLess(len(zlib.compress(payload)), len(raw) // 10)

    def test_existing_packed_file_is_not_overwritten(self):
        source = self.directory / "source"
        packed = self.directory / "packed"
        restored = self.directory / "restored"
        source.write_bytes(b"original input")
        packed.write_bytes(b"keep packed")
        result = self.run_program(source, packed, restored)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(source.read_bytes(), b"original input")
        self.assertEqual(packed.read_bytes(), b"keep packed")
        self.assertFalse(restored.exists())

    def test_existing_restored_file_is_not_overwritten(self):
        source = self.directory / "source"
        packed = self.directory / "packed"
        restored = self.directory / "restored"
        source.write_bytes(b"original input")
        restored.write_bytes(b"keep restored")
        result = self.run_program(source, packed, restored)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(source.read_bytes(), b"original input")
        self.assertEqual(restored.read_bytes(), b"keep restored")
        self.assertFalse(packed.exists(), "failed run left its new packed file")

    def test_input_path_cannot_be_an_output(self):
        source = self.directory / "source"
        restored = self.directory / "restored"
        source.write_bytes(b"original input")
        result = self.run_program(source, source, restored)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(source.read_bytes(), b"original input")
        self.assertFalse(restored.exists())

    def test_same_two_output_paths_are_rejected(self):
        source = self.directory / "source"
        packed = self.directory / "packed"
        source.write_bytes(b"original input")
        result = self.run_program(source, packed, packed)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(source.read_bytes(), b"original input")
        self.assertFalse(packed.exists())

    def test_missing_input_creates_no_outputs(self):
        packed = self.directory / "packed"
        restored = self.directory / "restored"
        result = self.run_program(self.directory / "missing", packed, restored)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(packed.exists())
        self.assertFalse(restored.exists())

    def test_arguments_are_required(self):
        self.assertNotEqual(self.run_program().returncode, 0)


if __name__ == "__main__":
    if PROGRAM is None:
        raise SystemExit("Usage: python3 test_roundtrip.py /path/to/huffman_roundtrip")
    unittest.main(verbosity=2)
