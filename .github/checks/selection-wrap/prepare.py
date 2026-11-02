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
FONT_CONFIG_PATH = Path("/etc/fonts/fonts.conf")
FONT_CONFIG_PACKAGE = "fontconfig-config"
FONT_LINK_ARCHIVE_PATH = "squashfs-root/etc/fonts/fonts.conf"
FONT_LINK_ASSET_SHA256 = "32ff7e43eebe9b2befb28c24f60fb8705cf01e47cba9400a6494f7c0032e86f8"
SOURCES = (
    "deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] "
    "https://archive.ubuntu.com/ubuntu noble main universe\n"
    "deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] "
    "https://archive.ubuntu.com/ubuntu noble-updates main universe\n"
    "deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] "
    "https://security.ubuntu.com/ubuntu noble-security main universe\n"
)


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


def vendor_archive_listing(listing, asset_sha256):
    """Classify the one pinned vendor host reference; close every remaining entry."""
    if asset_sha256 != FONT_LINK_ASSET_SHA256:
        raise RuntimeError("The vendor font link is approved only for the exact reviewed asset")
    projected, found, other_links = [], 0, 0
    expected = ["lrwxrwxrwx", "0/0", "21", "2026-10-23", "15:22",
                FONT_LINK_ARCHIVE_PATH + " -> " + str(FONT_CONFIG_PATH)]
    for line in listing.splitlines(keepends=True):
        fields = line.rstrip("\r\n").split(maxsplit=5)
        name = fields[5].partition(" -> ")[0] if len(fields) == 6 else ""
        if name == FONT_LINK_ARCHIVE_PATH:
            if fields != expected or found:
                raise RuntimeError("Unexpected or duplicate vendor font-config leaf")
            found += 1
        else:
            projected.append(line)
            other_links += bool(fields and fields[0].startswith("l"))
    if found != 1:
        raise RuntimeError("The exact reviewed vendor font-config leaf is missing")
    closed_listing = "".join(projected)
    # Omission is only for closure proof: aliases/descendants now have no destination.
    footprint, count = listed_bytes(closed_listing)
    if count != 921 or other_links:
        raise RuntimeError("The pinned archive must have 921 closed entries and only the one vendor link")
    footprint += 4096
    if footprint > 1536 * 1024 ** 2:
        raise RuntimeError("Uncompressed application exceeds the owned budget")
    proof = {"rawListingSHA256": hashlib.sha256(listing.encode()).hexdigest(),
             "projectedListingSHA256": hashlib.sha256(closed_listing.encode()).hexdigest(),
             "containedEntryCount": count, "vendorHostReferenceCount": 1,
             "vendorHostReference": {"archivePath": FONT_LINK_ARCHIVE_PATH,
                                     "target": str(FONT_CONFIG_PATH), "allocatedBudgetBytes": 4096}}
    return footprint, count + 1, proof


def inode_fingerprint(info):
    return {"mode": info.st_mode, "uid": info.st_uid, "gid": info.st_gid,
            "device": info.st_dev, "inode": info.st_ino, "size": info.st_size,
            "mtimeNs": info.st_mtime_ns, "ctimeNs": info.st_ctime_ns}


def validate_host_font_snapshot(snapshot):
    """Fail closed on the fixed host leaf, its root-owned parents and package record."""
    if snapshot.get("path") != str(FONT_CONFIG_PATH):
        raise RuntimeError("Unexpected host font-config path")
    ancestors = snapshot.get("ancestors", [])
    if [item.get("path") for item in ancestors] != ["/", "/etc", "/etc/fonts"]:
        raise RuntimeError("Unexpected host font-config ancestor chain")
    for info, directory in [(item, True) for item in ancestors] + [(snapshot["file"], False)]:
        required = ("mode", "uid", "gid", "device", "inode", "size", "mtimeNs", "ctimeNs")
        if any(type(info.get(key)) is not int or info[key] < 0 for key in required):
            raise RuntimeError("Invalid host font-config metadata")
        valid_type = stat.S_ISDIR(info["mode"]) if directory else stat.S_ISREG(info["mode"])
        if not valid_type or info["uid"] != 0 or info["gid"] != 0 or info["mode"] & 0o022:
            raise RuntimeError("Host font-config path must be a root-owned non-writable directory/regular file")
    if not 0 < snapshot["file"]["size"] <= 65536:
        raise RuntimeError("Host font-config file exceeds its small read-only bound")
    package = snapshot.get("package", {})
    version = package.get("version", "")
    if (package.get("name") != FONT_CONFIG_PACKAGE or package.get("status") != "install ok installed"
            or package.get("ownerQuery") != FONT_CONFIG_PACKAGE + ": " + str(FONT_CONFIG_PATH)
            or not re.fullmatch(r"[A-Za-z0-9.+:~_-]+", version)
            or package.get("ubuntuCandidateVersion") != version
            or not re.fullmatch(r"[0-9a-f]{32}", snapshot.get("md5", ""))
            or package.get("conffileMd5") != snapshot["md5"]
            or not re.fullmatch(r"[0-9a-f]{64}", snapshot.get("sha256", ""))):
        raise RuntimeError("Host font-config package/checksum provenance is not established")


