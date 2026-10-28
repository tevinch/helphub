"""Prepare, verify and use one immutable official English model snapshot."""

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import tempfile


LOCK = json.loads(Path(__file__).with_name("snapshot.json").read_text())


def verify(directory):
    """Reject missing or changed assets before a model is loaded."""
    directory = Path(directory)
    for name, expected in LOCK["files"].items():
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing file or symlink: {name}")
        data = path.read_bytes()
        if len(data) != expected["size"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ValueError(f"Snapshot does not match: {name}")
    resources = json.loads((directory / "resources.json").read_bytes())
    for processor, name in LOCK["processors"].items():
        data = (directory / "en" / processor / (name + ".pt")).read_bytes()
        if hashlib.md5(data).hexdigest() != resources["en"][processor][name]["md5"]:
            raise ValueError(f"Resource MD5 does not match: {processor}/{name}")


def require_version():
    if version("stanza") != LOCK["stanza_version"]:
        raise ValueError(f"This example requires stanza=={LOCK['stanza_version']}")


def prepare(directory):
    """Download with native Stanza parameters into a new directory."""
    directory = Path(directory)
    if directory.exists() or directory.is_symlink():
        raise FileExistsError(f"Choose a new destination: {directory}")
    if not directory.parent.is_dir():
        raise FileNotFoundError(f"Parent directory does not exist: {directory.parent}")
    require_version()
    import stanza
    with tempfile.TemporaryDirectory(prefix="model-snapshot-", dir=directory.parent) as tmp:
        staged = Path(tmp) / "models"
        downloaded = stanza.download(
            LOCK["language"], model_dir=str(staged), package=None,
            processors=LOCK["processors"].copy(),
            resources_version=LOCK["resources_version"],
            resources_url="https://raw.githubusercontent.com/stanfordnlp/stanza-resources/" + LOCK["resources_commit"],
            model_url="https://huggingface.co/stanfordnlp/stanza-en/resolve/" + LOCK["model_commit"] + "/models/{filename}",
        )
        if {tuple(item) for item in downloaded} != set(LOCK["processors"].items()):
            raise ValueError("The downloaded processor list differs from the snapshot")
        verify(staged)
        staged.rename(directory)


def run(directory, text):
    """Verify bytes first, then run the local CPU pipeline without downloads."""
    verify(directory)
    require_version()
    import stanza
    pipeline = stanza.Pipeline(
        lang=LOCK["language"], dir=str(directory), package=None,
        processors=LOCK["processors"].copy(), download_method=None,
        use_gpu=False, verbose=False,
    )
    if set(pipeline.processors) != set(LOCK["processors"]):
        raise ValueError("The active processors differ from the snapshot")
    document = pipeline(text)
    return [[token.text for token in sentence.tokens] for sentence in document.sentences]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "verify", "run"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--text", default="A small test. Another sentence!")
    args = parser.parse_args()
    try:
        if args.operation == "prepare":
            prepare(args.directory)
            print("Prepared and verified the fixed model snapshot.")
        elif args.operation == "verify":
            verify(args.directory)
            print("All three snapshot files match.")
        else:
            print(json.dumps(run(args.directory, args.text), ensure_ascii=False))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
