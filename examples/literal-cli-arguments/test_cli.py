"""Run the example through actual CLI processes, without mocks."""

from pathlib import Path
import json
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent


class CommandLineTests(unittest.TestCase):
    def run_cli(self, filename, *arguments):
        result = subprocess.run(
            [sys.executable, str(ROOT / filename), *arguments],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout

    def test_original_version_argument_keeps_its_type_and_text(self):
        # Removing the explicit parser must expose the reported float coercion.
        for arguments in (("1.10",), ("--arg=1.10",), ("--arg", "1.10")):
            with self.subTest(arguments=arguments):
                self.assertEqual(
                    self.run_cli("tp.py", *arguments),
                    "Hello! <class 'str'> 1.10\n",
                )

    def test_literal_like_text_stays_exact(self):
        # Replacing the parser with default inference loses several of these values.
        cases = (
            ("1.1", "Hello! <class 'str'> 1.1\n"),
            ("0010", "Hello! <class 'str'> 0010\n"),
            ("True", "Hello! <class 'str'> True\n"),
            ("False", "Hello! <class 'str'> False\n"),
            ("None", "Hello! <class 'str'> None\n"),
            ("1e2", "Hello! <class 'str'> 1e2\n"),
            ("-1.10", "Hello! <class 'str'> -1.10\n"),
            (" 1.10 ", "Hello! <class 'str'>  1.10 \n"),
            ("", "Hello! <class 'str'> \n"),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(self.run_cli("tp.py", value), expected)

    def test_selective_parser_keeps_other_arguments_numeric(self):
        # Applying str to all arguments would wrongly make count a string.
        for arguments in (
            ("1.10", "2"),
            ("--arg=1.10", "--count=2"),
            ("--arg", "1.10", "--count", "2"),
        ):
            with self.subTest(arguments=arguments):
                self.assertEqual(
                    json.loads(self.run_cli("selective.py", *arguments)),
                    {"arg": "1.10", "arg_type": "str", "count": 2, "count_type": "int"},
                )


if __name__ == "__main__":
    unittest.main()

