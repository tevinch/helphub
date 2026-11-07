using XenoAtom.Terminal;
using XenoAtom.Terminal.UI;
using XenoAtom.Terminal.UI.Controls;

if (args.Contains("--verify"))
{
    Verification.Run();
    return;
}

var input = new CursorlessTextBox("Edit this text");
string? submitted = null;
var root = new VStack(
    new TextBlock("Edit the text, then Tab to Submit and press Enter."),
    input,
    new Button("Submit").Click(() => submitted = input.Text)
);

Terminal.Run(root, () => submitted is null
    ? TerminalLoopResult.Continue
    : TerminalLoopResult.StopAndKeepVisual);

if (submitted is not null)
    Console.WriteLine($"Submitted: {submitted}");
