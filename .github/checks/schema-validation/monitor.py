"""Run one command with a 1 GiB floor; signal only its new process group."""

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


FLOOR_BYTES = 1024**3


def report(event, directory, **fields):
    free = shutil.disk_usage(directory)[2]
    print(json.dumps({"event": event, "free_bytes": free, **fields}), flush=True)
    return free


def stop_owned_group(process):
    """The group ID is the PID returned by our start_new_session=True call."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        process.poll()
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def run_monitored(command, directory):
    if report("before_command", directory, command=command) < FLOOR_BYTES:
        report("disk_floor_before_start", directory, floor_bytes=FLOOR_BYTES)
        return 75
    process = subprocess.Popen(command, cwd=directory, start_new_session=True)
    print(json.dumps({"event": "started", "process_group": process.pid}), flush=True)
    stopped_for_disk = False

    def interrupted(signum, _frame):
        raise InterruptedError(signum)

    previous = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        while process.poll() is None:
            if shutil.disk_usage(directory)[2] < FLOOR_BYTES:
                stopped_for_disk = True
                report("disk_floor_stop", directory, floor_bytes=FLOOR_BYTES)
                stop_owned_group(process)
                break
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
        status = process.wait()
        status = 128 - status if status < 0 else status
        if stopped_for_disk and status == 0:
            status = 75
    except InterruptedError as error:
        stop_owned_group(process)
        status = 128 + error.args[0]
    except BaseException:
        stop_owned_group(process)
        raise
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    report("after_command", directory, exit_code=status, stopped_for_disk=stopped_for_disk)
    return status


if __name__ == "__main__":
    if len(sys.argv) < 4 or sys.argv[2] != "--":
        raise SystemExit("usage: monitor.py DIRECTORY -- COMMAND [ARG ...]")
    raise SystemExit(run_monitored(sys.argv[3:], Path(sys.argv[1]).resolve(strict=True)))
