# Keep line-value labels visible

When labels use a line mark as their input, the default one-pixel offset can leave very few positions clear of the line. Keep the reactive geometry and give the label transform more clearance:

```json
{
  "type": "label",
  "size": [600, 400],
  "padding": 5,
  "avoidBaseMark": true,
  "anchor": ["top", "bottom", "left", "right"],
  "offset": [8]
}
```

[The complete example](line-labels.vg.json) retains the 13 original values, 600×400 plot, axes, scales, 12px text, and two-pixel steelblue line. It adds `offset: [8]` to the existing reactive-line recipe from [Vega #3976](https://github.com/vega/vega/issues/3976#issuecomment-6694430208).

## Run it

1. Open the [Vega Editor](https://vega.github.io/editor/) and select **Vega**.
2. Replace the specification with the contents of `line-labels.vg.json`, then select **Run**.
3. Under **Settings → Renderer**, try **SVG** and **Canvas**. All 13 value labels should remain visible and clear of the line in this example.

The line is named `line-01`. The text mark reads its rendered items using `"from": {"data": "line-01"}`, with `"text": {"field": "datum.Cost", "format": ".2~s"}` retained from that recipe. Feeding the raw records directly to the text mark does not give `avoidBaseMark` the line geometry to avoid.

The additional offset is the missing piece for this chart: it gives the four anchor directions more room around each point. Use the array form `[8]`. The released Vega 6.4.0 parser rejected a scalar `8` in the checks.

## Verified scope

Software-operated browser checks with **Vega 6.4.0**, **Firefox 160.0**, and **Chrome 157.0.8103.52** rendered all 13 labels in SVG and Canvas, both in a standalone page and in **Vega Editor 1747515**. The checks retained the original data and line geometry and found no intersections between the line stroke and the placed label bounds in the standalone views. The unchanged one-pixel-offset recipe placed only one label in those checks.

The example keeps the original v5 schema declaration; the current Editor displays a schema-version warning while running Vega 6.4.0. The original text settings are also retained. Different data, fonts, plot sizes, or browser profiles may require different spacing. The label transform can still omit a label when none of its candidate positions fits; eight pixels is a verified setting for this example, not a universal guarantee.

See the official [label transform documentation](https://vega.github.io/vega/docs/transforms/label/) for reactive geometry, anchors, offsets, and avoidance settings.

## Optional coffee

This guide and example are free. If they save you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
