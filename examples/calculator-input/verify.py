"""Exercise the actual console process. Requires Python 3 and the .NET 8 SDK."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


def build(source, destination, dotnet):
    destination.mkdir()
    for name in ("Program.cs", "Calculator.csproj"):
        shutil.copy2(source / name, destination / name)
    result = subprocess.run(
        [dotnet, "build", "-c", "Release", "--nologo"], cwd=destination,
        text=True, capture_output=True, timeout=120,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return destination / "bin/Release/net8.0/Calculator.dll"


def verify_process(dotnet, dll):
    env = dict(os.environ, LANG="en_US.UTF-8", LC_ALL="en_US.UTF-8")
    count = 0

    def run(data, expected=(), messages=(), results=None, invalid=None, culture=None):
        nonlocal count
        settings = env if culture is None else dict(env, LANG=culture, LC_ALL=culture)
        result = subprocess.run([dotnet, str(dll)], input=data, text=True,
                                capture_output=True, env=settings, timeout=5)
        assert result.returncode == 0, (data, result.returncode, result.stderr)
        assert result.stderr == "", result.stderr
        for text in (*expected, *messages):
            assert text in result.stdout, (text, result.stdout)
        if results is not None:
            assert result.stdout.count("Result: ") == results, result.stdout
        if invalid is not None:
            assert result.stdout.count("Enter a finite number.") == invalid, result.stdout
        count += 1
        return result.stdout

    run("text\n\n3e100\nNaN\nInfinity\n-Infinity\n1.5\n+\n2.25\n4\n*\n3\n",
        expected=("Result: 1.5 + 2.25 = 3.75", "Result: 4 * 3 = 12"), results=2, invalid=6)
    run("8\n/\nword\n\n3e100\nNaN\n0\n2\n", expected=("Result: 8 / 2 = 4",),
        messages=("The divisor cannot be zero.",), results=1, invalid=4)
    run("7.5\n+\n2.5\n7.5\n-\n2.5\n2.5\n*\n4\n3\n/\n2\n7.5\n%\n2\n2.25\nsqrt\n",
        expected=("Result: 7.5 + 2.5 = 10", "Result: 7.5 - 2.5 = 5",
                  "Result: 2.5 * 4 = 10", "Result: 3 / 2 = 1.5",
                  "Result: 7.5 % 2 = 1.5", "Result: sqrt(2.25) = 1.5"), results=6)
    run("7\n%\n0\n2\n", expected=("Result: 7 % 2 = 1",),
        messages=("The divisor cannot be zero.",), results=1)
    run("2\n?\n+\n3\n", expected=("Result: 2 + 3 = 5",),
        messages=("Choose +, -, *, /, %, or sqrt.",), results=1)
    run("-4\nsqrt\n9\nsqrt\n", expected=("Result: sqrt(9) = 3",),
        messages=("Square root requires a nonnegative number.",), results=1)
    run("3e38\n+\n3e38\n1\n+\n2\n", expected=("Result: 1 + 2 = 3",),
        messages=("Result is outside the finite Single range.",), results=1)
    run("-2.5\n*\n+4\n", expected=("Result: -2.5 * 4 = -10",), results=1)
    run("3000000000\n-\n3000000000\n", expected=(" = 0",), results=1)
    run("1,5\n+\n2,25\n", expected=("Result: 1,5 + 2,25 = 3,75",),
        results=1, culture="de_DE.UTF-8")
    for data in ("", "x\n", "2\n", "2\n?\n", "2\n+\n", "2\n+\nx\n", "2\n/\n0\n"):
        run(data, results=0)
    print(f"PASS: {count} complete console-process scenarios")


def verify_integer_snippet(source, destination, dotnet):
    readme = (source / "README.md").read_text()
    heading = readme.index("## If the input must be an integer")
    match = re.search(r"```csharp\n(.*?)\n```", readme[heading:], re.S)
    assert match, "Missing integer snippet"
    destination.mkdir()
    shutil.copy2(source / "Calculator.csproj", destination / "Calculator.csproj")
    program = """using System;
class IntegerCheck
{
    static void Main()
    {
        foreach (string text in new[] { "hello", "", "2147483648", "-2147483648", "2147483647", " +42 " })
        {
            Console.SetIn(new System.IO.StringReader(text + "\\n"));
            Check();
        }
    }
    static void Check()
    {
SNIPPET
    }
}
""".replace("SNIPPET", match.group(1))
    (destination / "Program.cs").write_text(program)
    result = subprocess.run([dotnet, "build", "-c", "Release", "--nologo"],
                            cwd=destination, text=True, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run([dotnet, str(destination / "bin/Release/net8.0/Calculator.dll")],
                            text=True, capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["Enter a 32-bit integer."] * 3 + ["-2147483648", "2147483647", "42"], result.stdout
    print("PASS: README integer snippet, including both Int32 boundaries")


def main():
    source = Path(__file__).resolve().parent
    dotnet = str(Path(sys.argv[1]).resolve()) if len(sys.argv) > 1 else "dotnet"
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        dll = build(source, root / "calculator", dotnet)
        verify_process(dotnet, dll)
        verify_integer_snippet(source, root / "integer", dotnet)


if __name__ == "__main__":
    main()
