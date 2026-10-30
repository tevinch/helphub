"""Check real Seaborn artists and render the included synthetic fixture."""

import copy
import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn.objects as so

from example import make_plot, synthetic_data


def original_layers(background, observed, theme):
    return (
        so.Plot(background, x="age", y="overall_connectance", color="age_map")
        .add(so.Dot(alpha=0.2, pointsize=2), so.Jitter(), so.Dodge())
        .add(so.Dot(marker="*", pointsize=8), so.Dodge(), data=observed)
        .label(x="Carcass Years Post-Mortem", y="Overall Network Connectance", color="")
        .scale(color=so.Nominal(order=["Off", "On"]))
        .theme(theme)
    )


def render(plot):
    # Read compiled Matplotlib artists only in this verification script.
    compiled = plot.layout(size=(9, 5)).plot()
    figure = compiled._figure
    figure.canvas.draw()
    return figure, figure.axes[0]


def assert_alignment(axes, observed, labels):
    assert len(axes.collections) == 2, "both original point layers must run"
    stars = axes.collections[1].get_offsets()
    assert len(stars) == len(observed) == 6, "all observed points must be drawn"
    assert len(axes.texts) == len(labels) == 6, "all six supplied labels must be drawn"
    artists = {text.get_text(): text for text in axes.texts}
    assert set(artists) == set(labels.pvalue), "use the text mapping for supplied labels"
    for row in labels.itertuples():
        value = observed.loc[
            (observed.age == row.age) & (observed.age_map == row.age_map),
            "overall_connectance",
        ].item()
        # Fixture values are unique, so each y identifies one independently drawn star.
        star = stars[np.isclose(stars[:, 1], value)]
        assert len(star) == 1, "each annotation must have an independent observed point"
        text = artists[row.pvalue]
        assert not text.get_clip_on(), "labels at the plot boundary must remain visible"
        x, y = text.get_position()
        assert np.isclose(x, star[0, 0]), f"label x must match its dodged star: {row.pvalue}"
        assert np.isclose(y, row.yloc), "supplied annotation height must be preserved"
        rgba = colors.to_rgba(text.get_color())
        assert rgba[0] == rgba[1] == rgba[2] < 0.3 and rgba[3] == 1.0, "labels use dark k text, not the group palette"


class NativePlotChecks(unittest.TestCase):
    def setUp(self):
        self.frames = synthetic_data()
        self.before = [frame.copy(deep=True) for frame in self.frames]
        self.theme = {"axes.spines.top": False, "axes.spines.right": False}
        self.theme_before = copy.deepcopy(self.theme)

    def tearDown(self):
        for actual, expected in zip(self.frames, self.before):
            pd.testing.assert_frame_equal(actual, expected)
        self.assertEqual(self.theme, self.theme_before)
        plt.close("all")

    def test_full_plot_preservation_and_repeated_render(self):
        background, observed, labels = self.frames
        _, base_axes = render(original_layers(background, observed, self.theme))
        self.assertEqual([len(c.get_offsets()) for c in base_axes.collections], [24, 6])
        base_stars = base_axes.collections[1].get_offsets().copy()
        base_y = sorted(base_axes.collections[0].get_offsets()[:, 1])
        np.testing.assert_allclose(base_y, sorted(background.overall_connectance))

        with tempfile.TemporaryDirectory(prefix="dodged-text-") as temporary:
            output = Path(os.environ.get("FIGURE_OUTPUT_DIR", temporary))
            output.mkdir(parents=True, exist_ok=True)
            for repeat in range(2):
                with self.subTest(repeat=repeat):
                    figure, axes = render(make_plot(*self.frames, self.theme))
                    assert_alignment(axes, observed, labels)
                    np.testing.assert_allclose(axes.collections[1].get_offsets(), base_stars)
                    np.testing.assert_allclose(sorted(axes.collections[0].get_offsets()[:, 1]), base_y)
                    np.testing.assert_allclose(axes.collections[0].get_sizes(), 4)
                    np.testing.assert_allclose(axes.collections[1].get_sizes(), 64)
                    np.testing.assert_allclose(axes.collections[0].get_facecolors()[:, 3], 0.2)
                    self.assertEqual(axes.get_xlabel(), "Carcass Years Post-Mortem")
                    self.assertEqual(axes.get_ylabel(), "Overall Network Connectance")
                    self.assertEqual([t.get_text() for t in figure.legends[0].get_texts()], ["Off", "On"])
                    self.assertFalse(axes.spines["top"].get_visible())
                    self.assertFalse(axes.spines["right"].get_visible())
                    if repeat == 0:
                        axes.set_title("Synthetic fixture: supplied labels, no statistics calculated")
                        png, svg = output / "dodged-text.png", output / "dodged-text.svg"
                        figure.savefig(png, dpi=160, bbox_inches="tight")
                        figure.savefig(svg, bbox_inches="tight")
                        self.assertTrue(png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
                        self.assertEqual(ET.parse(svg).getroot().tag, "{http://www.w3.org/2000/svg}svg")

    def test_alignment_rejects_missing_dodge(self):
        background, observed, labels = self.frames
        incomplete = original_layers(background, observed, self.theme).add(
            so.Text(color="k", artist_kws={"clip_on": False}),
            orient="x",
            x="age",
            y="yloc",
            color="age_map",
            text="pvalue",
            data=labels,
        )
        _, axes = render(incomplete)
        with self.assertRaisesRegex(AssertionError, "label x must match its dodged star"):
            assert_alignment(axes, observed, labels)


if __name__ == "__main__":
    unittest.main(verbosity=2)
