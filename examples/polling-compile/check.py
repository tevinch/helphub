#!/usr/bin/env python3
"""Run real compiler checks in a disposable source/output project (POSIX only)."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

from pypdf import PdfReader


def wait_for(predicate, description, timeout=15):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if predicate():
            return
        time.sleep(0.04)
    raise AssertionError("Timed out: " + description)


def pdf_text(path):
    try:
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    except Exception:
        return ""  # The real compiler may currently be writing the PDF.


def document(marker, busy=False):
    work = "#let total = range(2000000).fold(0, (a, b) => a + b)\n#total\n" if busy else ""
    return ('#import "parts/chapter.typ": chapter\n'
            '#import ".hidden-part.typ": hidden\n'
            '#let data = json("data.json")\n'
            '= Polling compilation\n' + work + marker + '\n\n#chapter\n\n#hidden\n\n#data.asset\n')


def replace_preserving_mtime(path, content, atomic=False):
    previous = path.stat()
    target = path.with_suffix(".save.tmp") if atomic else path
    target.write_text(content)
    os.utime(target, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    if atomic:
        target.replace(path)
    assert path.stat().st_mtime_ns == previous.st_mtime_ns


def fixture(base):
    source = base / "document source with spaces"
    output = base / "output sibling with spaces"
    (source / "parts").mkdir(parents=True)
    (source / "vendor").mkdir()
    output.mkdir()
    (source / "main document.typ").write_text(document("INITIAL0"))
    (source / "parts/chapter.typ").write_text('#let chapter = [IMPORTEDONE]\n')
    (source / ".hidden-part.typ").write_text('#let hidden = [HIDDENONE]\n')
    (source / "data.json").write_text('{"asset":"ASSETONE"}\n')
    (source / "vendor/keep.txt").write_text("Keep this unrelated content\n")
    return source, output / "main document.pdf"


class Runner:
    def __init__(self, executable, typst, source, pdf, log):
        self.log = log
        self.handle = log.open("w")
        self.process = subprocess.Popen(
            [executable, str(source), "main document.typ", str(pdf)],
            env={**os.environ, "TYPST": typst}, stdout=self.handle,
            stderr=subprocess.STDOUT, start_new_session=True,
        )

    def text(self):
        return self.log.read_text()

    def starts(self):
        return self.text().count("[compile start]")

    def finishes(self):
        return self.text().count("[compile ok]")

    def close(self):
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGINT)
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait()
        self.handle.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poll-compile", required=True)
    parser.add_argument("--control-compile", help="Optional omission-control executable built with compare_contents(false)")
    parser.add_argument("--typst", default="typst")
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--initial-timeout", type=float, default=15)
    args = parser.parse_args()
    for name in ["poll_compile", "typst"] + (["control_compile"] if args.control_compile else []):
        found = shutil.which(getattr(args, name))
        if not found:
            parser.error("Executable not found: " + getattr(args, name))
        setattr(args, name, str(Path(found).resolve()))
    args.evidence = args.evidence.resolve()
    args.evidence.mkdir(parents=True, exist_ok=False)
    report = {"checks": {}, "platform": os.uname().sysname + " " + os.uname().machine}
    report["typst"] = subprocess.check_output([args.typst, "--version"], text=True).strip()
    with tempfile.TemporaryDirectory(prefix="polling compile check ") as temporary:
        root = Path(temporary)
        source, pdf = fixture(root)
        main_file = source / "main document.typ"
        vendor_original = (source / "vendor/keep.txt").read_bytes()
        runner = Runner(args.poll_compile, args.typst, source, pdf, args.evidence / "normal.txt")
        try:
            wait_for(lambda: "INITIAL0" in pdf_text(pdf), "initial actual PDF", args.initial_timeout)
            assert "PollWatcher" in runner.text() and "compare_contents=true" in runner.text()
            for marker in ["EDIT0001", "EDIT0002", "EDIT0003"]:
                old_size = main_file.stat().st_size
                replace_preserving_mtime(main_file, document(marker))
                assert main_file.stat().st_size == old_size
                wait_for(lambda: marker in pdf_text(pdf), "same-size preserved-mtime save " + marker)
            replace_preserving_mtime(main_file, document("ATOMIC00"), atomic=True)
            wait_for(lambda: "ATOMIC00" in pdf_text(pdf), "atomic replacement actual PDF")
            replace_preserving_mtime(source / "parts/chapter.typ", '#let chapter = [IMPORTEDTWO]\n')
            wait_for(lambda: "IMPORTEDTWO" in pdf_text(pdf), "import edit actual PDF")
            replace_preserving_mtime(source / ".hidden-part.typ", '#let hidden = [HIDDENTWO]\n')
            wait_for(lambda: "HIDDENTWO" in pdf_text(pdf), "hidden import actual PDF")
            replace_preserving_mtime(source / "data.json", '{"asset":"ASSETTWO"}\n')
            wait_for(lambda: "ASSETTWO" in pdf_text(pdf), "non-Typst data asset edit actual PDF")
            report["checks"]["repeated_same_size_preserved_mtime_atomic_import_hidden_asset"] = True
            # Real Typst computation makes the compiler busy, without a fake sleep command.
            previous_starts, previous_finishes = runner.starts(), runner.finishes()
            replace_preserving_mtime(main_file, document("BUSYOLD0", busy=True))
            wait_for(lambda: runner.starts() > previous_starts, "native busy compile starts")
            time.sleep(0.65)
            assert runner.finishes() == previous_finishes, "Increase workload: native compiler finished before busy edit"
            replace_preserving_mtime(main_file, document("BUSYNEW0", busy=True))
            wait_for(lambda: runner.finishes() > previous_finishes, "first native busy compile ends", 30)
            assert "BUSYOLD0" in pdf_text(pdf), "First PDF must reflect source read before the busy edit"
            shutil.copyfile(pdf, args.evidence / "busy-before.pdf")
            wait_for(lambda: "BUSYNEW0" in pdf_text(pdf), "queued follow-up PDF reflects latest source", 30)
            report["checks"]["busy_first_pdf"] = "BUSYOLD0"
            report["checks"]["busy_followup_pdf"] = "BUSYNEW0"
            previous_errors = runner.text().count("[compile failed]")
            replace_preserving_mtime(main_file, "#let broken = (\n")
            wait_for(lambda: runner.text().count("[compile failed]") > previous_errors, "real syntax error")
            assert "BUSYNEW0" in pdf_text(pdf), "Error must retain last successful output"
            replace_preserving_mtime(main_file, document("RECOVER0"))
            wait_for(lambda: "RECOVER0" in pdf_text(pdf), "error recovery actual PDF")
            replace_preserving_mtime(main_file, document("CONTINUE"))
            wait_for(lambda: "CONTINUE" in pdf_text(pdf), "continued edit after recovery")
            time.sleep(0.7)
            before = runner.starts()
            (pdf.parent / "generated.typ").write_text("Generated sibling output\n")
            (source / "vendor/keep.txt").write_bytes(vendor_original)
            os.utime(pdf, None)
            time.sleep(1.1)
            assert runner.starts() == before, "Output/vendor changes caused another compile"
            assert (source / "vendor/keep.txt").read_bytes() == vendor_original
            final = pdf_text(pdf)
            assert all(x in final for x in ["CONTINUE", "IMPORTEDTWO", "HIDDENTWO", "ASSETTWO"])
            shutil.copyfile(pdf, args.evidence / "final.pdf")
            report["checks"]["error_recovery_continued_edit_output_no_loop_preserved_content"] = True
        finally:
            runner.close()
        # The program must reject an output under the watched source root.
        rejected = subprocess.run([args.poll_compile, str(source), "main document.typ", str(source / "bad.pdf")],
                                  env={**os.environ, "TYPST": args.typst}, capture_output=True, text=True, timeout=3)
        assert rejected.returncode != 0 and not (source / "bad.pdf").exists()
        report["checks"]["output_inside_source_rejected"] = True
        # Registration must precede even the first (potentially slow) compile.
        initial_source, initial_pdf = fixture(root / "initial busy")
        initial_main = initial_source / "main document.typ"
        initial_main.write_text(document("FIRSTOLD", busy=True))
        initial = Runner(args.poll_compile, args.typst, initial_source, initial_pdf,
                         args.evidence / "initial-busy.txt")
        try:
            wait_for(lambda: initial.starts() == 1, "initial busy compiler starts")
            time.sleep(0.65)
            assert initial.finishes() == 0, "Increase workload: initial compiler finished before edit"
            replace_preserving_mtime(initial_main, document("FIRSTNEW", busy=True))
            wait_for(lambda: initial.finishes() >= 1, "first initial-busy PDF", 30)
            assert "FIRSTOLD" in pdf_text(initial_pdf)
            wait_for(lambda: "FIRSTNEW" in pdf_text(initial_pdf), "edit during initial compile reaches PDF", 30)
            report["checks"]["edit_during_initial_compile"] = "FIRSTOLD then FIRSTNEW"
        finally:
            initial.close()
        if args.control_compile:
            control_root = root / "control"
            control_root.mkdir()
            control_source, control_pdf = fixture(control_root)
            control = Runner(args.control_compile, args.typst, control_source, control_pdf, args.evidence / "control.txt")
            try:
                wait_for(lambda: "INITIAL0" in pdf_text(control_pdf), "omission-control initial PDF")
                time.sleep(0.7)
                path = control_source / "main document.typ"
                before = path.stat()
                replace_preserving_mtime(path, document("EDIT0001"))
                assert path.stat().st_size == before.st_size
                time.sleep(1.1)
                assert "INITIAL0" in pdf_text(control_pdf) and "EDIT0001" not in pdf_text(control_pdf)
                report["checks"]["compare_contents_false_omission_control"] = "Actual PDF remains INITIAL0"
            finally:
                control.close()
    (args.evidence / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
