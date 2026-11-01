#!/usr/bin/env python3
"""Run the complete example on a native x86_64 GNU/Linux host."""

import json
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
import unittest


TARGET = "x86_64-unknown-linux-gnu"
EXPECTED = b"Hello from no_std and libc.\n"
SENTINEL = "rust_panic_is_reachable_in_this_build"
SOURCE = Path(__file__).resolve().parent


def without_core_dumps():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


class NativeWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="libc example ")
        cls.base = Path(cls.scratch.name)
        cls.environment = os.environ.copy()
        for key in (
            "RUSTFLAGS",
            "CARGO_ENCODED_RUSTFLAGS",
            "CARGO_BUILD_RUSTFLAGS",
            "CARGO_BUILD_TARGET",
            "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUSTFLAGS",
        ):
            cls.environment.pop(key, None)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def copy(self, name):
        destination = self.base / name
        shutil.copytree(
            SOURCE,
            destination,
            ignore=shutil.ignore_patterns("target", "__pycache__", ".git"),
        )
        return destination

    def command(self, argv, directory, environment=None):
        env = self.environment.copy()
        env["CARGO_TARGET_DIR"] = str(directory / "target")
        if environment:
            env.update(environment)
        return subprocess.run(
            argv,
            cwd=directory,
            env=env,
            capture_output=True,
            timeout=120,
            preexec_fn=without_core_dumps,
        )

    def build(self, directory, profile="release", features=None):
        argv = ["cargo", "build", "--locked", "--target", TARGET, "--message-format=json"]
        if profile == "release":
            argv.append("--release")
        if features:
            argv.extend(["--features", features])
        result = self.command(argv, directory)
        messages = []
        for line in result.stdout.splitlines():
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return result, messages

    def assert_success(self, result):
        self.assertEqual(
            result.returncode,
            0,
            (result.stdout + result.stderr).decode(errors="replace"),
        )

    def assert_host_scripts_ran(self, messages):
        for package in ("libc", "linux-libc-entry"):
            scripts = [
                message for message in messages
                if message.get("reason") == "build-script-executed"
                and message.get("package_id", "").split("#")[-1].split("@")[0] == package
            ]
            self.assertEqual(len(scripts), 1, f"missing {package} build-script execution")
            out = Path(scripts[0]["out_dir"])
            self.assertTrue(out.is_dir())
            self.assertTrue((out.parent / "output").read_text().strip())
            if package == "linux-libc-entry":
                witness = json.loads((out / "host-script.json").read_text())
                self.assertEqual(witness, {"host": TARGET, "target": TARGET})

    def test_01_original_missing_c_link_fails(self):
        directory = self.copy("missing native link")
        manifest = directory / "Cargo.toml"
        manifest.write_text(manifest.read_text().replace("default-features = false", "default-features = true"))
        (directory / "src/main.rs").write_text('''#![no_std]
#![no_main]
#[unsafe(no_mangle)]
pub extern "C" fn _start() -> ! { unsafe { libc::exit(0) } }
#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! { loop {} }
''')
        result, messages = self.build(directory)
        self.assertNotEqual(result.returncode, 0, "the missing-link control unexpectedly built")
        diagnostics = (result.stdout + result.stderr).decode(errors="replace")
        self.assertRegex(diagnostics, r"undefined (?:symbol: |reference to .?)exit")
        self.assert_host_scripts_ran(messages)

    def test_02_global_startup_flags_break_host_script(self):
        directory = self.copy("global flags")
        (directory / ".cargo/config.toml").write_text("")
        result = self.command(
            ["cargo", "build", "--release", "--locked"],
            directory,
            {"RUSTFLAGS": "-C link-arg=-nostartfiles"},
        )
        self.assertNotEqual(result.returncode, 0)
        diagnostics = (result.stdout + result.stderr).decode(errors="replace")
        self.assertIn("failed to run custom build command", diagnostics)
        self.assertRegex(diagnostics, r"signal: (?:11|4)|SIGSEGV|SIGILL")

    def test_03_correct_debug_and_release_run_repeatedly(self):
        directory = self.copy("working program")
        for profile in ("debug", "release"):
            with self.subTest(profile=profile):
                result, messages = self.build(directory, profile=profile)
                self.assert_success(result)
                self.assert_host_scripts_ran(messages)
                binary = directory / "target" / TARGET / profile / "linux-libc-entry"
                for _ in range(3):
                    run = self.command([str(binary)], directory)
                    self.assert_success(run)
                    self.assertEqual(run.stdout, EXPECTED)
                    self.assertEqual(run.stderr, b"")

                elf = self.command(["readelf", "-d", str(binary)], directory)
                self.assert_success(elf)
                self.assertIn(b"libc.so.6", elf.stdout)
                symbols = self.command(["nm", "-u", str(binary)], directory)
                self.assert_success(symbols)
                self.assertNotIn(SENTINEL.encode(), symbols.stdout)
                self.assertRegex(symbols.stdout.decode(), r"\bwrite@")
                self.assertRegex(symbols.stdout.decode(), r"\b_exit@")
                header = self.command(["readelf", "-h", str(binary)], directory)
                self.assert_success(header)
                names = self.command(["nm", "-n", str(binary)], directory)
                self.assert_success(names)
                import re
                entry = re.search(rb"Entry point address:\s+(0x[0-9a-f]+)", header.stdout)
                start = re.search(rb"^([0-9a-f]+)\s+T\s+_start$", names.stdout, re.MULTILINE)
                self.assertIsNotNone(entry)
                self.assertIsNotNone(start)
                self.assertEqual(int(entry[1], 16), int(start[1], 16))

                with open("/dev/full", "wb") as full:
                    failed_output = subprocess.run(
                        [str(binary)], stdout=full, stderr=subprocess.PIPE,
                        timeout=10, preexec_fn=without_core_dumps,
                    )
                self.assertEqual(failed_output.returncode, 1)
                self.assertEqual(failed_output.stderr, b"")

    def test_04_reachable_panic_cannot_link(self):
        directory = self.copy("reachable panic")
        for profile in ("debug", "release"):
            with self.subTest(profile=profile):
                result, _ = self.build(directory, profile=profile, features="panic-probe")
                self.assertNotEqual(result.returncode, 0, "reachable Rust panic unexpectedly linked")
                self.assertIn(SENTINEL.encode(), result.stdout + result.stderr)


if __name__ == "__main__":
    if platform.system() != "Linux" or platform.machine() != "x86_64" or platform.libc_ver()[0] != "glibc":
        raise SystemExit("This check requires native x86_64 GNU/Linux with glibc.")
    print(platform.platform(), flush=True)
    subprocess.run(["rustc", "--version"], check=True)
    subprocess.run(["cargo", "--version"], check=True)
    unittest.main(verbosity=2)
