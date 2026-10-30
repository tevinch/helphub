#!/usr/bin/env python3
"""Exercise the native Gum + GNU timeout recipe using owned temporary jobs."""
import argparse
import errno
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time

CHILD = """import os, pathlib, signal, sys, time
root = pathlib.Path(sys.argv[1])
if sys.argv[2] == "ignore":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
root.joinpath("child-started").write_text(str(os.getpid()))
time.sleep(1.4)
root.joinpath("child-late").write_text("completed")
"""
WORKER = """import os, pathlib, signal, subprocess, sys, time
root = pathlib.Path(sys.argv[1])
if sys.argv[2] == "ignore":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
child = subprocess.Popen([sys.executable, "-c", sys.argv[3], str(root), sys.argv[2]])
while not root.joinpath("child-started").exists():
    time.sleep(0.005)
root.joinpath("started").write_text(str(os.getpid()))
time.sleep(1.4)
child.wait()
root.joinpath("late").write_text("completed")
print("JOB-COMPLETED", flush=True)
"""


def run(command, terminal):
    """Wait for the actual Gum process; capture output without holding up its exit."""
    started = time.monotonic()
    env = dict(os.environ, TERM="xterm-256color", NO_COLOR="1", GUM_SPIN_TIMEOUT="50ms")
    master = slave = None
    if terminal:
        master, slave = pty.openpty()
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                   stdout=slave, stderr=slave, env=env,
                                   start_new_session=True)
        os.close(slave)
        output = bytearray()
        try:
            while process.poll() is None:
                if time.monotonic() - started > 5:
                    raise AssertionError("Gum did not return within five seconds")
                if select.select([master], [], [], 0.03)[0]:
                    try:
                        output.extend(os.read(master, 65536))
                    except OSError as error:
                        if error.errno != errno.EIO:
                            raise
            elapsed = time.monotonic() - started
            while select.select([master], [], [], 0.05)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                output.extend(chunk)
            return process.returncode, bytes(output), b"", elapsed
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            os.close(master)
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                   stdout=out, stderr=err, env=env,
                                   start_new_session=True)
        try:
            process.wait(timeout=5)
            elapsed = time.monotonic() - started
            out.seek(0)
            err.seek(0)
            return process.returncode, out.read(), err.read(), elapsed
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def deadline(gum, timeout, terminal, ignore=False, negative=False):
    with tempfile.TemporaryDirectory(prefix="command-deadline-") as directory:
        root = Path(directory)
        job = [sys.executable, "-c", WORKER, str(root), "ignore" if ignore else "term", CHILD]
        if negative:
            command = [gum, "spin", "--timeout=250ms", "--", *job]
        else:
            command = [gum, "spin", "--timeout=0s", "--", timeout, "--kill-after=0.2s", "0.25s", *job]
        pid = None
        try:
            status, out, err, elapsed = run(command, terminal)
            assert root.joinpath("started").is_file(), "the wrapped job never started"
            pid = int(root.joinpath("started").read_text())
            # Wait beyond the job's normal completion to catch an orphan continuing work.
            time.sleep(max(0, 1.65 - elapsed))
            assert not root.joinpath("late").exists(), "late marker exists: the wrapped job continued"
            assert root.joinpath("child-started").is_file(), "the job's child never started"
            child_pid = int(root.joinpath("child-started").read_text())
            assert not root.joinpath("child-late").exists(), "late child marker exists"
            assert not alive(pid), "the wrapped job is still alive"
            assert not alive(child_pid), "the job's child is still alive"
            expected = 1 if ignore else 124
            assert status == expected, f"expected status {expected}, received {status}: {out!r} {err!r}"
            assert elapsed < 2, f"deadline returned too late: {elapsed:.3f}s"
            return {"mode": "pty" if terminal else "redirected", "kind": "kill" if ignore else "term",
                    "status": status, "seconds": round(elapsed, 3), "job_started": True,
                    "late_marker": False, "job_alive": False}
        finally:
            if pid is None and root.joinpath("started").exists():
                pid = int(root.joinpath("started").read_text())
            owned = [pid]
            if root.joinpath("child-started").exists():
                owned.append(int(root.joinpath("child-started").read_text()))
            for owned_pid in owned:
                if owned_pid is not None and alive(owned_pid):
                    # Confirm the unique fixture path before signaling an owned job.
                    try:
                        command_line = subprocess.check_output(
                            ["ps", "-p", str(owned_pid), "-o", "command="], text=True)
                    except subprocess.CalledProcessError:
                        command_line = ""
                    if str(root) in command_line:
                        os.kill(owned_pid, signal.SIGKILL)


def completion_case(gum, timeout, terminal, status):
    code = 'import sys; print(sys.argv[1], flush=True); print("JOB-STDERR", file=sys.stderr, flush=True); sys.exit(int(sys.argv[2]))'
    literal = 'a quoted argument; $(no-substitution)'
    command = [gum, "spin", "--timeout=0s", "--", timeout, "2s",
               sys.executable, "-c", code, literal, str(status)]
    result, out, err, elapsed = run(command, terminal)
    assert result == status, f"exit status changed: {result} != {status}"
    if terminal:
        # Gum's default terminal presentation intentionally hides job output.
        assert literal.encode() not in out and b"JOB-STDERR" not in out, repr(out)
    else:
        assert out == (literal + "\n").encode(), repr(out)
        assert b"JOB-STDERR\n" in err, repr(err)
    return {"mode": "pty" if terminal else "redirected", "kind": "completion",
            "status": result, "terminal_output_hidden": terminal,
            "redirected_output_checked": not terminal}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gum", default=shutil.which("gum"))
    parser.add_argument("--timeout", default=shutil.which("timeout") or shutil.which("gtimeout"))
    parser.add_argument("--negative-control", action="store_true",
                        help="intentionally test Gum's UI timeout against the job deadline contract")
    args = parser.parse_args()
    if not args.gum or not args.timeout:
        parser.error("install Gum and GNU Coreutils timeout, or pass their paths")
    versions = {"gum": subprocess.check_output([args.gum, "--version"], text=True).strip(),
                "timeout": subprocess.check_output([args.timeout, "--version"], text=True).splitlines()[0]}
    records = []
    try:
        if args.negative_control:
            records.append(deadline(args.gum, args.timeout, False, negative=True))
        else:
            for terminal in (False, True):
                for _ in range(2):
                    records.append(deadline(args.gum, args.timeout, terminal))
                records.append(deadline(args.gum, args.timeout, terminal, ignore=True))
                for status in (0, 42):
                    records.append(completion_case(args.gum, args.timeout, terminal, status))
    except AssertionError as error:
        print(json.dumps({"versions": versions, "passed": records, "failure": str(error)}, indent=2))
        return 1
    print(json.dumps({"versions": versions, "passed": records, "count": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
