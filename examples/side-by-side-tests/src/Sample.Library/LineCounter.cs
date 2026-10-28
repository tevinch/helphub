namespace Sample.Library;

public static class LineCounter
{
    public static int CountNonEmpty(string text) =>
        text.Split('\n').Count(line => !string.IsNullOrWhiteSpace(line));
}
