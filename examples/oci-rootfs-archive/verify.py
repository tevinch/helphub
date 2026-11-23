#!/usr/bin/env python3
"""Exercise both archive formats with a synthetic two-layer OCI image."""

import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import tarfile
import tempfile


MEDIA_TYPE = "application/vnd.oci.image."
CONTAINER = "oci-demo"


def add_file(archive, name, data, mode=0o644):
    entry = tarfile.TarInfo(name)
    entry.size = len(data)
    entry.mode = mode
    archive.addfile(entry, io.BytesIO(data))


def make_layer(files, symlinks=()):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, data in files.items():
            add_file(archive, name, data)
        for name, target in symlinks:
            entry = tarfile.TarInfo(name)
            entry.type = tarfile.SYMTYPE
            entry.linkname = target
            archive.addfile(entry)
    return buffer.getvalue()


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def make_oci_archive(destination):
    architecture = {"aarch64": "arm64", "x86_64": "amd64"}.get(platform.machine())
    if architecture is None:
        raise SystemExit("This fixture supports Linux ARM64 and x86-64 hosts.")

    base = make_layer({
        "etc/hosts": b"fixture hosts before install\n",
        "etc/demo/version": b"first\n",
        "etc/demo/inherited": b"keep me\n",
        "etc/demo/obsolete": b"remove me\n",
    }, [("bin/demo-version", "../etc/demo/version")])
    update = make_layer({
        "etc/demo/.wh.obsolete": b"",
        "etc/demo/version": b"second\n",
        "etc/demo/added": b"new file\n",
    })

    with tarfile.open(destination, mode="w") as archive:
        def add_json(name, value):
            add_file(archive, name, json.dumps(value).encode("utf-8"))

        def blob(kind, data):
            identifier = digest(data)
            add_file(archive, "blobs/" + identifier.replace(":", "/"), data)
            return {"mediaType": MEDIA_TYPE + kind, "digest": identifier, "size": len(data)}

        add_json("oci-layout", {"imageLayoutVersion": "1.0.0"})
        layer_descriptors = [blob("layer.v1.tar+gzip", gzip.compress(layer, mtime=0))
                             for layer in (base, update)]
        config = blob("config.v1+json", json.dumps({
            "architecture": architecture,
            "os": "linux",
            "config": {},
            "rootfs": {"type": "layers", "diff_ids": [digest(base), digest(update)]},
        }).encode("utf-8"))
        manifest = blob("manifest.v1+json", json.dumps({
            "schemaVersion": 2,
            "mediaType": MEDIA_TYPE + "manifest.v1+json",
            "config": config,
            "layers": layer_descriptors,
        }).encode("utf-8"))
        manifest["platform"] = {"architecture": architecture, "os": "linux"}
        add_json("index.json", {"schemaVersion": 2, "manifests": [manifest]})


def pd(workspace, *args, check=True):
    workspace.mkdir(exist_ok=True)
    environment = {**os.environ, "XDG_DATA_HOME": str(workspace / "data"),
                   "XDG_CACHE_HOME": str(workspace / "cache")}
    return subprocess.run(["proot-distro", *map(str, args)], env=environment, check=check)


def container_dir(workspace, name=CONTAINER):
    return workspace / "data" / "proot-distro" / "containers" / name


def check_tree(root):
    contents = {item.name: item.read_bytes() for item in (root / "etc/demo").iterdir()}
    assert contents == {"version": b"second\n", "inherited": b"keep me\n", "added": b"new file\n"}, contents
    assert os.readlink(root / "bin/demo-version") == "../etc/demo/version"
    assert (root / "bin/demo-version").read_bytes() == b"second\n"


def check_members(filename, base):
    with tarfile.open(filename) as archive:
        names = {PurePosixPath(member.name).as_posix() for member in archive}
    expected = {str(PurePosixPath(base, "etc/demo", name)) for name in ("inherited", "version", "added")}
    assert expected <= names, names
    assert all(not name.endswith(("/obsolete", "/.wh.obsolete")) for name in names), names
    return names


def snapshot(root):
    entries = {}
    for item in root.rglob("*"):
        content = None
        if item.is_symlink():
            content = os.readlink(item)
        elif item.is_file():
            content = item.read_bytes()
        entries[item.relative_to(root)] = (item.lstat().st_mode, content)
    return entries


def export_plain(rootfs, filename, *, check=True):
    command = 'set -C; tar -C "$1" -czf - . > "$2"'
    return subprocess.run(["sh", "-ec", command, "sh", str(rootfs), str(filename)], check=check)


def main():
    if platform.system() != "Linux" or os.environ.get("TERMUX_VERSION") or os.environ.get("TERMUX_APP__APP_VERSION_NAME"):
        raise SystemExit("Run this verifier on regular Linux, where it can isolate data with XDG_DATA_HOME.")

    with tempfile.TemporaryDirectory(prefix="oci-rootfs-") as folder:
        work = Path(folder)
        image = work / "image.oci.tar"
        make_oci_archive(image)
        source = work / "source"
        pd(source, "install", image, "--name", CONTAINER)
        original = container_dir(source)
        check_tree(original / "rootfs")
        hosts = (original / "rootfs/etc/hosts").read_text()
        assert "localhost" in hosts and "fixture hosts before install" not in hosts
        manifest = (original / "manifest.json").read_bytes()
        assert len(json.loads(manifest)["manifest"]["layers"]) == 2
        print("1. OCI install applies both layers and honors the whiteout.", flush=True)

        backup = work / "container-backup.tar.gz"
        pd(source, "backup", CONTAINER, "--output", backup)
        assert f"{CONTAINER}/manifest.json" in check_members(backup, f"{CONTAINER}/rootfs")
        restored = work / "restored"
        pd(restored, "restore", backup)
        restored_container = container_dir(restored)
        assert (restored_container / "manifest.json").read_bytes() == manifest
        check_tree(restored_container / "rootfs")
        print("2. Native backup restores both the tree and OCI metadata into fresh state.", flush=True)

        plain = work / "rootfs.tar.gz"
        original_state = snapshot(original)
        export_plain(original / "rootfs", plain)
        plain_names = check_members(plain, ".")
        assert all(not name.endswith("manifest.json") for name in plain_names)
        raw_destination = work / "plain-install"
        pd(raw_destination, "install", plain, "--name", "plain-demo")
        plain_container = container_dir(raw_destination, "plain-demo")
        check_tree(plain_container / "rootfs")
        assert not (plain_container / "manifest.json").exists()
        assert snapshot(original) == original_state
        print("3. Plain archive reinstalls the merged tree and leaves the source unchanged.", flush=True)

        wrong_destination = work / "wrong-command"
        result = pd(wrong_destination, "restore", plain, check=False)
        assert result.returncode != 0
        assert not container_dir(wrong_destination).exists()
        print("4. Native restore rejects the plain archive as expected.", flush=True)

        original_archive = plain.read_bytes()
        assert export_plain(original / "rootfs", plain, check=False).returncode != 0
        assert plain.read_bytes() == original_archive
        print("5. Repeating a plain export preserves the existing archive.", flush=True)


if __name__ == "__main__":
    main()
