# Hide the cursor while keeping a TextBox editable

For **XenoAtom.Terminal.UI 3.10.0** and **.NET 10**. This example keeps keyboard input, selection and focus traversal available while hiding the terminal cursor in one `TextBox`.

`TextBox` inherits the public `ICursorProvider` implementation from `TextEditorBase`. A small subclass can explicitly reimplement that interface and return `false`:

```csharp
using XenoAtom.Terminal.UI.Controls;
using XenoAtom.Terminal.UI.Input;

public sealed class CursorlessTextBox(string? text = null)
    : TextBox(text), ICursorProvider
{
    bool ICursorProvider.TryGetCursorCell(out int x, out int y)
    {
        x = 0;
        y = 0;
        return false;
    }
}
```

Use `new CursorlessTextBox("Initial text")` where you would otherwise create a `TextBox`. The explicit interface implementation matters: the inherited method is not virtual, so this is interface reimplementation rather than an `override`. The host consults `ICursorProvider` on the focused control when rendering the terminal cursor.

Run the complete form from this directory:

```sh
dotnet restore --locked-mode
dotnet run
```

Edit the existing text, press **Tab** to reach **Submit**, then **Enter**. The submitted value is printed after the form closes. **Ctrl+Q** exits without submitting. To copy the behavior into an existing app, copy `CursorlessTextBox.cs`; the verification file is only needed to run this example's checks.

The control stays focusable and editable. Other text boxes still display their cursors, and leaving the app lets the host restore the terminal cursor. This hides the terminal insertion cursor; it does not mask text, disable selection highlighting, or affect the mouse pointer. Removing the caret can make editing harder to follow, so use it only where the surrounding UI makes the current editing position clear.

## Verify the interaction

```sh
dotnet run -- --verify
```

The check opens the real public host over `InMemoryTerminalBackend`, sends keyboard events and verifies the cursor visibility commands, focus changes, retained content, rendered text, repeated editing and final submission. A normal `TextBox` is included as a visibility control. It completes with 17 `PASS` lines. Replacing the custom input with a normal `TextBox` makes the hidden-cursor check fail.

The example also passed a software-operated macOS PTY run: editing the initial text, tabbing to Submit and pressing Enter produced the exact submitted value, with hide/restore cursor commands. These checks do not constitute human testing or confirmation from the original requester.

References: [original question](https://github.com/XenoAtom/XenoAtom.Terminal.UI/issues/54), [public cursor interface](https://github.com/XenoAtom/XenoAtom.Terminal.UI/blob/3.10.0/src/XenoAtom.Terminal.UI/Input/ICursorProvider.cs), [TextEditorBase](https://github.com/XenoAtom/XenoAtom.Terminal.UI/blob/3.10.0/src/XenoAtom.Terminal.UI/Controls/TextEditorBase.cs), [host cursor selection](https://github.com/XenoAtom/XenoAtom.Terminal.UI/blob/3.10.0/src/XenoAtom.Terminal.UI/TerminalApp.cs).

## Optional coffee

This example is free. If it saves you some time, a small, entirely optional coffee is appreciated.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
