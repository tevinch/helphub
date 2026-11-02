#!/usr/bin/env python3
"""Check the compiled example through its command-line interface."""
from pathlib import Path
import subprocess
import sys
import unittest


class CommandLineTests(unittest.TestCase):
    def run_cli(self, arguments):
        return subprocess.run(
            [str(BINARY), *arguments],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def assert_rejected(self, arguments):
        result = self.run_cli(arguments)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.strip(), "Rejected input needs a diagnostic")

    def test_declared_options_complete_the_formatting_operation(self):
        cases = [
            ([], "value: 0\n"),
            (["--label", "tasks", "--number", "7"], "tasks: 7\n"),
            (["-l", "items in queue", "-n", "-2"], "items in queue: -2\n"),
            (["--label", "tasks", "--number", "7", "--"], "tasks: 7\n"),
        ]
        for arguments, expected_line in cases:
            with self.subTest(arguments=arguments):
                result = self.run_cli(arguments)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, expected_line)
                self.assertEqual(result.stderr, "")

    def test_help_completes_without_formatting_a_line(self):
        for arguments in [["--help"], ["-h"]]:
            with self.subTest(arguments=arguments):
                result = self.run_cli(arguments)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, "")
                self.assertTrue(result.stdout.startswith("Format a labelled integer."))
                self.assertIn("Usage:", result.stdout)
                self.assertIn("--label", result.stdout)
                self.assertIn("--number", result.stdout)
                self.assertNotIn("value: 0\n", result.stdout)

    def test_native_parse_errors_prevent_formatting(self):
        for arguments in [
            ["--unknown"],
            ["-z"],
            ["--number", "not-an-integer"],
            ["--number"],
        ]:
            with self.subTest(arguments=arguments):
                self.assert_rejected(arguments)

    def test_plain_extra_arguments_prevent_formatting(self):
        for arguments in [
            ["stray"],
            ["--label", "tasks", "--number", "7", "stray"],
        ]:
            with self.subTest(arguments=arguments):
                self.assert_rejected(arguments)

    def test_separator_does_not_enable_positional_arguments(self):
        for arguments in [["--", "word"], ["--", "--unknown"]]:
            with self.subTest(arguments=arguments):
                self.assert_rejected(arguments)

    def test_extra_arguments_are_rejected_before_help(self):
        for arguments in [["--help", "word"], ["--help", "--", "--unknown"]]:
            with self.subTest(arguments=arguments):
                self.assert_rejected(arguments)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 verify.py /path/to/label-number")
    BINARY = Path(sys.argv[1]).resolve()
    unittest.main(argv=[sys.argv[0]], verbosity=2)