def assert_same_host_font_config(before, after):
    validate_host_font_snapshot(before)
    validate_host_font_snapshot(after)
    if ({key: value for key, value in before.items() if key != "ancestors"}
            != {key: value for key, value in after.items() if key != "ancestors"}):
        raise RuntimeError("Read-only host font-config fingerprint changed")
    # Allowed APT work may change directory timestamps/size through sibling entries.
    # Retain those observations, but require the same safe directory identities.
    identity = ("path", "mode", "uid", "gid", "device", "inode")
    for previous, current in zip(before["ancestors"], after["ancestors"]):
        if any(previous[key] != current[key] for key in identity):
            raise RuntimeError("Host font-config ancestor safety/identity changed")


def host_font_config_snapshot(packages):
    """Read only; inherit the trusted Ubuntu runner/package database, never repair it."""
    ancestors = [{"path": str(path), **inode_fingerprint(path.lstat())}
                 for path in (Path("/"), Path("/etc"), Path("/etc/fonts"))]
    file_info = inode_fingerprint(FONT_CONFIG_PATH.lstat())
    # Validate parents/type before open; O_NOFOLLOW also rejects a leaf replacement.
    for item in ancestors:
        if not stat.S_ISDIR(item["mode"]) or item["uid"] != 0 or item["gid"] != 0 or item["mode"] & 0o022:
            raise RuntimeError("Unsafe host font-config ancestor")
    if (not stat.S_ISREG(file_info["mode"]) or file_info["uid"] != 0 or file_info["gid"] != 0
            or file_info["mode"] & 0o022 or not 0 < file_info["size"] <= 65536
            or FONT_CONFIG_PATH.resolve(strict=True) != FONT_CONFIG_PATH):
        raise RuntimeError("Unsafe host font-config file")
    with os.fdopen(os.open(FONT_CONFIG_PATH, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC), "rb") as stream:
        if inode_fingerprint(os.fstat(stream.fileno())) != file_info:
            raise RuntimeError("Host font-config changed before its read-only observation")
        content = stream.read(65537)
        if len(content) != file_info["size"] or inode_fingerprint(os.fstat(stream.fileno())) != file_info:
            raise RuntimeError("Host font-config changed during its bounded observation")
    if inode_fingerprint(FONT_CONFIG_PATH.lstat()) != file_info:
        raise RuntimeError("Host font-config changed after its read-only observation")
    if any(inode_fingerprint(Path(item["path"]).lstat()) != {k: v for k, v in item.items() if k != "path"}
           for item in ancestors):
        raise RuntimeError("Host font-config ancestor changed during observation")
    owner = run(["dpkg-query", "-S", str(FONT_CONFIG_PATH)], packages.env).strip()
    record = run(["dpkg-query", "-W", "-f=${Status}\n${Version}\n${Conffiles}", FONT_CONFIG_PACKAGE], packages.env)
    fields = record.split("\n", 2)
    if len(fields) != 3:
        raise RuntimeError("Missing installed font-config package metadata")
    status_text, version, conffiles = fields
    checksums = [match[1] for line in conffiles.splitlines()
                 if (match := re.fullmatch(r"\s*/etc/fonts/fonts\.conf ([0-9a-f]{32})", line))]
    if len(checksums) != 1:
        raise RuntimeError("Missing unique unmodified package font-config record")
    candidate = packages.candidate(FONT_CONFIG_PACKAGE, version)
    snapshot = {"path": str(FONT_CONFIG_PATH), "ancestors": ancestors, "file": file_info,
                "sha256": hashlib.sha256(content).hexdigest(), "md5": hashlib.md5(content).hexdigest(),
                "package": {"name": FONT_CONFIG_PACKAGE, "status": status_text, "version": version,
                            "ubuntuCandidateVersion": candidate, "ownerQuery": owner,
                            "conffileMd5": checksums[0]}}
    validate_host_font_snapshot(snapshot)
    return snapshot


