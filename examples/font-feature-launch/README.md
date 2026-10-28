# Launch the OTFeatFreezer graphical interface

OTFeatFreezer's graphical interface is the top-level `featfreeze_gui.py` script. You can run it from a source checkout; building an application bundle is optional.

These steps target the upstream **v0.7.0 prerelease**, checked on 29 October 2026. Its project metadata requires Python 3.15 or newer. The checked environment was macOS 14.6 on Apple silicon, Python 3.15.2, PySide6 6.12.0 and opentype-feature-freezer 1.32.2. The PySide6 6.12.0 macOS wheels require macOS 14 or newer; other operating systems were not tested here.

## Install the project and open the window

Install Git and [uv using its official installation instructions](https://docs.astral.sh/uv/getting-started/installation/). In Terminal, choose a working directory and run:

```sh
git clone --branch v0.7.0 --depth 1 https://github.com/postnumbers/OTFeatFreezer.git
cd OTFeatFreezer
uv sync --locked --no-dev
uv run --no-sync python featfreeze_gui.py
```

`uv sync` creates a `.venv` environment for this project, installs the upstream locked dependencies, and can download a suitable Python interpreter when needed. The dependency set includes Qt and build tools, so allow room for a substantial download and environment (about 1.3 GiB installed in the checked macOS environment).

The final command opens a window titled **OpenType Feature Freezer**. Keep Terminal open while using it. Use the same final command from the checkout directory to start it again.

In this release, the installed `otfeatfreezer` command prints `Hello from otfeatfreezer!` and exits. That command currently points to a placeholder in `src/otfeatfreezer/__init__.py`. Invoke `featfreeze_gui.py` explicitly to open the interface.

## Process a font

1. Click **Add fonts…** and choose a font you are allowed to modify.
2. Select the font's row, then check the required feature under **OpenType features**. The preview should show its effect for supported characters.
3. Set **Output folder** to a separate, empty folder, so the original font remains available.
4. Click **Generate output font files**. Wait for `Done: 1 font file(s) saved.` when processing one font, and inspect the generated file in the output folder.

You can also pass a font path when starting the interface:

```sh
uv run --no-sync python featfreeze_gui.py "/full/path/to/font.ttf"
```

## Try a small sample first

[make_demo_font.py](make_demo_font.py) creates a tiny font with one character: `a` is a rectangle, and selecting `ss01` changes it to a triangle. It creates a file without installing a font. The script refuses to overwrite an existing destination.

Save the script into your checkout directory, then run:

```sh
uv run --no-sync python make_demo_font.py feature-demo.ttf
uv run --no-sync python featfreeze_gui.py feature-demo.ttf
```

Select **ss01 · Stylistic Set 1**, choose a separate output folder, and generate the output. The preview should show the triangle and report one changed character. The generated font should use that triangle for `a` without requiring an application to enable `ss01`.

The original v0.7.0 source launcher was checked through its actual Qt window with scripted interactions: loading this sample, selecting `ss01`, observing the preview change, and generating files into two separate output folders. Independent font-table reads confirmed `a` mapped to `a.alt` in both output files; the input bytes stayed unchanged. Controls that omitted feature selection or the Generate click failed those checks. This was software-operated GUI validation, not human manual testing. The downloadable application bundle and other platforms were not tested.

## References and license

- [Upstream v0.7.0 prerelease](https://github.com/postnumbers/OTFeatFreezer/releases/tag/v0.7.0)
- [GUI script and its launch instructions](https://github.com/postnumbers/OTFeatFreezer/blob/v0.7.0/featfreeze_gui.py)
- [Python and dependency requirements](https://github.com/postnumbers/OTFeatFreezer/blob/v0.7.0/pyproject.toml), [console entry point](https://github.com/postnumbers/OTFeatFreezer/blob/v0.7.0/src/otfeatfreezer/__init__.py)
- [uv project environments](https://docs.astral.sh/uv/guides/projects/)

This guide and the sample-font generator are available under the [MIT license](LICENSE). They do not include OTFeatFreezer's source code or application bundle.

## Optional coffee

If this helped, you can optionally buy me a coffee. The guide and sample are free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
