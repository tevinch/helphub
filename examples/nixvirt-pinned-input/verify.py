#!/usr/bin/env python3
"""Evaluate the example with Nix and check its actual dependency provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

NIXVIRT_REV = "b9489f0e4b1cef1d5fe5dcc48f705c1cdfc9e7a8"
SELECTED_REV = "b349185bb79c7cf7ad8ea8c097931730bf473c71"
BASELINE_REV = "50ab793786d9de88ee30ec4e4c24fb4236fc2674"
REQUIRED = {
    "nixVersion", "nixvirtRevision", "rootRevision", "dependencyRevision",
    "baselineRevision", "rootPath", "dependencyPath", "baselinePath",
    "rootVersion", "dependencyVersion", "baselineVersion", "generatedXml",
    "writeXmlDerivation", "expectedDerivation",
}


def check_evidence(data):
    """Return errors; never accept absent operations or root-only version checks."""
    errors = []
    if not isinstance(data, dict):
        return ["result must be a JSON object"]
    missing = REQUIRED - data.keys()
    if missing:
        return ["missing evidence: " + ", ".join(sorted(missing))]
    if any(not isinstance(data[k], str) or not data[k] for k in REQUIRED):
        return ["every evidence field must be a nonempty string"]
    for key, expected in [
        ("nixvirtRevision", NIXVIRT_REV), ("rootRevision", SELECTED_REV),
        ("dependencyRevision", SELECTED_REV), ("baselineRevision", BASELINE_REV),
    ]:
        if data[key] != expected:
            errors.append(("NixVirt nixpkgs" if key == "dependencyRevision" else key)
                          + " revision differs from the required pin")
    if not data["rootVersion"].startswith("26.05"):
        errors.append("root nixpkgs version is not 26.05")
    if not data["dependencyVersion"].startswith("26.05"):
        errors.append("NixVirt nixpkgs version is not 26.05")
    if not data["baselineVersion"].startswith("24.11"):
        errors.append("original import did not reproduce the 24.11 baseline")
    if data["dependencyPath"] != data["rootPath"]:
        errors.append("NixVirt nixpkgs source path differs from the root input")
    if data["baselinePath"] == data["rootPath"]:
        errors.append("original and selected nixpkgs unexpectedly use the same source")
    if data["writeXmlDerivation"] != data["expectedDerivation"]:
        errors.append("NixVirt nixpkgs writeXML derivation differs from the selected package set")
    if not data["writeXmlDerivation"].startswith("/nix/store/") or not data["writeXmlDerivation"].endswith(".drv"):
        errors.append("writeXML did not produce a Nix derivation path")
    try:
        volume = ET.fromstring(data["generatedXml"])
        capacity = volume.find("capacity")
        if (volume.tag != "volume" or volume.findtext("name") != "fixture-volume"
                or capacity is None or capacity.attrib != {"unit": "MiB"}
                or capacity.text != "1"):
            errors.append("actual generated volume XML has the wrong contents")
    except ET.ParseError:
        errors.append("actual generated volume XML is malformed")
    return errors


def run(command):
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError("command failed: " + " ".join(command[:3]) + "\n" + result.stderr[-4000:])
    return result.stdout


def evaluate(directory, consumer):
    return json.loads(run([
        "nix-instantiate", "--eval", "--strict", "--json",
        "--option", "allow-import-from-derivation", "false",
        "--argstr", "fixture", str(directory), str(consumer),
    ]))


def verify_native():
    if not shutil.which("nix") or not shutil.which("nix-instantiate"):
        raise RuntimeError("Nix is required; this script does not install it")
    source = Path(__file__).resolve().parent
    committed_lock = source / "flake.lock"
    lock_before = committed_lock.read_bytes() if committed_lock.exists() else None
    with tempfile.TemporaryDirectory(prefix="nixvirt-input-") as temporary:
        root = Path(temporary)
        good, bad = root / "good", root / "without-follows"
        for directory in (good, bad):
            directory.mkdir()
            for filename in ("flake.nix", "default.nix"):
                shutil.copyfile(source / filename, directory / filename)
        if lock_before is not None:
            (good / "flake.lock").write_bytes(lock_before)
        nix_lock = [
            "nix", "--extra-experimental-features", "nix-command flakes",
            "--option", "allow-import-from-derivation", "false", "flake", "lock",
        ]
        lock_command = nix_lock.copy()
        if lock_before is not None:
            lock_command.append("--no-update-lock-file")
        run(lock_command + ["path:" + str(good)])
        locked_bytes = (good / "flake.lock").read_bytes()
        if lock_before is not None and locked_bytes != lock_before:
            raise RuntimeError("committed lock changed during lock validation")
        result = evaluate(good, source / "consumer.nix")
        errors = check_evidence(result)
        if errors:
            raise RuntimeError("good fixture failed: " + "; ".join(errors))
        repeated = evaluate(good, source / "consumer.nix")
        if repeated != result or (good / "flake.lock").read_bytes() != locked_bytes:
            raise RuntimeError("repeated evaluation changed the result or lock")

        # A new valid lock is essential: do not accidentally test a stale lock.
        text = (bad / "flake.nix").read_text()
        follows = '    inputs.nixpkgs.follows = "nixpkgs";\n'
        if text.count(follows) != 1:
            raise RuntimeError("expected exactly one follows declaration")
        (bad / "flake.nix").write_text(text.replace(follows, ""))
        run(nix_lock + ["path:" + str(bad)])
        bad_result = evaluate(bad, source / "consumer.nix")
        bad_errors = check_evidence(bad_result)
        if not bad_errors or not any("NixVirt nixpkgs" in error for error in bad_errors):
            raise RuntimeError("absent-follows control did not fail dependency acceptance")
        if bad_result["dependencyRevision"] != BASELINE_REV or bad_result["rootRevision"] != SELECTED_REV:
            raise RuntimeError("negative control did not preserve distinct valid pinned inputs")
        if committed_lock.exists() and committed_lock.read_bytes() != lock_before:
            raise RuntimeError("source lock was changed")
        return {
            "status": "PASS", "lockMode": "committed" if lock_before is not None else "bootstrap",
            "nativeResult": result, "repeatedEvaluationStable": True,
            "negativeControl": {"actualResult": bad_result, "acceptanceErrors": bad_errors},
            "lockSha256": hashlib.sha256(locked_bytes).hexdigest(),
            "generatedLock": json.loads(locked_bytes),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", type=Path, help="check an existing native-result JSON file")
    args = parser.parse_args()
    try:
        if args.check:
            errors = check_evidence(json.loads(args.check.read_text()))
            if errors:
                print("FAIL: " + "; ".join(errors), file=sys.stderr)
                return 1
            print("PASS: complete dependency and XML evidence")
        else:
            print(json.dumps(verify_native(), separators=(',', ':')))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print("FAIL: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
