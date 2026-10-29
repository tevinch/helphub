"""Acceptance checks against the real Backsub command, with synthetic pixels."""

import csv
from importlib.metadata import version
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import tifffile


def run_case(root, mode):
    case = root / mode
    fixture = subprocess.run([
        sys.executable, str(Path(__file__).with_name("make_fixture.py")),
        "--out", str(case), "--names", mode,
    ], text=True, capture_output=True, timeout=15)
    if fixture.returncode:
        raise AssertionError(f"Fixture exited {fixture.returncode}\n{fixture.stdout}\n{fixture.stderr}")
    result = subprocess.run([
        sys.executable, "-m", "backsub", "--input", str(case / "input.tif"),
        "--output", str(case / "output.ome.tif"), "--markers", str(case / "markers.csv"),
        "--marker-output", str(case / "output.csv"), "--pixel-size", "1",
        "--tile-size", "16", "--compression", "none",
    ], text=True, capture_output=True, timeout=45)
    if result.returncode:
        raise AssertionError(f"Backsub exited {result.returncode}\n{result.stdout}\n{result.stderr}")
    with tifffile.TiffFile(case / "output.ome.tif") as image:
        values = image.series[0].asarray()
        xml = ET.fromstring(image.ome_metadata)
        levels = [level.shape for level in image.series[0].levels]
    with (case / "output.csv").open(newline="") as stream:
        markers = list(csv.DictReader(stream))
    return result, values, xml, levels, markers


class MarkerNameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.cases = {
            mode: run_case(Path(cls.directory.name), mode)
            for mode in ("unique", "duplicate-dapi", "ambiguous-background")
        }

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_released_backsub_version(self):
        self.assertEqual(version("backsub"), "0.5.2")

    def test_each_cycle_uses_its_own_background(self):
        result, values, _, levels, _ = self.cases["unique"]
        expected = np.broadcast_to(np.array([10, 14, 80, 73])[:, None, None], (4, 32, 32))
        np.testing.assert_array_equal(values, expected)
        self.assertEqual(values.dtype, np.uint16)
        self.assertEqual(levels, [(4, 32, 32), (4, 16, 16)])
        self.assertNotIn("Only the first occurrence", result.stdout)

    def test_output_csv_and_ome_match_the_retained_planes(self):
        _, _, xml, _, markers = self.cases["unique"]
        expected_names = ["DAPI_001", "Signal_001", "DAPI_002", "Signal_002"]
        channels = xml.findall(".//{*}Channel")
        pixels = xml.find(".//{*}Pixels")
        self.assertEqual(pixels.get("SizeC"), "4")
        self.assertEqual([channel.get("Name") for channel in channels], expected_names)
        self.assertEqual(len({channel.get("ID") for channel in channels}), 4)
        self.assertEqual([row["marker_name"] for row in markers], expected_names)
        self.assertEqual([row["channel_number"] for row in markers], ["1", "2", "3", "4"])
        self.assertEqual([row["cycle_number"] for row in markers], ["1", "1", "2", "2"])
        self.assertEqual([row["exposure"] for row in markers], ["60", "20", "60", "30"])
        self.assertEqual(
            [row["background"] for row in markers], ["", "bg_001_signal", "", "bg_002_signal"],
        )

    def test_duplicate_dapi_rows_stay_distinct_but_unique_labels_preserve_pixels(self):
        _, values, xml, _, markers = self.cases["duplicate-dapi"]
        np.testing.assert_array_equal(values, self.cases["unique"][1])
        self.assertEqual(int(values[0, 0, 0]), 10)
        self.assertEqual(int(values[2, 0, 0]), 80)
        expected_names = ["DAPI", "Signal_001", "DAPI", "Signal_002"]
        self.assertEqual([row["marker_name"] for row in markers], expected_names)
        channels = xml.findall(".//{*}Channel")
        self.assertEqual([channel.get("Name") for channel in channels], expected_names)
        self.assertEqual(len({channel.get("ID") for channel in channels}), 4)

    def test_ambiguous_background_warns_and_uses_the_first_row(self):
        result, values, _, _, _ = self.cases["ambiguous-background"]
        self.assertEqual(result.stdout.count("Only the first occurrence will be used"), 2)
        np.testing.assert_array_equal(values[:, 0, 0], [10, 14, 80, 91])
        self.assertEqual(int(self.cases["unique"][1][3, 0, 0]), 73)


if __name__ == "__main__":
    unittest.main()
