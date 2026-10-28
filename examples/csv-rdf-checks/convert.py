"""Check this example's CSV expressions before constructing its RDF graph."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
CLI_SHA256 = "0855bc869a35f83c4a97a5d31ca65e9f4ff16fd9c5a4f619ad7a7bd508053414"


def cli(args, query, source, format_name):
    result = subprocess.run(
        [args.java, "-jar", str(args.jar), "-q", str(HERE / query),
         "-v", "input=" + source.as_uri(), "-f", format_name],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode:
        raise ValueError("SPARQL Anything failed: " + result.stderr.strip())
    return result.stdout


def convert(args):
    args.jar = args.jar.resolve()
    source = args.input.resolve(strict=True)
    output = args.output.absolute()
    if output.exists() or output.is_symlink() or output.resolve() == source:
        raise ValueError("Output already exists; choose a new output path")
    if hashlib.sha256(args.jar.read_bytes()).hexdigest() != CLI_SHA256:
        raise ValueError("Expected the official SPARQL Anything 1.3.0 CLI jar")
    original = source.read_bytes()
    reader = csv.DictReader(io.StringIO(original.decode("utf-8-sig"), newline=""), strict=True)
    if not reader.fieldnames or len(reader.fieldnames) != 3 or set(reader.fieldnames) != {"subject", "text", "lang"}:
        raise ValueError("This example requires the CSV headers subject,text,lang")
    rows = list(reader)
    if not rows or any(None in row or None in row.values() for row in rows):
        raise ValueError("Expected complete CSV records with exactly three fields")
    with tempfile.TemporaryDirectory(prefix="csv-rdf-") as temp:
        snapshot = Path(temp) / "input.csv"
        snapshot.write_bytes(original)
        bindings = json.loads(cli(args, "preflight.rq", snapshot, "JSON"))["results"]["bindings"]
        if len(bindings) != len(rows):
            raise ValueError("Native preflight did not return every CSV record")
        issues = []
        for index, (row, binding) in enumerate(zip(rows, bindings), 1):
            if int(binding["record"]["value"]) != index:
                raise ValueError("Native preflight record positions do not match the CSV")
            for column in ("subject", "text", "lang"):
                if binding.get("source_" + column, {}).get("value") != row[column]:
                    raise ValueError("Native preflight did not preserve the source fields")
            if binding["subject_ok"]["value"] != "true":
                issues.append({"record": index, "function": "IRI", "arguments": [row["subject"]]})
            if binding["label_ok"]["value"] != "true":
                issues.append({"record": index, "function": "STRLANG", "arguments": [row["text"], row["lang"]]})
        if issues:
            print(json.dumps({"status": "rejected", "records_checked": len(rows), "issues": issues}, ensure_ascii=False))
            return 2
        graph = cli(args, "construct.rq", snapshot, "TURTLE").encode("utf-8")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(graph)
            # Publish the completed local result without replacing an existing file.
            os.link(temporary, output)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        print(json.dumps({"status": "written", "records_checked": len(rows)}))
        return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java", default="java", help="Java 21+ executable")
    parser.add_argument("--jar", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        return convert(args)
    except (OSError, ValueError, KeyError, TypeError, csv.Error, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "error", "message": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