def observe_host_font_config(packages, report, stage, expected=None):
    observation = {"stage": stage, "status": "checking"}
    report.setdefault("hostFontConfigObservations", []).append(observation)
    try:
        snapshot = host_font_config_snapshot(packages)
        observation["fingerprint"] = snapshot
        if expected is not None:
            assert_same_host_font_config(expected, snapshot)
        observation["status"] = ("verified file unchanged; ancestor safety/identity unchanged"
                                 if expected is not None else "verified read-only baseline")
        return snapshot
    except Exception as error:
        observation.update(status="rejected", error=str(error))
        raise


def check_extracted_vendor_leaf(appdir):
    # lstat/walk do not follow the one vendor reference or read its host target.
    for path in (appdir, appdir / "etc", appdir / "etc/fonts"):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            raise RuntimeError("Extracted vendor font-config parent is not an owned real directory")
    leaf = appdir / "etc/fonts/fonts.conf"
    info = leaf.lstat()
    if (not stat.S_ISLNK(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o777 or info.st_uid != os.getuid()
            or info.st_size != 21 or os.readlink(leaf) != str(FONT_CONFIG_PATH)):
        raise RuntimeError("Extracted vendor font-config leaf differs from its reviewed link")
    links = []
    def fail_walk(error):
        raise error
    for folder, directories, files in os.walk(appdir, followlinks=False, onerror=fail_walk):
        for name in directories + files:
            path = Path(folder) / name
            if path.is_symlink():
                links.append(path.relative_to(appdir).as_posix())
    if sorted(links) != ["etc/fonts/fonts.conf"]:
        raise RuntimeError("Unexpected extracted link or alias beyond the one vendor host reference")
    return {"archiveRelativePath": "etc/fonts/fonts.conf", "target": os.readlink(leaf),
            "uid": info.st_uid, "mode": stat.S_IMODE(info.st_mode), "symlinkCount": len(links)}


def contained_regular_file(path, root):
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve(strict=True)) or not resolved.is_file():
        raise RuntimeError("Official application file resolves outside its owned root")
    return resolved


