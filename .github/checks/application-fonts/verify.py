"""Baseline-only native font observation. Requires the verified Linux SDK and tools."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time


SDK_SIZE = 46_307_026
SDK_SHA256 = "c138fbc4bc2c21de5aa5ce63d2ced40661373ed3d857f4605a315981f23d5641"
MIN_FREE = 1024 ** 3
MAX_LOG = 4 * 1024 ** 2
WIDGETS = ["window", "label", "button", "lineEdit", "comboBox", "checkBox"]
CONTENTS = {
    "label": "Sample label", "button": "Sample action", "lineEdit": "Sample input",
    "comboBox": ["First choice", "Second choice"], "checkBox": "Sample check",
}


class SetupFailure(Exception):
    pass


class Interrupted(SetupFailure):
    def __init__(self, signum):
        super().__init__(f"interrupted by signal {signum}")
        self.status = 128 + signum


def interrupted(signum, _frame):
    raise Interrupted(signum)


def require(condition, message):
    if not condition:
        raise SetupFailure(message)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def free_space(path):
    free = shutil.disk_usage(path).free
    require(free >= MIN_FREE, f"free-space guard failed: {free} bytes")
    return free


def stop_group(process):
    # Every process here starts a new session. Never target an inherited group.
    for sig, wait_seconds in [(signal.SIGTERM, 3), (signal.SIGKILL, 3)]:
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            break
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            process.poll()
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            continue
        break
    process.wait(timeout=3)


def run(command, *, env, work, label, timeout=90):
    stdout = work / f"{label}.stdout"
    stderr = work / f"{label}.stderr"
    print(json.dumps({"command": command, "label": label}), flush=True)
    stopped = None
    with stdout.open("wb") as out, stderr.open("wb") as err:
        process = subprocess.Popen(command, cwd=work, env=env, stdout=out, stderr=err,
                                   start_new_session=True)
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                require(time.monotonic() < deadline, f"{label}: timeout")
                free_space(work)
                require(all(path.stat().st_size <= MAX_LOG for path in
                            [stdout, stderr, work / "xvfb.log"] if path.exists()),
                        f"{label}: output limit")
                time.sleep(0.1)
            status = process.returncode
        except SetupFailure as error:
            stopped = error
            status = process.poll()
        finally:
            stop_group(process)
    require(stdout.stat().st_size <= MAX_LOG and stderr.stat().st_size <= MAX_LOG,
            f"{label}: output limit")
    output = stdout.read_text(errors="replace")
    errors = stderr.read_text(errors="replace")
    print(json.dumps({"label": label, "exit": status, "stdout": output, "stderr": errors}), flush=True)
    if stopped:
        raise stopped
    require(status == 0, f"{label}: native/tool exit {status}")
    return output


def extract_sdk(archive, destination):
    require(archive.is_file() and not archive.is_symlink(), "SDK must be a regular file")
    require(archive.stat().st_size == SDK_SIZE, "SDK size mismatch")
    require(digest(archive) == SDK_SHA256, "SDK digest mismatch")
    # Inspect all members before writing any of them. No links/devices/absolute paths.
    with tarfile.open(archive, "r:bz2") as bundle:
        members = bundle.getmembers()
        require(0 < len(members) <= 10_000, "SDK member-count bound")
        names = set()
        total = 0
        files = set()
        for member in members:
            path = PurePosixPath(member.name)
            require(not path.is_absolute() and path.parts and ".." not in path.parts
                    and "\\" not in member.name, "unsafe SDK member path")
            name = str(path)
            require(name not in names, "duplicate SDK member")
            names.add(name)
            require(member.isdir() or member.isfile(), "SDK contains a link or special member")
            require(0 <= member.size <= 128 * 1024 ** 2, "SDK member-size bound")
            total += member.size
            require(total <= 256 * 1024 ** 2, "SDK uncompressed-size bound")
            if member.isfile():
                files.add(name)
        for name in names:
            require(not any(str(parent) in files for parent in PurePosixPath(name).parents),
                    "SDK file/directory collision")
        require(len(members) == 2106 and total == 188_245_920, "unexpected SDK metadata")
        destination.mkdir()
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, 1024 ** 2)
                target.chmod(member.mode & 0o777)
    print(json.dumps({"sdkSha256": SDK_SHA256, "members": len(members),
                      "uncompressedBytes": total}), flush=True)


def inspect_report(output, sdk, matched_family):
    # Literal external requirements: omitted callback/records cannot satisfy this gate.
    lines = [line for line in output.splitlines() if line.startswith("FONT_REPORT ")]
    require(len(lines) == 1, "expected exactly one native final report")
    report = json.loads(lines[0][len("FONT_REPORT "):])
    require(report.get("version") == "2.1.0", "wrong native CopperSpice version")
    require(report.get("platform", "").lower() == "xcb", "XCB platform did not run")
    require(report.get("callbackCount") == 1 and report.get("eventLoopExit") == 0,
            "native event loop/callback did not complete once")
    require(report.get("styleSheet") == "", "baseline unexpectedly has a stylesheet")
    require(isinstance(report.get("availableStyles"), list) and report["availableStyles"],
            "no actual native styles")
    require(isinstance(report.get("style"), str) and report["style"], "missing current style")
    require(report.get("contents") == CONTENTS, "native widget content changed or is absent")
    records = report.get("widgets")
    require(isinstance(records, list) and len(records) == len(WIDGETS), "missing widget records")
    require([record.get("name") for record in records] == WIDGETS, "wrong/duplicate widget records")
    for record in records:
        require(record.get("visible") is True and record.get("polished") is True,
                f"{record['name']}: not shown/polished")
        require(isinstance(record.get("requestedFamily"), str) and record["requestedFamily"]
                and isinstance(record.get("matchedFamily"), str) and record["matchedFamily"],
                f"{record['name']}: missing actual font family")
        for field in ["requestedPointSize", "matchedPointSize"]:
            require(isinstance(record.get(field), (int, float)) and math.isfinite(record[field]),
                    f"{record['name']}: missing finite {field}")
        require(record["matchedPointSize"] > 0, f"{record['name']}: no resolved point size")
    loaded = report.get("loadedLibraries")
    require(isinstance(loaded, list) and len(loaded) == len(set(loaded)), "bad loaded-library evidence")
    for name in ["libCsCore2.1.so", "libCsGui2.1.so", "CsGuiXcb2.1.so"]:
        paths = [Path(path) for path in loaded if Path(path).name == name]
        require(len(paths) == 1 and paths[0].resolve() == (sdk / "lib" / name).resolve(),
                f"wrong/missing loaded {name}")
    require(not any(Path(path).name.startswith("libQt") for path in loaded), "mixed Qt libraries")
    for path in loaded:
        if "CsCore" in Path(path).name or "CsGui" in Path(path).name:
            require(Path(path).resolve().is_relative_to(sdk), "foreign CopperSpice library")
    misses = [{"name": record["name"], "requestedPointSize": record["requestedPointSize"],
               "matchedFamily": record["matchedFamily"], "expectedFamily": matched_family}
              for record in records
              if not math.isclose(record["requestedPointSize"], 12, abs_tol=0.01)
              or record["matchedFamily"].casefold() != matched_family.casefold()]
    print(json.dumps({"baseline": report, "independentSansFamily": matched_family,
                      "fontTargetDifferences": misses}), flush=True)
    return misses


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk-archive", type=Path, required=True)
    parser.add_argument("--work-parent", type=Path, required=True)
    args = parser.parse_args()
    require(sys.platform == "linux" and platform.machine() == "x86_64", "Linux x86_64 required")
    parent = args.work_parent.resolve(strict=True)
    require(parent.is_dir() and parent != Path("/"), "invalid owned work parent")
    print(json.dumps({"freeBytesBefore": free_space(parent), "machine": platform.machine()}), flush=True)
    with tempfile.TemporaryDirectory(prefix="font-baseline-", dir=parent) as temporary:
        work = Path(temporary)
        for directory in ["home", "tmp", "config", "cache", "runtime"]:
            (work / directory).mkdir(mode=0o700)
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(work / "home"),
               "TMPDIR": str(work / "tmp"), "XDG_CONFIG_HOME": str(work / "config"),
               "XDG_CACHE_HOME": str(work / "cache"), "XDG_RUNTIME_DIR": str(work / "runtime"),
               "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
        for command in ["g++", "cmake", "Xvfb", "xvfb-run", "xauth", "fc-match", "fc-list", "ldd"]:
            require(shutil.which(command, path=env["PATH"]), f"missing prerequisite: {command}")
        for name in ["libz.so", "libOpenGL.so", "libGLX.so"]:
            require((Path("/usr/lib/x86_64-linux-gnu") / name).is_file(), f"missing native link dependency: {name}")
        for label, command in [("compiler", ["g++", "--version"]), ("cmake", ["cmake", "--version"])]:
            run(command, env=env, work=work, label=label)
        fonts = run(["fc-list", "--format", "%{family[0]}\n"], env=env, work=work, label="fonts")
        require(fonts.strip(), "no installed fonts")
        matched_family = run(["fc-match", "--format", "%{family[0]}\n", "Sans:size=12"],
                             env=env, work=work, label="sans-match").strip()
        require(matched_family and "\n" not in matched_family, "ambiguous Sans font match")
        sdk = work / "sdk"
        extract_sdk(args.sdk_archive.resolve(strict=True), sdk)
        env["LD_LIBRARY_PATH"] = str(sdk / "lib")
        for index, name in enumerate(["libCsCore2.1.so", "libCsGui2.1.so", "CsGuiXcb2.1.so"]):
            output = run(["ldd", str(sdk / "lib" / name)], env=env, work=work, label=f"sdk-deps-{index}")
            require("not found" not in output, f"unavailable native dependency for {name}")
        source = Path(__file__).resolve().parent / "consumer"
        build = work / "build"
        run(["cmake", "-S", str(source), "-B", str(build), "-DCMAKE_BUILD_TYPE=Release",
             f"-DCopperSpice_DIR={sdk / 'lib/cmake/CopperSpice'}"], env=env, work=work,
            label="configure", timeout=120)
        run(["cmake", "--build", str(build), "--parallel", "2"], env=env, work=work,
            label="build", timeout=180)
        binary = build / "font-inspector"
        require(binary.is_file(), "native consumer was not produced")
        output = run(["ldd", str(binary)], env=env, work=work, label="consumer-deps")
        require("not found" not in output, "consumer has unavailable native dependencies")
        print(json.dumps({"consumerSha256": digest(binary), "freeBytesBeforeNative": free_space(work)}), flush=True)
        try:
            output = run(["xvfb-run", "-a", "-e", str(work / "xvfb.log"), "-s",
                          "-screen 0 1280x720x24 -nolisten tcp", str(binary),
                          "-platformpluginpath", str(sdk / "lib"), "-platform", "xcb"],
                         env=env, work=work, label="baseline-native", timeout=60)
        finally:
            log = work / "xvfb.log"
            if log.is_file():
                print(json.dumps({"xvfbLog": log.read_bytes()[:MAX_LOG].decode(errors="replace")}), flush=True)
        misses = inspect_report(output, sdk, matched_family)
        print(json.dumps({"freeBytesAfterNative": free_space(work),
                          "result": "BEHAVIOR_RED_FONT_TARGET" if misses else "BASELINE_ALREADY_MATCHES_TARGET"}), flush=True)
        return 1 if misses else 0


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        sys.exit(main())
    except (SetupFailure, OSError, ValueError, tarfile.TarError, subprocess.SubprocessError) as error:
        print(json.dumps({"result": "SETUP_OR_UNEXPECTED_FAILURE", "message": str(error)}), flush=True)
        sys.exit(getattr(error, "status", 2))
