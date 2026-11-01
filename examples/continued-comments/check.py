"""Exercise complete native parsing and transformed comment values."""

import json
from pathlib import Path
import subprocess
import sys
import unittest

from lark import Lark, UnexpectedInput

from comments import GRAMMAR, parser


class CommentChecks(unittest.TestCase):
    def test_original_three_physical_lines_become_one_comment(self):
        """Omitting token transformation leaves continuation pairs in the value."""
        source = "# this is a comment \\\nthat spans multiple \\\nlines\n"
        self.assertEqual(
            parser.parse(source),
            ["# this is a comment that spans multiple lines\n"],
        )

    def test_adjacent_comments_remain_separate_on_repeated_parses(self):
        """Consuming an ordinary newline must not merge the following comment."""
        for _ in range(2):
            self.assertEqual(
                parser.parse("# first \\\ncontinued\n# second\n"),
                ["# first continued\n", "# second\n"],
            )

    def test_ordinary_backslashes_and_noncontinued_newlines_are_preserved(self):
        """Removing every backslash would corrupt paths and literal punctuation."""
        cases = [
            (r"# path C:\temp\notes" + "\n", [r"# path C:\temp\notes" + "\n"]),
            ("# slash \\ \n# next\n", ["# slash \\ \n", "# next\n"]),
            (r"# two \\" + "\ncontinued\n", [r"# two \continued" + "\n"]),
            ("# end " + chr(92), ["# end " + chr(92)]),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(parser.parse(source), expected)

    def test_crlf_eof_and_unicode(self):
        """A CRLF continuation is one pair, while the final line ending stays intact."""
        self.assertEqual(
            parser.parse("# café \\\r\ncontinued\r\n# final"),
            ["# café continued\r\n", "# final"],
        )

    def test_noncontinued_noncomment_input_is_rejected(self):
        """A too-broad terminal must not silently consume another source line."""
        with self.assertRaises(UnexpectedInput):
            parser.parse("# finished\nnot a comment\n")

    def test_raw_token_and_semantic_value_are_distinct(self):
        """The raw lexer token contains the pair; the installed Transformer removes it."""
        source = "# first\\\nsecond\n"
        raw = Lark(GRAMMAR, parser="lalr").parse(source)
        self.assertEqual(len(raw.children), 1)
        self.assertEqual(str(raw.children[0]), "# first\\\nsecond\n")
        self.assertEqual(parser.parse(source), ["# firstsecond\n"])

    def test_complete_example_process_prints_the_joined_values(self):
        """The executable example must run its parse, not merely define a callback."""
        run = subprocess.run(
            [sys.executable, "comments.py"],
            cwd=Path(__file__).resolve().parent,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(json.loads(run.stdout), [
            "# this is a comment that spans multiple lines\n",
            "# path C:\\temp\\notes\n",
        ])


if __name__ == "__main__":
    unittest.main(verbosity=2)
