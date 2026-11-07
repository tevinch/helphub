using System.Text.RegularExpressions;
using System.Xml.Linq;
using XenoAtom.Terminal;
using XenoAtom.Terminal.Backends;
using XenoAtom.Terminal.UI;
using XenoAtom.Terminal.UI.Controls;

internal static class Verification
{
    public static void Run()
    {
        var backend = new InMemoryTerminalBackend(new TerminalSize(70, 12));
        using var session = Terminal.Open(backend, new TerminalOptions { ImplicitStartInput = true }, force: true);
        var normal = new TextBox("normal");
        var input = new CursorlessTextBox("seed");
        var next = new TextBox("next");
        string? submitted = null;
        var submit = new Button("Submit").Click(() => submitted = input.Text);
        var root = new VStack(normal, input, next, submit);
        var frame = 0;
        var stage = 0;
        var completed = false;
        var observations = new List<string>();

        void Check(bool condition, string reason)
        {
            if (!condition) throw new InvalidOperationException(reason);
            observations.Add(reason);
        }
        void Key(TerminalKey key, TerminalModifiers modifiers = TerminalModifiers.None)
            => backend.PushEvent(new TerminalKeyEvent { Key = key, Modifiers = modifiers });
        bool CursorShown()
        {
            var commands = Regex.Matches(backend.GetOutText(), "\\x1b\\[\\?25([hl])");
            if (commands.Count == 0) throw new InvalidOperationException("No cursor visibility command was emitted.");
            return commands[^1].Groups[1].Value == "h";
        }

        Terminal.Run(root, context =>
        {
            // Input arrives through the host's asynchronous relay. A focus/text
            // observation gets its own stage before inspecting the rendered frame.
            if (++frame > 150) throw new InvalidOperationException($"Acceptance stalled at stage {stage}.");
            switch (stage)
            {
                case 0 when ReferenceEquals(context.App.FocusedElement, normal):
                    Check(ReferenceEquals(context.App.FocusedElement, normal), "Normal input has initial focus.");
                    stage++;
                    break;
                case 1:
                    Check(CursorShown(), "Normal input shows the terminal cursor.");
                    Key(TerminalKey.Tab);
                    stage++;
                    break;
                case 2 when ReferenceEquals(context.App.FocusedElement, input):
                    Check(ReferenceEquals(context.App.FocusedElement, input), "Tab focuses the cursorless input.");
                    stage++;
                    break;
                case 3:
                    Check(!CursorShown(), "Focused cursorless input hides the terminal cursor.");
                    Check(input.Text == "seed", "Existing input content is preserved.");
                    Key(TerminalKey.End);
                    backend.PushEvent(new TerminalTextEvent { Text = "abc" });
                    Key(TerminalKey.Left);
                    Key(TerminalKey.Backspace);
                    backend.PushEvent(new TerminalTextEvent { Text = "X" });
                    stage++;
                    break;
                case 4 when input.Text == "seedaXc":
                    Check(input.Text == "seedaXc", "Typing, Left and Backspace produce seedaXc.");
                    stage++;
                    break;
                case 5:
                    Check(!CursorShown(), "Editing keeps the terminal cursor hidden.");
                    var renderedText = string.Concat(XDocument.Parse(context.App.CaptureSvg())
                        .Descendants().Where(e => e.Name.LocalName == "text").Select(e => e.Value));
                    Check(renderedText.Contains("seedaXc"), "The edited text is present in the rendered frame.");
                    Key(TerminalKey.Tab);
                    stage++;
                    break;
                case 6 when ReferenceEquals(context.App.FocusedElement, next):
                    Check(ReferenceEquals(context.App.FocusedElement, next), "Tab reaches the next normal input.");
                    stage++;
                    break;
                case 7:
                    Check(CursorShown(), "The next normal input shows its cursor.");
                    Key(TerminalKey.Tab, TerminalModifiers.Shift);
                    stage++;
                    break;
                case 8 when ReferenceEquals(context.App.FocusedElement, input):
                    Check(ReferenceEquals(context.App.FocusedElement, input), "Shift+Tab returns to cursorless input.");
                    stage++;
                    break;
                case 9:
                    Check(!CursorShown(), "Returning to cursorless input hides the cursor again.");
                    Key(TerminalKey.End);
                    backend.PushEvent(new TerminalTextEvent { Text = "!" });
                    stage++;
                    break;
                case 10 when input.Text == "seedaXc!":
                    Check(input.Text == "seedaXc!", "Repeated editing retains the exact text.");
                    Key(TerminalKey.Tab);
                    Key(TerminalKey.Tab);
                    stage++;
                    break;
                case 11 when ReferenceEquals(context.App.FocusedElement, submit):
                    Check(ReferenceEquals(context.App.FocusedElement, submit), "Keyboard traversal reaches Submit.");
                    Key(TerminalKey.Enter);
                    stage++;
                    break;
                case 12 when submitted is not null:
                    Check(submitted == "seedaXc!", "Enter submits the exact edited value.");
                    completed = true;
                    stage++;
                    return TerminalLoopResult.StopAndKeepVisual;
            }
            return TerminalLoopResult.Continue;
        }, new TerminalRunOptions());

        Check(completed && stage == 13, "The host executed and completed every acceptance stage.");
        Check(backend.TryGetCursorVisible(out var visible) && visible, "Exit restores the original visible cursor state.");
        foreach (var observation in observations) Console.WriteLine($"PASS {observation}");
    }
}
