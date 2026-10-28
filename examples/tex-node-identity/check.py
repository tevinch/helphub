"""Run the example and check the identity boundaries with real TexSoup objects."""

from pathlib import Path
import subprocess
import sys
import unittest

from TexSoup import TexSoup


class IdentityChecks(unittest.TestCase):
    def test_example_completes_comparison_and_shared_edit(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("example.py"))],
            text=True, capture_output=True, check=True,
        )
        self.assertEqual(result.stdout.splitlines(), [
            "Same wrapper: False",
            "Same parsed expression: True",
            "Value through the other wrapper: updated",
            "Serialized document contains the edit: True",
            "Repeated equal commands share an expression: False",
            "Separately parsed documents share an expression: False",
        ])

    def test_repeated_equal_commands_are_distinct_expressions(self):
        soup = TexSoup(r"\textit{same}\textit{same}")
        first, second = soup.find_all("textit")
        self.assertEqual(first.expr, second.expr)
        self.assertIsNot(first.expr, second.expr)
        self.assertIs(first.expr, soup.children[0].expr)
        self.assertIs(second.expr, soup.children[1].expr)

    def test_separate_identical_documents_have_distinct_expressions(self):
        source = r"\textit{same}"
        first = TexSoup(source).textit
        second = TexSoup(source).textit
        self.assertEqual(first.position, second.position)
        self.assertEqual(str(first), str(second))
        self.assertIsNot(first.expr, second.expr)

    def test_equal_offsets_and_content_do_not_identify_source_document(self):
        first = TexSoup(r"\textit{same} left").textit
        second = TexSoup(r"\textit{same} right").textit
        self.assertEqual(first.position, second.position)
        self.assertEqual(str(first), str(second))
        self.assertIsNot(first.expr, second.expr)

    def test_nested_alternate_paths_share_an_expression_and_edit(self):
        soup = TexSoup(r"\begin{document}\section{A \textit{word}}\end{document}")
        found = soup.find("textit")
        navigated = soup.document.section.textit
        self.assertIsNot(found, navigated)
        self.assertIs(found.expr, navigated.expr)
        navigated.string = "changed"
        self.assertEqual(found.string, "changed")
        self.assertEqual(str(soup), r"\begin{document}\section{A \textit{changed}}\end{document}")

    def test_position_is_not_updated_after_a_preceding_edit(self):
        soup = TexSoup(r"\textbf{a}\textit{b}")
        italic = soup.textit
        original_position = italic.position
        self.assertEqual(original_position, 10)
        soup.textbf.string = "a much longer prefix"
        self.assertEqual(italic.position, original_position)
        self.assertEqual(str(soup).index(r"\textit"), 29)
        self.assertIs(italic.expr, soup.textit.expr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
