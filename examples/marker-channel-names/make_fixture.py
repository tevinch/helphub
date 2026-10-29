"""Write a small two-cycle TIFF and its marker table for Backsub."""

import argparse
import csv
from pathlib import Path

import numpy as np
import tifffile


def write_fixture(directory: Path, names: str = "unique") -> None:
    if names not in {"unique", "duplicate-dapi", "ambiguous-background"}:
        raise ValueError(f"Unknown name layout: {names}")
    directory.mkdir(parents=True, exist_ok=True)
    if any((directory / name).exists() for name in ("input.tif", "markers.csv")):
        raise FileExistsError("Choose an empty output directory for the fixture")

    rows = []
    for cycle, signal_exposure in ((1, 20), (2, 30)):
        background = f"bg_{cycle:03d}_signal"
        if names == "ambiguous-background":
            background = "bg_signal"
        reference = "DAPI" if names == "duplicate-dapi" else f"DAPI_{cycle:03d}"
        rows.extend([
            [cycle, f"bg_{cycle:03d}_DAPI", "", 60, "TRUE"],
            [cycle, background, "", 10, "TRUE"],
            [cycle, reference, "", 60, ""],
            [cycle, f"Signal_{cycle:03d}", background, signal_exposure, ""],
        ])

    with (directory / "markers.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([
            "channel_number", "cycle_number", "marker_name", "background", "exposure", "remove",
        ])
        for number, row in enumerate(rows, start=1):
            writer.writerow([number, *row])

    image = np.stack([
        np.full((32, 32), value, dtype=np.uint16)
        for value in (1, 3, 10, 20, 2, 9, 80, 100)
    ])
    tifffile.imwrite(
        directory / "input.tif", image,
        photometric="minisblack", metadata={"axes": "CYX"},
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--names", choices=("unique", "duplicate-dapi", "ambiguous-background"), default="unique",
    )
    arguments = parser.parse_args()
    write_fixture(arguments.out, arguments.names)
