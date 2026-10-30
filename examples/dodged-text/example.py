"""Native Seaborn objects text aligned with two dodged point layers."""

import pandas as pd
import seaborn.objects as so


def make_plot(within_nulls, network_obs, pvals, theme):
    """Plot supplied data and labels without calculating any statistics."""
    return (
        so.Plot(
            x="age", y="overall_connectance", color="age_map", data=within_nulls
        )
        .add(so.Dot(alpha=0.2, pointsize=2), so.Jitter(), so.Dodge())
        .add(so.Dot(marker="*", pointsize=8), so.Dodge(), data=network_obs)
        .add(
            so.Text(color="k", artist_kws={"clip_on": False}),
            so.Dodge(by=["color"]),
            orient="x",
            x="age",
            y="yloc",
            color="age_map",
            text="pvalue",
            data=pvals,
        )
        .label(
            x="Carcass Years Post-Mortem",
            y="Overall Network Connectance",
            color="",
        )
        .scale(color=so.Nominal(order=["Off", "On"]))
        .theme(theme)
    )


def synthetic_data():
    """Small invented data; label strings are examples, not p-values."""
    background, observed, labels = [], [], []
    for age in [1, 3, 5]:
        for group, shift in [("Off", 0.0), ("On", 0.10)]:
            value = 0.10 + age * 0.08 + shift
            for difference in [-0.03, -0.01, 0.01, 0.03]:
                background.append(
                    dict(age=age, age_map=group, overall_connectance=value + difference)
                )
            observed.append(dict(age=age, age_map=group, overall_connectance=value))
            labels.append(
                dict(age=age, age_map=group, yloc=value + 0.15, pvalue=f"label {age}-{group}")
            )
    # Different input orders make grouping depend on the mapped values, not row order.
    return (
        pd.DataFrame(background),
        pd.DataFrame(observed[::-1]),
        pd.DataFrame(labels[::2] + labels[1::2]),
    )


if __name__ == "__main__":
    within_nulls, network_obs, pvals = synthetic_data()
    theme = {"axes.spines.top": False, "axes.spines.right": False}
    (
        make_plot(within_nulls, network_obs, pvals, theme)
        .label(title="Synthetic example: supplied labels, no statistics calculated")
        .layout(size=(9, 5))
        .show()
    )
