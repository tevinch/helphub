"""Check complete CSV files independently of CsvHelper and its generated mapping."""

import csv
import io
import sys
from pathlib import Path


NAMES = ['Café, large', 'A "quoted" name', "line one\r\nline two", "NULL", ""]
NOTES = ["new column", "x;y", "A note", "NULL", ""]
PAIRS = [[str(i + 1), name] for i, name in enumerate(NAMES)]
EXPANDED = [[str(i + 1), NOTES[i], name] for i, name in enumerate(NAMES)]
NAMES_FIRST = [[name, str(i + 1), NOTES[i]] for i, name in enumerate(NAMES)]
SPARSE = [[row[0], *([""] * 9), row[1]] for row in PAIRS]
SPARSE_HEADER = ["ID", *([""] * 9), "Name"]
EVOLVED_SPARSE = [[row[0], *([""] * 4), row[1], *([""] * 4), row[2]] for row in EXPANDED]
EVOLVED_SPARSE_HEADER = ["ID", *([""] * 4), "Note", *([""] * 4), "Name"]

EXPECTED = {
    "baseline.csv": ([SPARSE_HEADER, *SPARSE], ",", "\r\n"),
    "compact.csv": ([["ID", "Name"], *PAIRS], ",", "\r\n"),
    "evolved-default.csv": ([EVOLVED_SPARSE_HEADER, *EVOLVED_SPARSE], ",", "\r\n"),
    "evolved.csv": ([["ID", "Note", "Name"], *EXPANDED], ",", "\r\n"),
    "names-first.csv": ([["Name", "ID", "Note"], *NAMES_FIRST], ",", "\r\n"),
    "declaration-before.csv": ([["ID", "Name"], *PAIRS], ",", "\r\n"),
    "declaration-after.csv": ([["ID", "Note", "Name"], *EXPANDED], ",", "\r\n"),
    "empty.csv": ([["ID", "Name"]], ",", "\r\n"),
    "semicolon.csv": ([["Name", "ID", "Note"], *NAMES_FIRST], ";", "\n"),
    "headerless.csv": (EXPANDED, ",", "\r\n"),
    "default-after.csv": ([SPARSE_HEADER, *SPARSE], ",", "\r\n"),
}


def verify(directory: Path) -> None:
    for name, (expected_rows, delimiter, newline) in EXPECTED.items():
        path = directory / name
        if not path.is_file():
            raise AssertionError(f"Missing complete output file: {name}")
        actual = path.read_bytes()
        # Build literal expected rows with Python's independent RFC CSV encoder.
        expected = io.StringIO(newline="")
        csv.writer(expected, delimiter=delimiter, lineterminator=newline).writerows(expected_rows)
        if actual != expected.getvalue().encode("utf-8"):
            raise AssertionError(f"{name}: persisted UTF-8 bytes differ from expected CSV")
        rows = list(csv.reader(io.StringIO(actual.decode("utf-8"), newline=""), delimiter=delimiter))
        if rows != expected_rows:
            raise AssertionError(f"{name}: decoded fields or complete rows differ")
        width = len(expected_rows[0])
        if any(len(row) != width for row in rows):
            raise AssertionError(f"{name}: inconsistent column count")
    actual_names = {p.name for p in directory.iterdir() if p.is_file()}
    if actual_names != set(EXPECTED):
        raise AssertionError(f"Unexpected or missing output files: {sorted(actual_names ^ set(EXPECTED))}")
    if (directory / "baseline.csv").read_bytes() != (directory / "default-after.csv").read_bytes():
        raise AssertionError("The original generated export changed after explicit exports")


if __name__ == "__main__":
    output = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).parent / "output"
    if len(sys.argv) > 2:
        raise SystemExit("Usage: python3 verify_output.py [output-directory]")
    try:
        verify(output)
    except (AssertionError, OSError, UnicodeError, csv.Error) as error:
        raise SystemExit(f"FAIL: {error}") from error
    print(f"PASS: 11 complete files; exact UTF-8 bytes, every CSV field and all rows ({output})")