def record_launcher_evidence(apprun, output):
    # The caller has already verified this original vendor file is contained.
    with apprun.open("rb") as source:
        content = source.read(16 * 1024 + 1)
    if not content or len(content) > 16 * 1024:
        raise RuntimeError("Original vendor launcher exceeds the small evidence bound")
    name = "application-launcher.txt"
    (output / name).write_bytes(content)
    return {"evidenceFile": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


def prepare_loader_bootstrap(appdir, image, offset, output, env):
    # This task-owned bootstrap changes exactly one vendor selection line, never file modes.
    original_sha = "85f2e5b8fed68bb23b4197fbdfd0aee57478c5e59bb3da1d43576c4fa7698242"
    effective_sha = "46a2ddb2d23a60dcc526579760a17574e8d8b831ba425995b0ff8f7532b323e0"
    old_line = b'LD_LINUX=$(find "$HERE" -name \'ld-*.so.*\' | head -n 1)\n'
    new_line = b'LD_LINUX="$HERE/lib64/ld-linux-x86-64.so.2"\n'
    specs = (("lib64/ld-linux-x86-64.so.2", 0o755),
             ("usr/lib64/ld-linux-x86-64.so.2", 0o644))
    apprun = appdir / "AppRun"
    original_info = apprun.lstat()
    if (not stat.S_ISREG(original_info.st_mode) or original_info.st_uid != os.geteuid()
            or stat.S_IMODE(original_info.st_mode) != 0o755):
        raise RuntimeError("Unexpected original launcher type, owner or mode")
    contained_regular_file(apprun, appdir)
    with apprun.open("rb") as stream:
        original = stream.read(16 * 1024 + 1)
    if (hashlib.sha256(original).hexdigest() != original_sha or original.count(old_line) != 1
            or (output / "application-launcher.txt").read_bytes() != original):
        raise RuntimeError("Original vendor launcher bytes or retained evidence mismatch")
    found = sorted(p.relative_to(appdir).as_posix() for p in appdir.rglob("ld-*.so.*"))
    if found != sorted(name for name, mode in specs):
        raise RuntimeError("Unexpected bundled loader candidate set")
    if not offset.isdigit() or not 0 < int(offset) < ASSET_SIZE:
        raise RuntimeError("Invalid verified application filesystem offset")
    proof = {"scope": "ephemeral native-test bootstrap; one vendor loader-selection line changed",
             "originalSHA256": original_sha, "effectiveSHA256": effective_sha,
             "selectedLoader": specs[0][0], "candidates": [], "fileModesChanged": False,
             "environmentChanged": False}
    for relative, expected_mode in specs:
        path = appdir / relative
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != expected_mode or info.st_size != 240936):
            raise RuntimeError("Bundled loader type, owner, mode or size differs from the verified archive")
        contained_regular_file(path, appdir)
        parents = []
        parent = path.parent
        while True:
            metadata = parent.lstat()
            if not stat.S_ISDIR(metadata.st_mode) or not os.access(parent, os.X_OK):
                raise RuntimeError("Bundled loader parent is not a searchable real directory")
            parents.append({"path": "." if parent == appdir else parent.relative_to(appdir).as_posix(),
                            "mode": oct(stat.S_IMODE(metadata.st_mode)), "uid": metadata.st_uid,
                            "gid": metadata.st_gid})
            if parent == appdir:
                break
            parent = parent.parent
        with path.open("rb") as stream:
            extracted = stream.read(240937)
        archive = subprocess.run(["/usr/bin/timeout", "--signal=TERM", "--kill-after=3s", "15s",
                                  "unsquashfs", "-cat", "-no-wildcards", "-no-progress", "-processors", "2",
                                  "-o", offset, str(image), relative], env=env, capture_output=True, timeout=20)
        if (archive.returncode or len(archive.stderr) > 8192 or len(archive.stdout) != 240936
                or len(extracted) != 240936 or extracted != archive.stdout):
            raise RuntimeError("Read-only archive comparison of the bundled loader failed")
        proof["candidates"].append({"path": relative, "mode": oct(stat.S_IMODE(info.st_mode)),
                                     "uid": info.st_uid, "gid": info.st_gid, "device": info.st_dev,
                                     "inode": info.st_ino, "bytes": info.st_size,
                                     "extractedSHA256": hashlib.sha256(extracted).hexdigest(),
                                     "archiveSHA256": hashlib.sha256(archive.stdout).hexdigest(),
                                     "executableForRunner": os.access(path, os.X_OK), "parents": parents})
    if not proof["candidates"][0]["executableForRunner"]:
        raise RuntimeError("The selected bundled loader is not executable for this runner")
    effective = original.replace(old_line, new_line, 1)
    if hashlib.sha256(effective).hexdigest() != effective_sha:
        raise RuntimeError("The one-line effective launcher differs from the reviewed bytes")
    (output / "loader-bootstrap-observations.json").write_text(json.dumps(proof, indent=2) + "\n")
    (output / "effective-application-launcher.txt").write_bytes(effective)
    apprun.write_bytes(effective)
    after = apprun.lstat()
    if (after.st_mode != original_info.st_mode or after.st_uid != original_info.st_uid
            or after.st_gid != original_info.st_gid or apprun.read_bytes() != effective):
        raise RuntimeError("Effective launcher write changed metadata or failed exact readback")
    return proof


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
        self.report.setdefault("ubuntuPackagePlans", []).append(plan)
        statistics = {
            "currentPlan": {"newPackageCount": len(plan),
                            "uniquePackageCount": len({p["name"].removesuffix(":amd64") for p in plan}),
                            "downloadBytes": sum(p["bytes"] for p in plan),
                            "installedKiB": sum(p["installedKiB"] for p in plan)},
            "cumulative": {"newPackageCount": self.count, "downloadBytes": self.download_bytes,
                           "installedKiB": self.installed_kib},
            "limits": {"newPackageCount": 64, "downloadBytes": 150 * 1024 ** 2,
                       "installedKiB": 400 * 1024},
        }
        self.report.setdefault("ubuntuPackagePlanStatistics", []).append(statistics)
        if self.count > 64 or self.download_bytes > 150 * 1024 ** 2 or self.installed_kib > 400 * 1024:
            raise RuntimeError("Ordinary dependency plan exceeds the approved bound "
                               f"(new={self.count}/64, download={self.download_bytes}/{150 * 1024 ** 2}B, "
                               f"installed={self.installed_kib}/{400 * 1024}KiB)")
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
        footprint, entry_count, archive_proof = vendor_archive_listing(listing, ASSET_SHA256)
        report["officialAsset"] = {"name": ASSET_NAME, "bytes": ASSET_SIZE, "sha256": ASSET_SHA256,
                                   "listedAllocatedBytes": footprint, "entryCount": entry_count,
                                   "archiveClosure": archive_proof}
        disk_checkpoint(report, "before-application-extraction", work, installed=footprint)
        appdir = work / "appdir"
        if os.geteuid() == 0 or appdir.exists() or appdir.is_symlink():
            raise RuntimeError("Extraction requires an unprivileged process and a fresh owned destination")
        host_font_baseline = observe_host_font_config(packages, report, "before-application-extraction")
        try:
            run(["unsquashfs", "-no-progress", "-strict-errors", "-no-xattrs", "-processors", "2", "-o", offset_text, "-d", str(appdir), str(image)], env, timeout=60)
        finally:
            observe_host_font_config(packages, report, "after-application-extraction", host_font_baseline)
        report["officialAsset"]["extractedVendorHostReference"] = check_extracted_vendor_leaf(appdir)
        actual_app_bytes, actual_work_bytes = allocated_tree_bytes(appdir), allocated_tree_bytes(work)
        report["officialAsset"]["actualAllocatedBytes"] = actual_app_bytes
        report["ownedWorkAllocatedBytesAfterExtraction"] = actual_work_bytes
        disk_checkpoint(report, "after-application-extraction", work)
        if actual_app_bytes > 1536 * 1024 ** 2 or actual_work_bytes > 2 * GIB:
            raise RuntimeError("Actual allocated application/work footprint exceeds the owned budget")
        binary, apprun = appdir / "usr/bin/texstudio", appdir / "AppRun"
        for path in (binary, apprun):
            contained_regular_file(path, appdir)
        xcb_plugins = list(appdir.rglob("libqxcb.so"))
        if len(xcb_plugins) != 1:
            raise RuntimeError("Expected one official XCB platform plugin")
        contained_regular_file(xcb_plugins[0], appdir)
        report["officialAsset"]["launcher"] = record_launcher_evidence(apprun, output)
        report["officialAsset"]["launcherBootstrap"] = prepare_loader_bootstrap(appdir, image, offset_text, output, env)
        report["runtimeDependencyAssessment"] = {"method": "native GUI through vendor AppRun with one recorded bundled-loader selection adaptation",
                                                 "staticDependencyAudit": "not performed",
                                                 "automaticRuntimePackageInstall": False}
        source = Path(__file__).resolve().parent
        desktop_env = dict(env, XDG_CONFIG_HOME=str(work / "config"), XDG_CACHE_HOME=str(work / "cache"), XDG_DATA_HOME=str(work / "data"), XDG_RUNTIME_DIR=str(work / "runtime"), QT_QPA_PLATFORM="xcb", QT_LINUX_ACCESSIBILITY_ALWAYS_ON="1")
        command = ["dbus-run-session", "--", "xvfb-run", "-a", "-s", "-screen 0 1600x1000x24 -dpi 96", "/usr/bin/python3", str(source / "desktop.py"), "--app", str(apprun), "--work", str(work), "--output", str(output), "--fixture", str(source / "baseline.tex")]
        disk_checkpoint(report, "before-native-probe", work)
        observe_host_font_config(packages, report, "before-native-probe", host_font_baseline)
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
                try:
                    disk_checkpoint(report, "after-native-probe", work)
                finally:
                    observe_host_font_config(packages, report, "after-native-probe", host_font_baseline)
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
