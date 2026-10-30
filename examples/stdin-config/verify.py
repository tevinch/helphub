#!/usr/bin/env python3
"""Compile the example and check real file/stdin behavior with CLI11 headers."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

ENV_NAME = "CLI11_CONFIG_EXAMPLE_VALUE"
TRANSFORM = '->transform(CLI::Transformer({{"-", "/dev/stdin"}}))'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("include_dir", type=Path, help="CLI11 2.7.2 include directory")
    parser.add_argument("--compiler", default="c++")
    args = parser.parse_args()
    include_dir = args.include_dir.resolve()
    source = Path(__file__).with_name("example.cpp")
    clean_env = os.environ.copy()
    clean_env.pop(ENV_NAME, None)
    checks = 0

    with tempfile.TemporaryDirectory(prefix="stdin-config-") as directory:
        work = Path(directory)
        executable = work / "example"

        def compile_source(path, output):
            command = [args.compiler, "-std=c++11", "-Wall", "-Wextra", "-pedantic",
                       "-I", str(include_dir), str(path), "-o", str(output)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            assert result.returncode == 0, result.stderr
            assert not result.stderr.strip(), result.stderr

        compile_source(source, executable)

        def run(arguments=(), text="", value=None, program=executable):
            env = clean_env.copy()
            if value is not None:
                env[ENV_NAME] = str(value)
            return subprocess.run([str(program), *arguments], input=text, env=env,
                                  cwd=work, capture_output=True, text=True, timeout=5)

        def expect(label, arguments, text, value, wanted):
            nonlocal checks
            result = run(arguments, text, value)
            assert result.returncode == 0, (label, result.returncode, result.stderr)
            # The application callback prints one record. Check outside that callback
            # that it actually ran exactly once and produced the final values.
            lines = result.stdout.splitlines()
            assert len(lines) == 1, (label, lines)
            assert json.loads(lines[0]) == wanted, (label, lines, wanted)
            assert result.stderr == "", (label, result.stderr)
            checks += 1
            print("PASS", label)

        expect("defaults", [], "", None,
               {"value": 10, "config_only": 20, "untouched": 30})
        expect("environment fills absent config", [], "", 90,
               {"value": 90, "config_only": 20, "untouched": 30})
        config_text = "value=40\nconfig_only=41\n"
        config_file = work / "settings file.toml"
        config_file.write_text(config_text, encoding="utf-8")
        expected = {"value": 40, "config_only": 41, "untouched": 30}
        expect("named file beats environment", ["--config_file", str(config_file)],
               "", 90, expected)
        expect("literal stdin path beats environment", ["--config_file", "/dev/stdin"],
               config_text, 90, expected)
        expect("dash stdin beats environment", ["--config_file", "-"],
               config_text, 90, expected)
        cli_expected = {"value": 60, "config_only": 41, "untouched": 30}
        expect("CLI beats named file and environment",
               ["--config_file", str(config_file), "--value", "60"], "", 90, cli_expected)
        expect("CLI beats stdin and environment",
               ["--value", "60", "--config_file", "-"], config_text, 90, cli_expected)
        expect("environment fills a key absent from stdin",
               ["--config_file", "-"], "config_only=42\n", 90,
               {"value": 90, "config_only": 42, "untouched": 30})
        expect("fresh repeated stdin is consumed",
               ["--config_file", "-"], "value=43\nconfig_only=44\n", 90,
               {"value": 43, "config_only": 44, "untouched": 30})
        (work / "-").write_text("value=45\n", encoding="utf-8")
        expect("a path named dash remains a named file",
               ["--config_file", "./-"], "", 90,
               {"value": 45, "config_only": 20, "untouched": 30})

        for label, arguments, text, error_field in [
            ("CLI range validator", ["--value", "101"], "", "--value"),
            ("stdin range validator", ["--config_file", "-"], "value=101\n", "--value"),
            ("strict config extras", ["--config_file", "-"], "unknown_key=1\n", "unknown_key"),
            ("missing named file", ["--config_file", "missing.toml"], "", "missing.toml"),
        ]:
            result = run(arguments, text)
            assert result.returncode != 0, (label, result.stdout)
            assert result.stdout == "", (label, result.stdout)
            assert error_field in result.stderr, (label, result.stderr)
            checks += 1
            print("PASS", label)

        # Keep stdin open and send nothing: help must complete without reading it.
        process = subprocess.Popen([str(executable), "--config_file", "-", "--help"],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, env=clean_env, cwd=work)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise AssertionError("help waited for stdin")
        process.stdin.close()
        process.stdin = None
        stdout, stderr = process.communicate()
        assert process.returncode == 0 and "--config_file" in stdout, (stdout, stderr)
        assert stderr == "" and not any(line.startswith("{") for line in stdout.splitlines())
        checks += 1
        print("PASS help finishes with stdin still open")

        # Removing the essential mapping must make the same dash request fail.
        original = source.read_text(encoding="utf-8")
        assert original.count(TRANSFORM) == 1, "Cannot identify the single dash transform"
        negative_source = work / "without_dash.cpp"
        negative_source.write_text(original.replace(TRANSFORM, ""), encoding="utf-8")
        negative = work / "without_dash"
        compile_source(negative_source, negative)
        # A file named '-' exists in work, so use a separate empty cwd.
        empty = work / "empty"
        empty.mkdir()
        result = subprocess.run([str(negative), "--config_file", "-"],
                                input=config_text, env=clean_env, cwd=empty,
                                capture_output=True, text=True, timeout=5)
        assert result.returncode != 0 and result.stdout == "", result
        assert "-" in result.stderr, result.stderr
        checks += 1
        print("PASS omitted-transform negative rejects dash")

    print(f"{checks} checks passed")


if __name__ == "__main__":
    main()

