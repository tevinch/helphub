import argparse
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from packaging.specifiers import SpecifierSet


def main():
    parser = argparse.ArgumentParser(description="Run PDM with a verified local virtualenv.")
    parser.add_argument("python", type=Path, help="path to Python inside an existing virtualenv")
    parser.add_argument("command", choices=("install", "sync", "run"))
    parser.add_argument("program", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command == "run" and not args.program:
        parser.error("run needs a program")
    if args.command != "run" and args.program:
        parser.error("this example takes no additional install or sync options")

    project = Path.cwd()
    # Keep the virtualenv path intact when its executable is a symlink.
    python = args.python.absolute()
    if not python.is_file():
        parser.error(f"{python} does not exist")

    try:
        with (project / "pyproject.toml").open("rb") as file:
            requirement = tomllib.load(file)["project"].get("requires-python", "")
        specifier = SpecifierSet(requirement)
        probe = subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                "import json, platform, sys; "
                "print(json.dumps([platform.python_version(), sys.prefix != sys.base_prefix]))",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        version, in_venv = json.loads(probe.stdout)
    except (OSError, subprocess.CalledProcessError, KeyError, ValueError) as error:
        parser.error(f"could not verify the local Python and pyproject.toml: {error}")

    if not in_venv:
        parser.error(f"{python} is not in a virtual environment")
    if not specifier.contains(version, prereleases=True):
        parser.error(f"Python {version} does not satisfy requires-python {requirement!r}")

    environment = {
        **os.environ,
        "PDM_PYTHON": str(python),
        "PDM_PROJECT": str(project),
        "PDM_IGNORE_SAVED_PYTHON": "false",
        "PDM_USE_VENV": "true",
    }
    command = [sys.executable, "-m", "pdm", args.command]
    if args.command == "run":
        command.extend(["--", *args.program])
    return subprocess.run(command, env=environment).returncode


if __name__ == "__main__":
    raise SystemExit(main())
