"""A small interactive fuzzy picker built from Textual widgets."""

from collections.abc import Iterable
from dataclasses import dataclass
import sys

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.fuzzy import Matcher
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option


@dataclass(frozen=True)
class Choice:
    """Keep a display label separate from the value returned to the caller."""

    label: str
    value: str


class Picker(App[str | None]):
    """Filter choices and return the selected original value."""

    CSS = """
    Screen { padding: 1 2; }
    #hint { height: 2; }
    #results { height: 1fr; }
    #count { height: 1; }
    """
    BINDINGS = [
        Binding("up", "move(-1)", "Previous", show=False, priority=True),
        Binding("down", "move(1)", "Next", show=False, priority=True),
        Binding("enter", "choose", "Choose", show=False, priority=True),
        Binding("escape", "cancel", "Cancel", show=False, priority=True),
    ]

    def __init__(self, choices: Iterable[Choice]) -> None:
        """Take a snapshot so result identities stay stable while filtering."""
        super().__init__()
        self.choices = tuple(choices)

    def compose(self) -> ComposeResult:
        """Keep the query and the result list visible together."""
        yield Static("Type to filter · ↑/↓ move · Enter choose · Esc cancel", id="hint")
        yield Input(placeholder="Search labels", id="query")
        yield OptionList(id="results")
        yield Static(id="count")

    def on_mount(self) -> None:
        """Show all choices and start typing into the query."""
        self.show_matches("")
        self.query_one(Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Rebuild the visible options whenever the query changes."""
        self.show_matches(event.value)

    def show_matches(self, query: str) -> None:
        """Rank native fuzzy matches, preserving each original record index."""
        matcher = Matcher(query) if query else None
        matches = []
        for index, choice in enumerate(self.choices):
            score = matcher.match(choice.label) if matcher else 1.0
            if score > 0:
                matches.append((-score, index))
        matches.sort()

        results = self.query_one(OptionList)
        results.clear_options()
        results.add_options(
            Option(
                Text.assemble(
                    self.choices[index].label,
                    (f"  {self.choices[index].value}", "dim")
                    if self.choices[index].value != self.choices[index].label
                    else "",
                ),
                id=str(index),
            )
            for _, index in matches
        )
        results.highlighted = 0 if matches else None
        self.query_one("#count", Static).update(
            f"{len(matches)} matches" if matches else "No matches"
        )

    def action_move(self, direction: int) -> None:
        """Move through results while the query keeps keyboard focus."""
        results = self.query_one(OptionList)
        if results.option_count:
            index = results.highlighted if results.highlighted is not None else 0
            results.highlighted = (index + direction) % results.option_count

    def action_choose(self) -> None:
        """Return the source value, rather than its filtered display position."""
        option = self.query_one(OptionList).highlighted_option
        if option is not None and option.id is not None:
            self.exit(self.choices[int(option.id)].value)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Allow clicking a result as well as choosing it with the keyboard."""
        event.stop()
        self.exit(self.choices[int(event.option_id)].value)

    def action_cancel(self) -> None:
        """Leave without selecting a value."""
        self.exit(None)


if __name__ == "__main__":
    choices = (
        [Choice(value, value) for value in sys.argv[1:]]
        if sys.argv[1:]
        else [
            Choice("README.md", "docs/README.md"),
            Choice("README.md", "package/README.md"),
            Choice("notes.txt", "notes.txt"),
        ]
    )
    selected = Picker(choices).run()
    if selected is not None:
        print(selected)
    else:
        raise SystemExit(1)
