using XenoAtom.Terminal.UI.Controls;
using XenoAtom.Terminal.UI.Input;

public sealed class CursorlessTextBox(string? text = null) : TextBox(text), ICursorProvider
{
    bool ICursorProvider.TryGetCursorCell(out int x, out int y)
    {
        x = 0;
        y = 0;
        return false;
    }
}
