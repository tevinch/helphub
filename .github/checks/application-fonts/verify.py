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
from xml.sax.saxutils import escape


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


def run(command, *, env, work, label, timeout=90, cwd=None):
    cwd = work if cwd is None else cwd
    require(cwd.resolve(strict=True).is_relative_to(work), "command cwd escaped owned tree")
    stdout = work / f"{label}.stdout"
    stderr = work / f"{label}.stderr"
    print(json.dumps({"command": command, "label": label, "cwd": str(cwd)}), flush=True)
    stopped = None
    with stdout.open("wb") as out, stderr.open("wb") as err:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=out, stderr=err,
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


def inspect_report(output, sdk, stylesheet=None):
    # Literal external requirements: omitted callback/records cannot satisfy this gate.
    lines = [line for line in output.splitlines() if line.startswith("FONT_REPORT ")]
    require(len(lines) == 1, "expected exactly one native final report")
    report = json.loads(lines[0][len("FONT_REPORT "):])
    require(report.get("version") == "2.1.0", "wrong native CopperSpice version")
    require(report.get("platform", "").lower() == "xcb", "XCB platform did not run")
    require(report.get("callbackCount") == 1 and report.get("eventLoopExit") == 0,
            "native event loop/callback did not complete once")
    # Stable QApplication preserves this argument as a file reference. Font values
    # below, rather than this metadata, prove that the file's rules took effect.
    expected_sheet = "" if stylesheet is None else "file:///" + str(stylesheet)
    require(report.get("styleSheet") == expected_sheet, "native stylesheet argument differs")
    require(isinstance(report.get("availableStyles"), list) and report["availableStyles"],
            "no actual native styles")
    require(isinstance(report.get("style"), str), "missing current style metadata")
    if stylesheet is None:
        require(report["style"], "missing unwrapped current style")
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
    return report


def font_misses(report, matched_family):
    return [record["name"] for record in report["widgets"]
            if record["requestedFamily"].casefold() != "sans"
            or not math.isclose(record["requestedPointSize"], 12, abs_tol=0.01)
            or record["requestedPixelSize"] != -1
            or record["matchedFamily"].casefold() != matched_family.casefold()
            # Matched sizes are quantized to whole pixels; the requested point
            # size and unset pixel-size property distinguish 12pt from 12px.
            or abs(record["matchedPointSize"] - 12) > 0.75]


def require_target(report, family, label):
    misses = font_misses(report, family)
    require(not misses, f"{label}: font target differs on {misses}")
    print(json.dumps({"case": label, "result": "SIX_WIDGET_FONT_TARGET_PASS",
                      "independentFamily": family}), flush=True)


def require_rejection(report, family, label):
    misses = font_misses(report, family)
    require(misses == WIDGETS, f"{label}: omission/control did not reject all six widgets")
    print(json.dumps({"case": label, "result": "EXPECTED_FONT_TARGET_REJECTION",
                      "rejectedWidgets": misses}), flush=True)


