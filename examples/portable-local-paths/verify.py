"""Native checks for checkout-derived local deployment paths."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time


PHAR_SHA256 = "0026dfa73626a8ccde06222fe5fccf03e6d4a19e765914bb87d7d2cc21f3e57d"
SOURCE = Path(__file__).resolve().parent
FLOOR_BYTES = 1024**3


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(command: list[str], cwd: Path, work: Path, label: str) -> tuple[int, str]:
    require(cwd.resolve().is_relative_to(work), "command cwd escaped the task tree")
    require(shutil.disk_usage(work).free >= FLOOR_BYTES, "disk floor before command")
    log = work / f"{label}.log"
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(work / "home"),
        "TMPDIR": str(work / "tmp"), "LANG": "C.UTF-8",
        "DO_NOT_TRACK": "true", "DO_NOT_SHOW_BANNER": "true",
    }
    started = time.monotonic()
    stopped = None
    with log.open("w") as output:
        process = subprocess.Popen(
            command, cwd=cwd, env=env, stdout=output,
            stderr=subprocess.STDOUT, start_new_session=True,
        )
        try:
            while process.poll() is None:
                if shutil.disk_usage(work).free < FLOOR_BYTES:
                    stopped = "disk floor"
                    break
                if time.monotonic() - started > 90:
                    stopped = "command timeout"
                    break
                time.sleep(0.2)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
    text = log.read_text()
    print(json.dumps({
        "label": label, "command": command, "cwd": str(cwd),
        "exit_code": process.returncode, "resource_stop": stopped,
        "output_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        "free_bytes_after": shutil.disk_usage(work).free,
    }), flush=True)
    print(text, flush=True)
    require(stopped is None, f"resource stop: {stopped}")
    return process.returncode, text


def command(php: str, phar: Path, root: Path, task: str, entry: str) -> list[str]:
    return [php, str(phar), "--file", str(root / ".paas" / entry),
            task, "testdeploy", "--no-ansi", "--no-interaction", "-vvv"]


def config_hashes(root: Path) -> dict[str, str]:
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in (".paas/deploy.php", ".paas/deploy.maml")}


def inspect_paths(output: str, root: Path, require_magento: bool) -> None:
    results = []
    decoder = json.JSONDecoder()
    for line in output.splitlines():
        start = line.find('{"task":"paths:show"')
        if start >= 0:
            value, _ = decoder.raw_decode(line[start:])
            results.append(value)
    require(len(results) == 1, "native path task must emit exactly one result")
    result = results[0]
    require(set(result) == {"task", "deploy_path", "current_path", "recipes"}
            and result["task"] == "paths:show"
            and result["deploy_path"] == str(root / "testdeploy")
            and result["current_path"] == str(root / "testdeploy/public_html"),
            "native paths are not anchored to this checkout")
    require(isinstance(result["recipes"], list) and "common" in result["recipes"],
            "native common recipe marker missing")
    if require_magento:
        require("magento2" in result["recipes"], "native Magento recipe marker missing")
    else:
        require("magento2" not in result["recipes"], "filesystem fixture imported Magento")


def path_task(php: str, phar: Path, root: Path, cwd: Path, work: Path,
              label: str, magento: bool) -> None:
    code, output = run(command(php, phar, root, "paths:show", "deploy.php"), cwd, work, label)
    require(code == 0, "native path-inspection task failed")
    inspect_paths(output, root, magento)


def no_deployment(root: Path) -> None:
    require(not (root / "testdeploy").exists()
            and not (root / ".paas/testdeploy").exists(),
            "configuration inspection created a deployment")


def artifact(root: Path, content: bytes) -> None:
    destination = root / "artifacts/payload.tar.gz"
    destination.parent.mkdir(exist_ok=True)
    member = tarfile.TarInfo("payload.txt")
    member.size, member.mode, member.mtime = len(content), 0o644, 0
    with tarfile.open(destination, "w:gz") as archive:
        archive.addfile(member, io.BytesIO(content))


def current(root: Path, release: str, content: bytes) -> None:
    deployment = root / "testdeploy"
    link = deployment / "public_html"
    require(link.is_symlink(), "current_path is not a native published symlink")
    require(link.resolve(strict=True) == deployment / "releases" / release,
            "current_path does not resolve to the expected release")
    require((link / "payload.txt").read_bytes() == content, "published payload differs")
    require((deployment / ".dep/latest_release").read_text().strip() == release,
            "native release counter differs")
    require(not (deployment / "release").exists() and not (deployment / "release").is_symlink(),
            "unfinished native release link remains")
    require(not (deployment / "testdeploy").exists()
            and not (root / ".paas/testdeploy").exists(),
            "relative-path deployment directory appeared")


def main() -> None:
    require(len(sys.argv) == 2, "usage: verify.py /absolute/path/to/deployer.phar")
    phar = Path(sys.argv[1]).resolve(strict=True)
    require(hashlib.sha256(phar.read_bytes()).hexdigest() == PHAR_SHA256,
            "release PHAR digest differs")
    php = shutil.which("php")
    require(php is not None, "preinstalled PHP is unavailable")
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="portable-path-", dir=runner_temp) as name:
        work = Path(name).resolve()
        require(work.parent == runner_temp and work.name.startswith("portable-path-"),
                "unsafe task temporary directory")
        for folder in ("home", "tmp", "unrelated", "relocated"):
            (work / folder).mkdir()
        code, output = run([php, "-r", (
            "echo json_encode(['php'=>PHP_VERSION,"
            "'tracking'=>getenv('DO_NOT_TRACK'),'banner'=>getenv('DO_NOT_SHOW_BANNER')]);"
        )], work, work, "runtime-settings")
        require(code == 0, "task PHP configuration did not start")
        settings = json.loads(output)
        require(settings["tracking"] == "true" and settings["banner"] == "true",
                "supported telemetry/banner switches were not applied")

        # Actual Magento recipe, but only configuration inspection: no application task.
        magento = work / "magento-a"
        shutil.copytree(SOURCE / "magento-paths", magento)
        magento_hashes = config_hashes(magento)
        path_task(php, phar, magento, magento, work, "magento-root-paths", True)
        no_deployment(magento)
        moved_magento = work / "relocated/magento-b"
        magento.rename(moved_magento)
        require(not magento.exists(), "Magento-mode checkout was copied rather than moved")
        require(config_hashes(moved_magento) == magento_hashes,
                "Magento-mode checked-in configuration changed on relocation")
        path_task(php, phar, moved_magento, work / "unrelated", work, "magento-moved-paths", True)
        no_deployment(moved_magento)

        omitted_recipe = work / "omitted-magento-import"
        shutil.copytree(SOURCE / "magento-paths", omitted_recipe)
        maml = omitted_recipe / ".paas/deploy.maml"
        original = maml.read_text()
        recipe = 'import: "recipe/magento2.php"'
        require(original.count(recipe) == 1, "omitted-recipe control is ambiguous")
        maml.write_text(original.replace(recipe, 'import: "recipe/common.php"'))
        code, output = run(command(php, phar, omitted_recipe, "paths:show", "deploy.php"),
                           work / "unrelated", work, "omitted-magento-import")
        require(code == 0, "omitted-recipe path task did not run")
        try:
            inspect_paths(output, omitted_recipe, True)
        except AssertionError as error:
            require(str(error) == "native Magento recipe marker missing",
                    "omitted-recipe control failed for a different reason")
        else:
            raise AssertionError("omitting the Magento recipe was not rejected")
        no_deployment(omitted_recipe)
        print("EXPECTED_OMITTED_MAGENTO_IMPORT_REJECTION", flush=True)

        omitted_anchor = work / "omitted-anchor"
        shutil.copytree(SOURCE / "magento-paths", omitted_anchor)
        entry = omitted_anchor / ".paas/deploy.php"
        original = entry.read_text()
        anchor = "set('checkout_root', dirname(__DIR__));"
        require(original.count(anchor) == 1, "omitted-anchor control is ambiguous")
        entry.write_text(original.replace(anchor, "// Anchor omitted for this negative control."))
        code, output = run(command(php, phar, omitted_anchor, "paths:show", "deploy.php"),
                           work / "unrelated", work, "omitted-anchor")
        require(code != 0 and 'Config option "checkout_root" does not exist.' in output,
                "missing anchor was not rejected by native configuration evaluation")
        no_deployment(omitted_anchor)
        print("EXPECTED_MISSING_ANCHOR_FAILURE", flush=True)

        # Separate common-recipe filesystem publication with an inert, owned artifact.
        checkout = work / "checkout-a"
        shutil.copytree(SOURCE / "fixture", checkout)
        fixture_hashes = config_hashes(checkout)
        path_task(php, phar, checkout, checkout / ".paas", work, "common-config-dir-paths", False)
        artifact(checkout, b"release-one\n")
        code, _ = run(command(php, phar, checkout, "paths:publish", "deploy.php"),
                      checkout, work, "publish-one-root")
        require(code == 0, "first native artifact publication failed")
        current(checkout, "1", b"release-one\n")
        print("FIRST_NATIVE_ARTIFACT_PUBLICATION_VERIFIED", flush=True)

        moved = work / "relocated/checkout-b"
        checkout.rename(moved)
        require(not checkout.exists(), "filesystem checkout was copied rather than moved")
        require(config_hashes(moved) == fixture_hashes,
                "checked-in configuration changed on physical relocation")
        current(moved, "1", b"release-one\n")
        path_task(php, phar, moved, work / "unrelated", work, "common-moved-paths", False)
        artifact(moved, b"release-two\n")
        code, _ = run(command(php, phar, moved, "paths:publish", "deploy.php"),
                      work / "unrelated", work, "publish-two-unrelated-cwd")
        require(code == 0, "second native artifact publication failed")
        current(moved, "2", b"release-two\n")
        require((moved / "testdeploy/releases/1/payload.txt").read_bytes() == b"release-one\n",
                "previous release content changed")
        history = [json.loads(line) for line in
                   (moved / "testdeploy/.dep/releases_log").read_text().splitlines()]
        require([item["release_name"] for item in history] == ["1", "2"],
                "native release history did not advance twice")
        require(config_hashes(moved) == fixture_hashes,
                "checked-in configuration changed during publication")
        for path in (moved / "testdeploy").rglob("*"):
            if path.is_symlink():
                require(path.resolve(strict=True).is_relative_to(moved),
                        "a symlink escaped the relocated checkout")
        print("RELOCATED_REPEATED_NATIVE_ARTIFACT_PUBLICATION_VERIFIED", flush=True)

        missing = work / "missing-artifact"
        shutil.copytree(SOURCE / "fixture", missing)
        require(not (missing / "artifacts/payload.tar.gz").exists(),
                "missing-artifact control unexpectedly has an archive")
        code, output = run(command(php, phar, missing, "paths:publish", "deploy.php"),
                           work / "unrelated", work, "missing-artifact")
        upload_error = any("rsync:" in line and "No such file or directory" in line
                           for line in output.splitlines())
        require(code != 0 and "task paths:unpack" in output and upload_error
                and (missing / "testdeploy/releases/1").is_dir(),
                "missing artifact did not fail the actual native upload step")
        require(not (missing / "testdeploy/public_html").exists()
                and not (missing / "testdeploy/public_html").is_symlink(),
                "missing-artifact control published current_path")
        print("EXPECTED_MISSING_ARTIFACT_FAILURE", flush=True)
        print(json.dumps({
            "result": "NATIVE_PORTABLE_PATHS_VERIFIED",
            "php": settings["php"],
            "magento_mode": "native configuration inspection only; no application lifecycle",
            "filesystem_mode": "common recipe, two inert-artifact publications and physical relocation",
            "fixture_configuration_sha256": fixture_hashes,
            "magento_configuration_sha256": magento_hashes,
            "scope": "Linux filesystem/configuration; no original Magento/Docker/cron or cross-OS claim",
        }), flush=True)


if __name__ == "__main__":
    main()
