# Freeform coordinates in python-pptx

Draw the requested trapezoid at its exact inch coordinates with python-pptx's native editable freeform API:

```python
from pptx import Presentation
from pptx.util import Inches

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
slide = prs.slides.add_slide(prs.slide_layouts[6])

points = [(2.0, 2.5), (4.5, 2.5), (4.0, 5.5), (2.5, 5.5)]
vertices = [(Inches(x), Inches(y)) for x, y in points]

builder = slide.shapes.build_freeform(*vertices[0])  # default scale=1
builder.add_line_segments(vertices[1:], close=True)
shape = builder.convert_to_shape()

prs.save("trapezoid.pptx")
```

Two details matter:

- **Local coordinates are rounded to integers.** Passing `2.5` with `scale=Inches(1)` rounds the coordinate before scaling. Converting the inch values to integer EMUs first preserves these fractional-inch positions.
- **Line endpoints share the start point's coordinate system.** They are target positions, rather than movement deltas. Keep the original absolute endpoints; subtracting the first point only from the later points mixes two origins.

Here both the local coordinates and the slide coordinates use EMUs, so the default scale of 1 is appropriate. One inch is 914,400 EMUs. `convert_to_shape()` uses its default origin at the slide's top-left corner.

For these four points, the expected bounding box is **left 2 in, top 2.5 in, width 2.5 in, height 3 in**. The shape remains an editable vector freeform.

## Run the example

Requires Python 3.8 or later. Open a terminal in `examples/freeform-coordinates` first. A virtual environment keeps the example's dependencies separate:

```sh
python -m venv .venv
# macOS / Linux:
. .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
python freeform_example.py
python -m unittest -v test_freeform_example.py
```

The script writes `trapezoid.pptx`. Choose another filename with:

```sh
python freeform_example.py custom-name.pptx
```

The included script adds a fill and outline so the polygon is easy to see. Its `add_polygon(slide, points)` example also works on an existing slide; all input points are absolute slide positions in inches.

## Verification

Checked with Python 3.12.4 and python-pptx 1.0.2.

The four acceptance tests run the real library, save a presentation, reopen it, and inspect the saved shape geometry. They check the exact trapezoid vertices and bounding box, closure, a fractional-inch triangle, repeated polygons, preservation of existing text, and the command's output file.

The generated slide was also converted to PDF with LibreOffice, and the rendered image was inspected in software. PowerPoint itself was not used.

The [documented builder contract](https://python-pptx.readthedocs.io/en/latest/api/shapes.html#pptx.shapes.shapetree.SlideShapes.build_freeform), [line endpoints](https://python-pptx.readthedocs.io/en/latest/api/shapes.html#pptx.shapes.freeform.FreeformBuilder.add_line_segments), and [origin placement](https://python-pptx.readthedocs.io/en/latest/api/shapes.html#pptx.shapes.freeform.FreeformBuilder.convert_to_shape) describe the coordinate rules. The original reproducible example is in [python-pptx #1156](https://github.com/scanny/python-pptx/issues/1156).

## Optional coffee

This example is free to use. If it saves you time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`

