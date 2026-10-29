"""Exercise the frozen-time recipe and the library's migration command."""

import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from importlib.metadata import version


SOURCE = Path(__file__).with_name("test_frozen_utc.py").read_text(encoding="utf-8")
DESTINATION = "2025-12-11T12:01:02Z"
ENV = os.environ | {
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "PYTEST_ADDOPTS": "",
    "PY_COLORS": "0",
    "PYTHONDONTWRITEBYTECODE": "1",
}


def run(arguments, directory):
    result = subprocess.run(
        [sys.executable, *arguments],
        cwd=directory,
        env=ENV,
        text=True,
        capture_output=True,
        timeout=30,
    )
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    return result


def pytest_file(path, *, failure_line=None):
    result = run(
        ["-m", "pytest", "-c", os.devnull, "-p", "no:cacheprovider",
         "-v", "--tb=short", path.name],
        path.parent,
    )
    assert "::test_freezegun PASSED" in result.stdout
    if failure_line is None:
        assert result.returncode == 0
        assert "::test_time_machine PASSED" in result.stdout
        assert "2 passed" in result.stdout
    else:
        assert result.returncode == 1
        assert "::test_time_machine FAILED" in result.stdout
        assert f"{path.name}:{failure_line}: in test_time_machine" in result.stdout
        assert "AssertionError" in result.stdout
        assert "1 failed, 1 passed" in result.stdout


def main():
    print(f"Python {sys.version.split()[0]}; time-machine {version('time-machine')}")
    assert SOURCE.count(", tick=False") == 1
    original = SOURCE.replace(", tick=False", "")
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        positive = directory / "test_frozen_utc.py"
        positive.write_text(SOURCE, encoding="utf-8")
        for number in (1, 2):
            print(f"\nFrozen recipe, independent pytest run {number}", flush=True)
            pytest_file(positive)

        # This controlled negative adds a pause to make elapsed time observable.
        # It is separate from the original, unmodified reproduction.
        tree = ast.parse(original)
        test = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == "test_time_machine")
        second_assertion = test.body[1]
        assert isinstance(second_assertion, ast.Assert)
        lines = original.splitlines()
        lines.insert(second_assertion.lineno - 1, "    __import__('time').sleep(0.02)")
        negative = directory / "test_default_ticking.py"
        negative.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\nControlled negative: tick=False omitted, pause between reads", flush=True)
        pytest_file(negative, failure_line=second_assertion.lineno + 1)

        # Give the official CLI only the original freezegun comparison test.
        prefix = original[:original.index("@time_machine.travel(")]
        comparison = original[original.index("@freeze_time("):]
        migrated = directory / "test_migrated.py"
        migrated.write_text(prefix + comparison, encoding="utf-8")
        before = ast.parse(migrated.read_text(encoding="utf-8")).body[-1]
        print("\nOfficial migration CLI on a disposable test copy", flush=True)
        result = run(["-m", "time_machine", "migrate", migrated.name], directory)
        # The native CLI exits 1 when it rewrites a file, and 0 for no changes.
        assert result.returncode == 1
        assert result.stderr == f"Rewriting {migrated.name}\n"
        rewritten = migrated.read_text(encoding="utf-8")
        after = ast.parse(rewritten).body[-1]
        decorator = after.decorator_list[0]
        assert ast.unparse(decorator.func) == "time_machine.travel"
        assert ast.literal_eval(decorator.args[0]) == DESTINATION
        assert {item.arg: ast.literal_eval(item.value)
                for item in decorator.keywords} == {"tick": False}
        assert ast.dump(ast.Module(body=before.body, type_ignores=[])) == ast.dump(
            ast.Module(body=after.body, type_ignores=[]))
        assert "time_machine.naive_mode = time_machine.NaiveMode.ERROR" in rewritten
        print(rewritten, end="")
        repeat = run(["-m", "time_machine", "migrate", migrated.name], directory)
        assert repeat.returncode == 0
        assert not repeat.stdout and not repeat.stderr
        assert migrated.read_text(encoding="utf-8") == rewritten
        result = run(
            ["-m", "pytest", "-c", os.devnull, "-p", "no:cacheprovider",
             "-v", "--tb=short", migrated.name], directory)
        assert result.returncode == 0
        assert "::test_freezegun PASSED" in result.stdout
        assert "1 passed" in result.stdout

    print("\nAll frozen reads, negative control, and migrated test checked.")


if __name__ == "__main__":
    main()
