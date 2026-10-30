# Text labels aligned with dodged Seaborn points

Seaborn **0.13.2** already provides `so.Text`. Add a text layer to the existing objects plot, using the annotation table's own coordinates and groups:

```python
g = g.add(
    so.Text(color="k", artist_kws={"clip_on": False}),
    so.Dodge(by=["color"]),
    orient="x",
    x="age",
    y="yloc",
    color="age_map",
    text="pvalue",
    data=pvals,
)
g.show()
```

The `pvals` table needs `age`, `age_map`, `yloc`, and `pvalue` columns. Supply the label strings and their vertical positions; this example calculates no p-values.

- Put positional transforms such as `so.Dodge(...)` before keyword arguments.
- Use **`text=`**, rather than `string=`, for the label mapping. An unused `string` mapping can leave empty labels.
- Explicitly map `x` and `color` from the new table along with `y` and `text`. This avoids retaining the original table's coordinate/group vectors by index.
- Dodge the labels by `color`, matching the existing `Off`/`On` groups. Keep the original `so.Nominal(order=["Off", "On"])` scale and theme.

The native `clip_on=False` artist setting keeps long labels at the plot boundary visible without changing the axes limits.

`example.py` includes the original jittered point layer, observed star layer, axes labels, color order, and theme call. The caller supplies the data frames and theme. Its runnable demonstration uses invented data and strings such as `label 1-Off`; these are examples, not statistical results. The original question did not include its data frames or theme definition.

## Run

With Python 3.12:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python example.py
```

To use your own data, call `make_plot(within_nulls, network_obs, pvals, theme).show()`, or copy the text layer directly into your existing chain. Let the objects plot create its figure, as in the original `g.show()` workflow, so its theme applies when the axes are created.

## Verify

```sh
python verify.py
```

The checks render actual Matplotlib artists with the Agg backend. They verify six supplied labels against independently drawn star positions, the original point values and sizes, the color order, axes labels, theme, unchanged inputs, and repeated rendering. A negative case omits the text layer's dodge and must fail the same alignment check. PNG and SVG output are also rendered. Set `FIGURE_OUTPUT_DIR` to retain those synthetic figures; otherwise they are temporary.

The original random jitter is retained, so background dot x positions can vary between renders. The tests compare the unchanged values and star positions rather than requiring identical pixels. The pinned current dependencies pass the checks; Seaborn 0.13.2 emits a pandas 3.1 deprecation warning about its internal `pd.concat(copy=False)` call. No dependency source is changed or warning hidden.

These checks establish the included synthetic workflow, not the recipient's actual data, statistics, or adoption.

## References

- [Seaborn Text](https://seaborn.pydata.org/generated/seaborn.objects.Text.html)
- [Plot.add](https://seaborn.pydata.org/generated/seaborn.objects.Plot.add.html)
- [Dodge](https://seaborn.pydata.org/generated/seaborn.objects.Dodge.html)
- [Original question](https://github.com/mwaskom/seaborn/issues/3981)

## Optional coffee

If this saved you some time, a coffee is welcome, but entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
