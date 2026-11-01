"""Run the picker's complete interaction checks: python check.py."""

import unittest

from textual.messages import ExitApp
from textual.widgets import Input, OptionList

from picker import Choice, Picker


class PickerChecks(unittest.IsolatedAsyncioTestCase):
    async def test_fuzzy_filter_navigation_returns_original_value(self):
        """Using a filtered row index as identity selects the wrong file."""
        app = Picker([
            Choice("notes.txt", "notes.txt"),
            Choice("README.md", "docs/README.md"),
            Choice("README.md", "package/README.md"),
        ])
        async with app.run_test() as pilot:
            await pilot.press("r", "d")
            results = app.query_one(OptionList)
            self.assertEqual(app.query_one(Input).value, "rd")
            self.assertEqual(results.option_count, 2)
            await pilot.press("down")
            self.assertIs(app.focused, app.query_one(Input))
            await pilot.press("enter")
        self.assertEqual(app.return_value, "package/README.md")

    async def test_stronger_match_is_ranked_before_earlier_source_item(self):
        """Ignoring the native match score must not silently change the chosen item."""
        app = Picker([Choice("remote_data", "loose"), Choice("rd", "exact")])
        async with app.run_test() as pilot:
            await pilot.press("r", "d", "enter")
        self.assertEqual(app.return_value, "exact")

    async def test_no_matches_can_be_cleared_and_selected_repeatedly(self):
        """An empty result set must neither select a stale row nor trap input."""
        for _ in range(2):
            app = Picker([Choice("alpha.txt", "a"), Choice("beta.txt", "b")])
            async with app.run_test() as pilot:
                await pilot.press("z", "z", "z")
                self.assertEqual(app.query_one(OptionList).option_count, 0)
                await pilot.press("enter")
                self.assertTrue(app.is_running)
                self.assertIsNone(app.return_value)
                await pilot.press("backspace", "backspace", "backspace", "b", "t")
                self.assertEqual(app.query_one(OptionList).option_count, 1)
                await pilot.press("enter")
            self.assertEqual(app.return_value, "b")

    async def test_empty_query_wraps_navigation_and_escape_cancels(self):
        """Navigation while typing must retain input focus and source order."""
        app = Picker([Choice("one", "first"), Choice("two", "second")])
        async with app.run_test() as pilot:
            self.assertEqual(app.query_one(OptionList).option_count, 2)
            await pilot.press("up", "enter")
        self.assertEqual(app.return_value, "second")

        cancelled = Picker([Choice("one", "first")])
        messages = []
        async with cancelled.run_test(message_hook=messages.append) as pilot:
            await pilot.press("escape")
            self.assertTrue(any(isinstance(message, ExitApp) for message in messages))
        self.assertIsNone(cancelled.return_value)

    async def test_empty_choices_remain_usable(self):
        """Enter with no supplied choices must keep running until cancelled."""
        app = Picker([])
        messages = []
        async with app.run_test(message_hook=messages.append) as pilot:
            await pilot.press("enter")
            self.assertTrue(app.is_running)
            await pilot.press("escape")
            self.assertTrue(any(isinstance(message, ExitApp) for message in messages))
        self.assertIsNone(app.return_value)

    async def test_literal_unicode_label_can_be_clicked(self):
        """File-name brackets must not become markup or change selection identity."""
        app = Picker([Choice("[café].txt", "reports/original.txt")])
        async with app.run_test() as pilot:
            await pilot.press("c", "a", "f", "é")
            results = app.query_one(OptionList)
            self.assertEqual(results.option_count, 1)
            self.assertEqual(
                results.get_option_at_index(0).prompt.plain,
                "[café].txt  reports/original.txt",
            )
            await pilot.click("#results", offset=(3, 1))
        self.assertEqual(app.return_value, "reports/original.txt")


if __name__ == "__main__":
    unittest.main(verbosity=2)