def green_cases(binary, sdk, env, work, default_family):
    binary_sha = digest(binary)
    sheet_source = Path(__file__).resolve().parent / "sans12.qss"
    require(sheet_source.is_file(), "stylesheet is absent")
    expected_qss = '* {\n    font-family: "Sans";\n    font-size: 12pt;\n}\n'
    require(sheet_source.read_text() == expected_qss, "symbolic Sans/12pt source changed")
    sheet_sha = digest(sheet_source)
    spaced = work / "launch with spaces"
    spaced.mkdir()
    sheet = spaced / "font options.qss"
    shutil.copyfile(sheet_source, sheet)
    require(digest(sheet) == sheet_sha, "stylesheet copy differs")
    cases = []

    def native(label, *, options=(), stylesheet=None, case_env=None, cwd=work):
        require(digest(binary) == binary_sha, "consumer binary changed between cases")
        active_env = env if case_env is None else case_env
        try:
            output = run(["xvfb-run", "-a", "-e", str(work / "xvfb.log"), "-s",
                          "-screen 0 1280x720x24 -nolisten tcp", str(binary),
                          "-platformpluginpath", str(sdk / "lib"), "-platform", "xcb", *options],
                         env=active_env, work=work, cwd=cwd, label=label, timeout=60)
        finally:
            log = work / "xvfb.log"
            if log.is_file():
                print(json.dumps({"case": label, "xvfbLog": log.read_bytes()[:MAX_LOG].decode(errors="replace")}), flush=True)
        report = inspect_report(output, sdk, stylesheet)
        cases.append(label)
        print(json.dumps({"case": label, "consumerSha256": digest(binary),
                          "report": report}), flush=True)
        return report

    baseline = native("omitted-stylesheet", cwd=spaced)
    require_rejection(baseline, default_family, "omitted-stylesheet")
    separate = native("stylesheet-separate-spaced", options=["-stylesheet", str(sheet)],
                      stylesheet=sheet, cwd=spaced)
    require_target(separate, default_family, "stylesheet-separate-spaced")
    equals = native("stylesheet-equals-spaced", options=["-stylesheet=" + str(sheet)],
                    stylesheet=sheet, cwd=spaced)
    require_target(equals, default_family, "stylesheet-equals-spaced")

    # The same formerly successful path becomes missing: an echoed file argument
    # alone cannot satisfy acceptance. Restore identical bytes for later cases.
    sheet.unlink()
    removed = native("removed-stylesheet", options=["-stylesheet", str(sheet)],
                     stylesheet=sheet, cwd=spaced)
    require_rejection(removed, default_family, "removed-stylesheet")
    shutil.copyfile(sheet_source, sheet)
    absent = spaced / "does not exist.qss"
    require(not absent.exists(), "missing-file control unexpectedly exists")
    missing = native("missing-stylesheet", options=["-stylesheet=" + str(absent)],
                     stylesheet=absent, cwd=spaced)
    require_rejection(missing, default_family, "missing-stylesheet")
    pixels = spaced / "twelve pixels.qss"
    pixels.write_text(expected_qss.replace("12pt", "12px"))
    pixel_report = native("twelve-pixel-control", options=["-stylesheet", str(pixels)],
                          stylesheet=pixels, cwd=spaced)
    require(all(record["requestedPixelSize"] == 12 for record in pixel_report["widgets"]),
            "pixel control did not apply actual 12px rules")
    require_rejection(pixel_report, default_family, "twelve-pixel-control")

    # Task-owned diagnostics include normal system rules, then alter only the
    # process-local generic Sans aliases. No system/user configuration is edited.
    require(Path("/etc/fonts/fonts.conf").is_file(), "system Fontconfig include is unavailable")
    families = ["DejaVu Sans", "Liberation Sans"]
    alias_envs, independently_matched = [], []
    for index, family in enumerate(families):
        alias_file = work / f"font-alias-{index}.conf"
        edits = "".join(
            '<match target="pattern"><test name="family" qual="any" compare="eq">'
            f'<string>{escape(alias)}</string></test><edit name="family" mode="assign" binding="strong">'
            f'<string>{escape(family)}</string></edit></match>'
            for alias in ["Sans", "sans-serif", "Sans Serif"])
        alias_file.write_text('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
                              '<fontconfig><include>/etc/fonts/fonts.conf</include>' + edits + '</fontconfig>\n')
        alias_env = dict(env, FONTCONFIG_FILE=str(alias_file))
        matched = run(["fc-match", "--format", "%{family[0]}\n", "Sans:size=12"],
                      env=alias_env, work=work, label=f"independent-alias-{index}").strip()
        require(matched == family, f"Fontconfig alias {index} did not select the installed requested face")
        independently_matched.append(matched)
        alias_envs.append(alias_env)
        print(json.dumps({"alias": index, "fontconfigFile": str(alias_file),
                          "configurationSha256": digest(alias_file), "independentFamily": matched}), flush=True)
    require(independently_matched[0] != independently_matched[1], "A/B alias expectations did not change")
    require(default_family != independently_matched[1], "omitted-Fontconfig control lacks a distinct expectation")
    for index in [0, 1, 0]:
        label = f"native-alias-{index}-visit-{len(cases)}"
        report = native(label, options=["-stylesheet", str(sheet)], stylesheet=sheet,
                        case_env=alias_envs[index], cwd=spaced)
        require_target(report, independently_matched[index], label)
    omitted_alias = native("omitted-fontconfig", options=["-stylesheet", str(sheet)],
                           stylesheet=sheet, case_env=env, cwd=spaced)
    require_target(omitted_alias, default_family, "omitted-fontconfig-still-styled")
    require_rejection(omitted_alias, independently_matched[1], "omitted-fontconfig")

    # Validate an actually available native style before the stylesheet wrapper
    # is installed; its wrapper objectName need not retain the base style name.
    options = [name for name in baseline["availableStyles"]
               if name.casefold() != baseline["style"].casefold()]
    require(options, "no distinct available native style for the optional style check")
    style = options[0]
    style_only = native("native-style-only", options=["-style", style], cwd=spaced)
    require(style_only["style"].casefold() == style.casefold(), "native style selector did not run")
    styled = native("native-style-with-fonts", options=["-style", style, "-stylesheet", str(sheet)],
                    stylesheet=sheet, cwd=spaced)
    require_target(styled, default_family, "native-style-with-fonts")
    require(digest(binary) == binary_sha and digest(sheet) == sheet_sha,
            "binary/stylesheet changed during acceptance")
    print(json.dumps({"result": "NATIVE_APPLICATION_FONTS_VERIFIED", "cases": cases,
                      "consumerSha256": binary_sha, "stylesheetSha256": sheet_sha,
                      "aliasFamilies": independently_matched, "nativeStyle": style,
                      "scope": "six ordinary Linux/XCB widgets; no original application/global/Gentoo claim"}), flush=True)


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
        green_cases(binary, sdk, env, work, matched_family)
        print(json.dumps({"freeBytesAfterNative": free_space(work)}), flush=True)
        return 0


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        sys.exit(main())
    except (SetupFailure, OSError, ValueError, tarfile.TarError, subprocess.SubprocessError) as error:
        print(json.dumps({"result": "SETUP_OR_UNEXPECTED_FAILURE", "message": str(error)}), flush=True)
        sys.exit(getattr(error, "status", 2))
