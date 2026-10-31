"""Native relative-path baseline; successful publication is the required contract."""

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


def relative_link_failure(output: str, checkout: Path) -> bool:
    release_link = checkout / ".paas/testdeploy/release"
    link_diagnostic = any(
        "ln:" in line and "testdeploy/release" in line
        and "No such file or directory" in line
        for line in output.splitlines()
    )
    return (
        "deploy:release" in output and link_diagnostic
        and (checkout / ".paas/testdeploy/releases/1").is_dir()
        and not release_link.exists() and not release_link.is_symlink()
    )


def relative_cwd_failure(output: str, checkout: Path) -> bool:
    root_deployment = checkout / "testdeploy"
    return (
        'The provided cwd "testdeploy" does not exist.' in output
        and "recipe/deploy/release.php(87)" in output
        and "task deploy:release" in output
        and (checkout / ".paas/testdeploy").is_dir()
        and not root_deployment.exists() and not root_deployment.is_symlink()
    )


def inspect_magento_paths(output: str) -> None:
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
            and result["task"] == "paths:show" and result["deploy_path"] == "testdeploy"
            and result["current_path"] == "public_html",
            "baseline native task did not evaluate the original relative settings")
    require(isinstance(result["recipes"], list) and "common" in result["recipes"],
            "native common recipe marker missing")
    require("magento2" in result["recipes"], "native Magento recipe marker missing")


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
        for folder in ("home", "tmp"):
            (work / folder).mkdir()
        code, output = run([php, "-r", (
            "echo json_encode(['php'=>PHP_VERSION,"
            "'tracking'=>getenv('DO_NOT_TRACK'),'banner'=>getenv('DO_NOT_SHOW_BANNER')]);"
        )], work, work, "runtime-settings")
        require(code == 0, "task PHP configuration did not start")
        settings = json.loads(output)
        require(settings["tracking"] == "true" and settings["banner"] == "true",
                "supported telemetry/banner switches were not applied")

        # Actual Magento import, but only a safe native configuration task runs.
        magento = work / "magento-paths"
        shutil.copytree(SOURCE / "magento-paths", magento)
        code, output = run(command(php, phar, magento, "paths:show", "deploy.php"),
                           magento, work, "magento-paths")
        require(code == 0, "SETUP_BLOCKED: native Magento path task failed")
        inspect_magento_paths(output)
        require(not (magento / "testdeploy").exists()
                and not (magento / ".paas/testdeploy").exists(),
                "path inspection ran a deployment lifecycle")

        omitted = work / "omitted-magento-import"
        shutil.copytree(SOURCE / "magento-paths", omitted)
        maml = omitted / ".paas/deploy.maml"
        original = maml.read_text()
        recipe = 'import: "recipe/magento2.php"'
        require(original.count(recipe) == 1, "omitted-recipe control is ambiguous")
        maml.write_text(original.replace(recipe, 'import: "recipe/common.php"'))
        code, output = run(command(php, phar, omitted, "paths:show", "deploy.php"),
                           omitted, work, "omitted-magento-import")
        require(code == 0, "SETUP_BLOCKED: omitted-recipe path task did not run")
        try:
            inspect_magento_paths(output)
        except AssertionError as error:
            require(str(error) == "native Magento recipe marker missing",
                    "omitted-recipe control failed for a different reason")
        else:
            raise AssertionError("omitting the Magento recipe was not rejected")
        require(not (omitted / "testdeploy").exists()
                and not (omitted / ".paas/testdeploy").exists(),
                "omitted-recipe inspection ran a deployment lifecycle")
        print("EXPECTED_OMITTED_MAGENTO_IMPORT_REJECTION", flush=True)

        # Fresh identical configurations isolate the invocation cwd as a diagnostic.
        # Changing cwd is not the proposed consumer configuration fix.
        config_bytes = (SOURCE / "fixture/.paas/deploy.maml").read_bytes()
        content = b"release-one\n"
        for invocation in ("root", "config-dir"):
            checkout = work / f"checkout-{invocation}"
            shutil.copytree(SOURCE / "fixture", checkout)
            require((checkout / ".paas/deploy.maml").read_bytes() == config_bytes,
                    "diagnostic configuration bytes changed")
            artifact_dir = checkout / ".paas/artifacts"
            artifact_dir.mkdir()
            member = tarfile.TarInfo("payload.txt")
            member.size, member.mode, member.mtime = len(content), 0o644, 0
            with tarfile.open(artifact_dir / "payload.tar.gz", "w:gz") as archive:
                archive.addfile(member, io.BytesIO(content))
            cwd = checkout if invocation == "root" else checkout / ".paas"
            code, output = run(command(php, phar, checkout, "paths:publish", "deploy.maml"),
                               cwd, work, f"native-relative-{invocation}")
            if invocation == "root":
                cwd_variant = code != 0 and relative_cwd_failure(output, checkout)
                print(json.dumps({
                    "phase": "native-relative-root",
                    "classification": "NATIVE_RELATIVE_CWD_FAILURE" if cwd_variant
                                      else "SETUP_OR_UNEXPECTED_FAILURE",
                    "native_exit_code": code,
                    "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
                }), flush=True)
                require(cwd_variant, "root invocation did not reproduce the observed native cwd failure")
                continue
            if code != 0:
                behavior_red = relative_link_failure(output, checkout)
                print(json.dumps({
                    "phase": "native-relative-config-dir",
                    "classification": "BEHAVIOR_RED_NATIVE_RELATIVE_LINK" if behavior_red
                                      else "SETUP_OR_UNEXPECTED_FAILURE",
                    "native_exit_code": code,
                    "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
                }), flush=True)
                require(behavior_red, "config-dir invocation did not reach the native relative-link failure")
        require(code == 0, "portable-path contract: native artifact publication must complete")
        current = checkout / "testdeploy/public_html"
        require(current.is_symlink(), "portable-path contract: current link must be inside the checkout")
        require(current.resolve(strict=True) == checkout / "testdeploy/releases/1",
                "portable-path contract: current must resolve to its native release")
        require((current / "payload.txt").read_bytes() == content,
                "portable-path contract: published artifact content must be readable")
        raise AssertionError("Baseline unexpectedly passed; reassess before any GREEN proposal")


if __name__ == "__main__":
    main()
