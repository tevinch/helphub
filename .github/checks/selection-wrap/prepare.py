"""Prepare one disposable Linux desktop; this does not test the wrapping macro."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

ASSET_NAME = "texstudio-4.9.9-x86_64.AppImage"
ASSET_SIZE = 124064056
ASSET_SHA256 = "32ff7e43eebe9b2befb28c24f60fb8705cf01e47cba9400a6494f7c0032e86f8"
ASSET_URL = "https://github.com/texstudio-org/texstudio/releases/download/4.9.9/" + ASSET_NAME
PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
GIB = 1024 ** 3
EVIDENCE_TEMP_ALLOWANCE = 128 * 1024 ** 2
SOURCES = (
    "deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] "
    "https://archive.ubuntu.com/ubuntu noble main universe\n"
    "deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] "
    "https://archive.ubuntu.com/ubuntu noble-updates main universe\n"
    "deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] "
    "https://security.ubuntu.com/ubuntu noble-security main universe\n"
)
RUNTIME_PACKAGES = {
    "libxcb-icccm.so.4": "libxcb-icccm4", "libxcb-image.so.0": "libxcb-image0",
    "libxcb-keysyms.so.1": "libxcb-keysyms1", "libxcb-render-util.so.0": "libxcb-render-util0",
    "libxcb-xinerama.so.0": "libxcb-xinerama0", "libxcb-xkb.so.1": "libxcb-xkb1",
    "libxkbcommon-x11.so.0": "libxkbcommon-x11-0", "libX11-xcb.so.1": "libx11-xcb1",
    "libGL.so.1": "libgl1", "libOpenGL.so.0": "libopengl0", "libGLX.so.0": "libglx0",
    "libfontconfig.so.1": "libfontconfig1", "libfreetype.so.6": "libfreetype6",
    "libdbus-1.so.3": "libdbus-1-3", "libSM.so.6": "libsm6", "libICE.so.6": "libice6",
}


def run(argv, env, timeout=30, check=True):
    result = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=timeout)
    if len(result.stdout) + len(result.stderr) > 8 * 1024 ** 2:
        raise RuntimeError("Command output exceeds the observation budget")
    if check and result.returncode:
        raise RuntimeError(f"{argv[0]} exited {result.returncode}: {result.stderr[-3000:]} {result.stdout[-3000:]}")
    return result.stdout


def listed_bytes(listing):
    total, entries = 0, {}
    for line in listing.splitlines():
        if not line.strip() or re.fullmatch(r"Parallel unsquashfs: Using \d+ processors", line):
            continue
        fields = line.split(maxsplit=5)
        if (len(fields) != 6
                or not re.fullmatch(r"[dl-][r-][w-][xsS-][r-][w-][xsS-][r-][w-][xtT-]", fields[0])
                or not re.fullmatch(r"\d+/\d+", fields[1])
                or not fields[2].isdigit()
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fields[3])
                or not re.fullmatch(r"\d{2}:\d{2}", fields[4])):
            raise RuntimeError("Unexpected filesystem listing")
        name, arrow, target = fields[5].partition(" -> ")
        path = PurePosixPath(name)
        if (path.is_absolute() or path.as_posix() != name or ".." in path.parts
                or not path.parts or path.parts[0] != "squashfs-root"):
            raise RuntimeError("Unexpected archive entry path")
        kind, relative = fields[0][0], path.parts[1:]
        if ((kind == "l" and (not arrow or not target or PurePosixPath(target).is_absolute()))
                or (kind != "l" and arrow) or relative in entries):
            raise RuntimeError("Unexpected or duplicate archive link/entry")
        entries[relative] = {"kind": kind, "target": target}
        if len(entries) > 50000:
            raise RuntimeError("Too many application archive entries")
        total += max(4096, math.ceil(int(fields[2]) / 4096) * 4096)
    if entries.get((), {}).get("kind") != "d":
        raise RuntimeError("No independently listed application root directory")

    def resolve(parts):
        pending, resolved, followed = list(parts), [], set()
        while pending:
            component = pending.pop(0)
            if component in ("", "."):
                continue
            if component == "..":
                if not resolved:
                    raise RuntimeError("Archive link escapes its logical root")
                resolved.pop()
                continue
            resolved.append(component)
            key = tuple(resolved)
            if key not in entries:
                raise RuntimeError("Archive link or path has an unlisted destination")
            entry = entries[key]
            if entry["kind"] == "l":
                if key in followed or len(followed) >= 128:
                    raise RuntimeError("Archive link chain is cyclic or too long")
                followed.add(key)
                resolved.pop()
                pending = list(PurePosixPath(entry["target"]).parts) + pending
            elif pending and entry["kind"] != "d":
                raise RuntimeError("Archive path traverses a non-directory")
        return tuple(resolved)

    for path, entry in entries.items():
        if path and entries[resolve(path[:-1])]["kind"] != "d":
            raise RuntimeError("Archive entry has no closed directory parent")
        resolve(path)
    if total > 1536 * 1024 ** 2:
        raise RuntimeError("Uncompressed application exceeds the owned budget")
    return total, len(entries)


def contained_regular_file(path, root):
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve(strict=True)) or not resolved.is_file():
        raise RuntimeError("Official application file resolves outside its owned root")
    return resolved


def check_free_budget(free, download=0, installed=0):
    if any(not isinstance(value, int) or value < 0 for value in (free, download, installed)):
        raise RuntimeError("Unexpected disk budget input")
    required = 2 * GIB + EVIDENCE_TEMP_ALLOWANCE + download + installed
    if free < required:
        raise RuntimeError("The planned operation would cross the2GiB free-space reserve")
    return required


def disk_checkpoint(report, stage, path, download=0, installed=0):
    free = shutil.disk_usage(path).free
    observation = {"stage": stage, "freeBytes": free, "plannedDownloadBytes": download,
                   "plannedInstalledBytes": installed, "floorBytes": 2 * GIB,
                   "temporaryAndEvidenceBytes": EVIDENCE_TEMP_ALLOWANCE,
                   "requiredFreeBytes": 2 * GIB + EVIDENCE_TEMP_ALLOWANCE + download + installed}
    report.setdefault("diskCheckpoints", []).append(observation)
    check_free_budget(free, download, installed)


def allocated_tree_bytes(root):
    pending, seen, total = [root], set(), 0
    while pending:
        path = pending.pop()
        info = path.lstat()
        identity = (info.st_dev, info.st_ino)
        if identity in seen:
            continue
        seen.add(identity)
        total += info.st_blocks * 512
        if stat.S_ISDIR(info.st_mode):
            pending.extend(path.iterdir())
    return total


def terminate_group(child, report, term_seconds=3, kill_seconds=3):
    group = child.pid
    if group <= 1 or group == os.getpgrp():
        raise RuntimeError("Refusing an unowned native process-group cleanup")
    observation = {"group": group, "termSent": False, "killSent": False, "extinct": False}
    report["nativeProcessCleanup"] = observation

    def exists():
        child.poll()  # Reap the direct child even when descendants remain.
        try:
            os.killpg(group, 0)
            return True
        except ProcessLookupError:
            return False

    def wait_extinct(seconds):
        end = time.monotonic() + seconds
        while exists() and time.monotonic() < end:
            time.sleep(0.05)
        return not exists()

    if exists():
        try:
            os.killpg(group, signal.SIGTERM)
            observation["termSent"] = True
        except ProcessLookupError:
            pass
    if not wait_extinct(term_seconds):
        try:
            os.killpg(group, signal.SIGKILL)
            observation["killSent"] = True
        except ProcessLookupError:
            pass
        if not wait_extinct(kill_seconds):
            raise RuntimeError("Owned native process group survived bounded escalation; preserve its work")
    child.wait(timeout=1)
    observation["extinct"] = True


class UbuntuPackages:
    def __init__(self, work, env, report):
        self.env, self.report = dict(env), report
        self.work = work
        self.download_bytes, self.installed_kib, self.count = 0, 0, 0
        self.root = work / "apt"
        self.root.mkdir(mode=0o755)
        for name in ("empty", "lists"):
            (self.root / name).mkdir(mode=0o755)
        (self.root / "sources.list").write_text(SOURCES)
        config = self.root / "apt.conf"
        config.write_text(f'''Dir::Etc::parts "{self.root / 'empty'}";
Dir::Etc::main "/dev/null";
Dir::Etc::sourcelist "{self.root / 'sources.list'}";
Dir::Etc::sourceparts "{self.root / 'empty'}";
Dir::Etc::preferences "/dev/null";
Dir::Etc::preferencesparts "{self.root / 'empty'}";
Dir::Etc::netrc "/dev/null";
Dir::Etc::netrcparts "{self.root / 'empty'}";
Dir::Etc::trusted "/dev/null";
Dir::Etc::trustedparts "{self.root / 'empty'}";
Dir::State::lists "{self.root / 'lists'}";
Dir::Cache::pkgcache "";
Dir::Cache::srcpkgcache "";
APT::Install-Recommends "false";
APT::Install-Suggests "false";
APT::Get::AllowUnauthenticated "false";
Acquire::AllowInsecureRepositories "false";
Acquire::AllowDowngradeToInsecureRepositories "false";
Acquire::Check-Valid-Until "true";
Acquire::Languages "none";
Acquire::https::Verify-Peer "true";
Acquire::https::Verify-Host "true";
''')
        self.env["APT_CONFIG"] = str(config)
        owner = run(["dpkg-query", "-S", "/usr/share/keyrings/ubuntu-archive-keyring.gpg"], env)
        if not owner.startswith("ubuntu-keyring:"):
            raise RuntimeError("The Ubuntu archive keyring has unexpected package provenance")
        disk_checkpoint(report, "before-apt-metadata", work, download=256 * 1024 ** 2)
        run(["apt-get", "--error-on=any", "update"], self.env, timeout=180)
        disk_checkpoint(report, "after-apt-metadata", work)
        releases = list((self.root / "lists").glob("*_InRelease"))
        if len(releases) != 3 or any("Origin: Ubuntu\n" not in p.read_text() for p in releases):
            raise RuntimeError("Fresh authenticated Ubuntu release metadata is incomplete")

    def candidate(self, name, required=None):
        if not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*(?::amd64)?", name):
            raise RuntimeError("Unexpected package name")
        policy = run(["apt-cache", "policy", name], self.env)
        found = re.search(r"^\s*Candidate:\s*(\S+)\s*$", policy, re.M)
        if not found or found[1] == "(none)" or (required and required != found[1]):
            raise RuntimeError("No fixed Ubuntu candidate for " + name)
        version, active, origins = found[1], False, []
        for line in policy.splitlines():
            header = re.fullmatch(r"\s+(?:\*\*\*\s+)?(\S+)\s+\d+\s*", line)
            if header:
                active = header[1] == version
            elif active and re.search(r"\shttps?://", line):
                match = re.fullmatch(r"\s+\d+ https://(archive.ubuntu.com|security.ubuntu.com)/ubuntu (noble|noble-updates|noble-security)/(main|universe) amd64 Packages\s*", line)
                if not match:
                    raise RuntimeError("Non-Ubuntu package origin")
                origins.append(match.groups())
        if not origins:
            raise RuntimeError("Candidate has no authenticated Ubuntu package origin")
        return version

    def install_missing(self, requested):
        missing = []
        for name in sorted(set(requested)):
            status_text = run(["dpkg-query", "-W", "-f=${Status}", name], self.env, check=False)
            if status_text != "install ok installed":
                missing.append(name)
        if not missing:
            return
        pins = {name: self.candidate(name) for name in missing}
        simulation = run(["apt-get", "--simulate", "--no-remove", "--no-upgrade", "--no-install-recommends", "install", *(f"{n}={v}" for n, v in pins.items())], self.env, timeout=90)
        plan = []
        for line in simulation.splitlines():
            if line.startswith("Remv "):
                raise RuntimeError("Package removal is outside this check")
            if not line.startswith("Inst "):
                continue
            match = re.match(r"^Inst ([a-z0-9][a-z0-9+.:_-]*) \((\S+) ", line)
            if not match:
                raise RuntimeError("Existing package change is outside this check")
            name, version = match.groups()
            self.candidate(name, version)
            metadata = run(["apt-cache", "show", "--no-all-versions", f"{name}={version}"], self.env)
            size = re.search(r"^Size: (\d+)$", metadata, re.M)
            installed = re.search(r"^Installed-Size: (\d+)$", metadata, re.M)
            if not size or not installed:
                raise RuntimeError("Missing authenticated package footprint")
            plan.append({"name": name, "version": version, "bytes": int(size[1]), "installedKiB": int(installed[1])})
            pins[name] = version
        self.count += len(plan)
        self.download_bytes += sum(p["bytes"] for p in plan)
        self.installed_kib += sum(p["installedKiB"] for p in plan)
        if self.count > 40 or self.download_bytes > 150 * 1024 ** 2 or self.installed_kib > 400 * 1024:
            raise RuntimeError("Ordinary dependency plan exceeds the approved bound")
        self.report.setdefault("ubuntuPackagePlans", []).append(plan)
        disk_checkpoint(self.report, "before-apt-install", self.work,
                        download=sum(p["bytes"] for p in plan),
                        installed=sum(p["installedKiB"] for p in plan) * 1024)
        run(["sudo", "-n", "env", "-i", *(f"{k}={v}" for k, v in self.env.items()), "DEBIAN_FRONTEND=noninteractive", "/usr/bin/timeout", "--signal=TERM", "--kill-after=10s", "180s", "/usr/bin/apt-get", "--assume-yes", "--no-remove", "--no-upgrade", "--no-install-recommends", "install", *(f"{n}={v}" for n, v in sorted(pins.items()))], self.env, timeout=200)
        disk_checkpoint(self.report, "after-apt-install", self.work)


def download_asset(path):
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("The application asset worker is restricted to Linux x64")
    class HttpsRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, message, headers, newurl):
            parsed = urllib.parse.urlsplit(newurl)
            if parsed.scheme != "https" or parsed.hostname not in {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}:
                raise RuntimeError("Unexpected asset redirect")
            return super().redirect_request(request, fp, code, message, headers, newurl)
    opener = urllib.request.build_opener(HttpsRedirect())
    digest, total = hashlib.sha256(), 0
    with opener.open(ASSET_URL, timeout=20) as response, path.open("xb") as target:
        while chunk := response.read(1024 ** 2):
            total += len(chunk)
            if total > ASSET_SIZE:
                raise RuntimeError("Official asset exceeds pinned size")
            target.write(chunk)
            digest.update(chunk)
    if total != ASSET_SIZE or digest.hexdigest() != ASSET_SHA256:
        raise RuntimeError("Official application asset failed size/SHA256 verification")
    path.chmod(0o700)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    os_release = Path("/etc/os-release").read_text() if Path("/etc/os-release").exists() else ""
    if platform.system() != "Linux" or platform.machine() != "x86_64" or 'ID=ubuntu\n' not in os_release or 'VERSION_ID="24.04"' not in os_release:
        raise SystemExit("This proposal runs only in the disposable Ubuntu24.04 x64 job")
    if os.environ.get("GITHUB_REPOSITORY") != "tevinch/helphub" or os.environ.get("GITHUB_REF") != "refs/heads/main" or os.environ.get("GITHUB_SERVER_URL") != "https://github.com":
        raise SystemExit("Unexpected repository, ref or host")
    if not re.fullmatch(r"[0-9a-f]{40}", os.environ.get("GITHUB_SHA", "")):
        raise SystemExit("Missing exact reviewed commit identity")
    parent = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    output = args.output.resolve()
    if parent == Path("/") or output.parent != parent or output.name != "selection-wrap-evidence" or output.exists():
        raise SystemExit("Refusing unexpected or existing evidence path")
    output.mkdir(mode=0o700)
    report = {"stage": "native GUI prerequisite only", "macroAcceptance": "not run", "platformScope": "Linux / official Qt5 AppImage", "runnerImage": os.environ.get("ImageVersion", "unreported"), "commit": os.environ["GITHUB_SHA"], "status": "unknown"}
    work = Path(tempfile.mkdtemp(prefix="selection-wrap.", dir=parent))
    work.chmod(0o711)  # Only APT's public metadata directories are traversable.
    native_group_safe = True
    try:
        disk_checkpoint(report, "initial", work)
        if shutil.disk_usage(work).free < 4 * GIB:
            raise RuntimeError("Insufficient runner space for the bounded setup and2GiB reserve")
        for name in ("tmp", "config", "cache", "data", "runtime"):
            (work / name).mkdir(mode=0o700)
        # Preserve the runner's existing HOME value; isolate editor settings with --config/XDG.
        env = {name: os.environ[name] for name in ("HOME",) if name in os.environ}
        env.update({"PATH": PATH, "TMPDIR": str(work / "tmp"), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"})
        packages = UbuntuPackages(work, env, report)
        packages.install_missing(["xvfb", "xauth", "xdotool", "x11-utils", "xclip", "openbox", "python3-pil", "python3-pyatspi", "at-spi2-core", "dbus-x11", "squashfs-tools"])
        image = work / ASSET_NAME
        # An independent whole-process deadline bounds streaming, including slow servers.
        disk_checkpoint(report, "before-application-download", work, download=ASSET_SIZE)
        run(["/usr/bin/timeout", "--signal=TERM", "--kill-after=5s", "120s", "/usr/bin/python3", str(Path(__file__).resolve()), "--asset-only", str(image)], env, timeout=130)
        offset_text = run([str(image), "--appimage-offset"], env, timeout=10).strip()
        if not offset_text.isdigit() or not 0 < int(offset_text) < ASSET_SIZE:
            raise RuntimeError("Official runtime did not provide a valid filesystem offset")
        listing = run(["unsquashfs", "-lln", "-o", offset_text, str(image)], env, timeout=30)
        (output / "application-listing.txt").write_text(listing)
        footprint, entry_count = listed_bytes(listing)
        disk_checkpoint(report, "before-application-extraction", work, installed=footprint)
        appdir = work / "appdir"
        run(["unsquashfs", "-no-progress", "-strict-errors", "-no-xattrs", "-processors", "2", "-o", offset_text, "-d", str(appdir), str(image)], env, timeout=60)
        report["officialAsset"] = {"name": ASSET_NAME, "bytes": ASSET_SIZE, "sha256": ASSET_SHA256, "listedAllocatedBytes": footprint, "entryCount": entry_count}
        actual_app_bytes, actual_work_bytes = allocated_tree_bytes(appdir), allocated_tree_bytes(work)
        report["officialAsset"]["actualAllocatedBytes"] = actual_app_bytes
        report["ownedWorkAllocatedBytesAfterExtraction"] = actual_work_bytes
        disk_checkpoint(report, "after-application-extraction", work)
        if actual_app_bytes > 1536 * 1024 ** 2 or actual_work_bytes > 2 * GIB:
            raise RuntimeError("Actual allocated application/work footprint exceeds the owned budget")
        binary, apprun = appdir / "usr/bin/texstudio", appdir / "AppRun"
        for path in (binary, apprun):
            contained_regular_file(path, appdir)
        libraries = sorted({str(p.parent) for p in appdir.rglob("*.so*") if p.is_file() and p.resolve().is_relative_to(appdir.resolve())})
        link_env = dict(env, LD_LIBRARY_PATH=":".join(libraries))
        xcb_plugins = list(appdir.rglob("libqxcb.so"))
        if len(xcb_plugins) != 1:
            raise RuntimeError("Expected one official XCB platform plugin")
        contained_regular_file(xcb_plugins[0], appdir)
        dependencies = "\n".join(run(["ldd", str(p)], link_env) for p in (binary, xcb_plugins[0]))
        missing = set(re.findall(r"^\s*(\S+) => not found\s*$", dependencies, re.M))
        if missing - RUNTIME_PACKAGES.keys():
            raise RuntimeError("Unreviewed native dependency: " + ", ".join(sorted(missing - RUNTIME_PACKAGES.keys())))
        packages.install_missing([RUNTIME_PACKAGES[name] for name in missing])
        dependencies = "\n".join(run(["ldd", str(p)], link_env) for p in (binary, xcb_plugins[0]))
        if "not found" in dependencies:
            raise RuntimeError("Native runtime dependencies are unresolved")
        (output / "runtime-dependencies.txt").write_text(dependencies.replace(str(work), "<owned-work>"))
        source = Path(__file__).resolve().parent
        desktop_env = dict(env, XDG_CONFIG_HOME=str(work / "config"), XDG_CACHE_HOME=str(work / "cache"), XDG_DATA_HOME=str(work / "data"), XDG_RUNTIME_DIR=str(work / "runtime"), QT_QPA_PLATFORM="xcb", QT_LINUX_ACCESSIBILITY_ALWAYS_ON="1")
        command = ["dbus-run-session", "--", "xvfb-run", "-a", "-s", "-screen 0 1600x1000x24 -dpi 96", "/usr/bin/python3", str(source / "desktop.py"), "--app", str(apprun), "--work", str(work), "--output", str(output), "--fixture", str(source / "baseline.tex")]
        disk_checkpoint(report, "before-native-probe", work)
        child = subprocess.Popen(command, env=desktop_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        native_group_safe = False
        try:
            log, _ = child.communicate(timeout=240)
            (output / "desktop.log").write_text(log.replace(str(work), "<owned-work>"))
            if child.returncode:
                raise RuntimeError("Native GUI prerequisite was not established; inspect desktop evidence")
        except subprocess.TimeoutExpired as error:
            partial = error.stdout or ""
            if isinstance(partial, bytes):
                partial = partial.decode("utf-8", errors="replace")
            (output / "desktop.log").write_text(partial.replace(str(work), "<owned-work>"))
            raise RuntimeError("The bounded native GUI probe timed out; prerequisites remain unknown") from error
        finally:
            try:
                terminate_group(child, report)
                native_group_safe = True
            finally:
                disk_checkpoint(report, "after-native-probe", work)
        report["status"] = "GUI prerequisite observed; complete wrapping workflow still unverified"
        if sum(p.stat().st_size for p in output.rglob("*") if p.is_file()) > 50 * 1024 ** 2:
            raise RuntimeError("Evidence exceeds the small artifact budget")
    except Exception as error:
        report["status"] = "unknown; prerequisite check did not complete"
        report["error"] = str(error)
        raise
    finally:
        report["workCleanup"] = "pending" if native_group_safe else "preserved because native group extinction is unverified"
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        if native_group_safe:
            if work.parent != parent or work.is_symlink() or work.stat().st_uid != os.getuid() or not re.fullmatch(r"selection-wrap\.[A-Za-z0-9_]+", work.name):
                raise RuntimeError("Refusing unsafe owned-work cleanup")
            shutil.rmtree(work)
            report["workCleanup"] = "owned work removed after verified native group extinction or before launch"
            (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(report["status"], flush=True)


if __name__ == "__main__":
    if len(os.sys.argv) == 3 and os.sys.argv[1] == "--asset-only":
        download_asset(Path(os.sys.argv[2]))
    else:
        main()
