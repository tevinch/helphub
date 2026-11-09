"""Check the native linter and the complete generated documentation."""

import ast
from html.parser import HTMLParser
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
PYDOC = [sys.executable, "-c", "from pydoclint.main import main; main()"]
EXPECTED = [
    "dict[str, list[int]]",
    "dict[str, list[int]]",
    "dict[str, dict[str, list[int]]]",
    "dict[str, dict[str, list[int]]]",
]
NAMES = ["first", "second", "third", "fourth"]


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def lint(path):
    return subprocess.run(
        PYDOC + ["--config", str(ROOT / "pyproject.toml"), str(path)],
        text=True, capture_output=True, check=False,
    )


def main():
    source = (ROOT / "example.py").read_text()
    positive = lint(ROOT / "example.py")
    assert positive.returncode == 0, positive.stdout + positive.stderr
    assert "DOC" not in positive.stdout + positive.stderr
    print("PASS: original options and return-type checking; no DOC diagnostics")

    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef))
    assert [ast.unparse(n) for n in node.returns.slice.elts] == EXPECTED
    doc = ast.get_docstring(node)
    headers = [line for line in doc.splitlines() if " : " in line]
    assert headers[1:] == [f"{n} : {t}" for n, t in zip(NAMES, EXPECTED)]
    assert all(len(line) <= 79 for line in source.splitlines())
    spec = importlib.util.spec_from_file_location("tuple_example", ROOT / "example.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.f({}) == (
        {"first": [1]}, {"second": [2]},
        {"third": {"inner": [3]}}, {"fourth": {"inner": [4]}},
    )
    print("PASS: four ordered matching types, wrapped prose, same four-part value")

    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        bad = work / "bad.py"
        marker = "    Returns\n    -------\n"
        start = source.index(marker) + len(marker)
        end = source.index('    """', start)
        bad_returns = (
            "    tuple[\n"
            "        dict[str, list[int]],\n"
            "        dict[str, list[int]],\n"
            "        dict[str, dict[str, list[int]]],\n"
            "        dict[str, dict[str, list[int]]],\n"
            "    ]\n"
            "        A wrapped description of the tuple.\n"
        )
        controls = {
            "multiline tuple": source[:start] + bad_returns + source[end:],
            "missing fourth entry": source.replace(
                "    fourth : dict[str, dict[str, list[int]]]\n"
                "        The fourth collection.\n", ""
            ),
            "mismatched type": source.replace(
                "    first : dict[str, list[int]]", "    first : dict[str, list[str]]"
            ),
        }
        for name, value in controls.items():
            assert value != source, f"Control did not change source: {name}"
            bad.write_text(value)
            result = lint(bad)
            assert result.returncode != 0 and "DOC203" in result.stdout + result.stderr, (
                name, result.stdout, result.stderr
            )
        print("PASS: DOC203 catches multiline tuple, missing entry and wrong type")

        docs = work / "docs"
        shutil.copytree(ROOT / "docs", docs, ignore=shutil.ignore_patterns("autoapi"))
        (work / "example.py").write_text(
            source + '\nraise RuntimeError("AutoAPI must parse without importing")\n'
        )
        output = work / "html"
        built = subprocess.run(
            [sys.executable, "-m", "sphinx", "-W", "--keep-going", "-b", "html",
             str(docs), str(output)],
            text=True, capture_output=True, check=False,
        )
        assert built.returncode == 0, built.stdout + built.stderr
        rst = (docs / "autoapi" / "example" / "index.rst").read_text()
        page = (output / "autoapi" / "example" / "index.html").read_text()
        parsed = PageText()
        parsed.feed(page)
        text = " ".join("".join(parsed.parts).split())
        assert "example.f" in page
        returns = re.search(
            r'<dt[^>]*>Returns.*?</dt>\s*<dd[^>]*>(.*?)</dd>', page, re.S
        )
        assert returns is not None, "No rendered Returns field"
        return_text = PageText()
        return_text.feed(returns.group(1))
        rendered = " ".join("".join(return_text.parts).split())
        assert returns.group(1).count("<li>") == 4
        for name, expected_type in zip(NAMES, EXPECTED):
            assert name in rst
            assert f"{name} ({expected_type})" in rendered
        assert "dict[str, dict[str, list[int]]]" in rst
        assert "another line without changing" in text
        print("PASS: AutoAPI RST and Sphinx HTML include all entries and wrapped prose")
        print("PASS: warning-as-error build; AutoAPI did not import the source module")


if __name__ == "__main__":
    main()
