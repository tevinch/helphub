# Exact palette PNG export

Export a 64×64 opaque black/white image as a 4-bit indexed PNG with an exact 16-entry palette: entries 0–14 are black and entry 15 is white. The converter preserves the original's explicit 16-byte all-opaque `tRNS` chunk and refuses output larger than the original or 444 bytes.

This is a small, deliberately narrow solution for a legacy texture format. It does not threshold, dither, change pixels, edit a game resource, or promise that every image will fit the size limit.

## Run

Install [ImageMagick 7](https://imagemagick.org/script/download.php) with PNG support and Python 3.10 or newer. Keep `convert.py` and `check.py` together. Use an unmodified original PNG as the reference, your edited PNG as input, and a new output filename:

```sh
python3 convert.py --reference original.png edited.png ready.png
```

On Windows, the same command can use the Python launcher:

```powershell
py -3 convert.py --reference original.png edited.png ready.png
```

If ImageMagick is outside `PATH`, supply the executable path:

```powershell
py -3 convert.py --magick "C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe" --reference original.png edited.png ready.png
```

Adjust that example path to your installation. `--max-bytes 400` can impose a stricter limit. Existing destinations are never overwritten. Invalid input, changed RGBA pixels, a failed native decode, or a size overflow produces an error and leaves the sources and destination unchanged. Publication uses an atomic hard link in the destination directory; the filesystem must support hard links.

The reference must have exactly these properties:

- 64×64 pixels, 4-bit indexed PNG, no interlacing.
- 16 palette entries: 15 copies of `#000000`, followed by `#FFFFFF`.
- 16 explicit transparency bytes, all 255 (fully opaque).
- Only `IHDR`, `PLTE`, `tRNS`, `IDAT` and `IEND` chunks.

The edited input must be a single PNG of 64×64 pixels, with a PNG bit depth of 8 or less, at most 1 MiB, whose decoded pixels are exclusively `#000000FF` and `#FFFFFFFF`. All 16-bit inputs are rejected before native decoding so near-black or near-opaque values cannot be rounded into accepted colors. Animation, transparency, partial alpha and intermediate gray values are rejected. This converter is intentionally unsuitable for other palettes or dimensions.

## Why `-type` alone does not preserve the file layout

ImageMagick's in-memory type and the PNG file's color type are separate properties. Forcing `png:color-type=3` and `png:bit-depth=4` controls indexed encoding and bit depth, but does not by itself keep 15 duplicate black palette entries or an otherwise redundant all-opaque alpha table. `-strip` also removes profiles; APP1/8BIM/ICM/IPTC are unrelated to the palette.

This example lets ImageMagick decode the edited PNG, requires exact opaque black/white RGBA, then packs black as index 0 and white as index 15. Python's standard library writes the reference palette and transparency table and chooses the smallest of five lossless zlib strategies. A separate ImageMagick invocation must decode the candidate to the exact original edited RGBA before the file is published. No additional Python packages are required.

The reference has no `sRGB` chunk. The output follows that representation; ImageMagick reads both as sRGB. An opaque `tRNS` table can still make the decoder report alpha-capable palette storage. Displayed type labels can vary by build: the tested build reported `Type: Bilevel` and `Base type: PaletteAlpha` for both the original and output. The binary PNG contract is checked directly instead of relying on that label.

## Check the complete example

```sh
python3 check.py --magick magick
```

The check creates its own synthetic reference and edited PNGs in a temporary directory, runs the consumer command, independently reads CRCs, chunks, bounded zlib scanlines, filters and palette indices, and compares RGBA with a separate native decoder. It also exercises repeated conversion, source preservation, no-overwrite, malformed input, wrong dimensions, alpha, gray pixels, 16-bit near-gray and near-opaque input, file caps and a missing native executable. Omission controls verify that the checker rejects a shortened palette, a wrong white index, wrong bit depth, missing alpha metadata, changed pixels, invalid indices, oversized output, CRC errors and invalid or excessive compressed data.

To check your own two indexed PNGs through the same independent reader:

```sh
python3 check.py --magick magick --reference original.png --edited edited.png
```

The independent reader deliberately supports only the 4-bit/8-bit indexed PNGs used by this example. It is not a general PNG library. Temporary verification outputs are removed; run `convert.py` to retain your final file.

Validated on macOS with ImageMagick 7.1.2-34 Q16-HDRI, libpng 1.6.43, Python 3.12 and Python zlib 1.2.12. The supplied 504-byte edited PNG produced 399 bytes with unchanged decoded RGBA and the exact original palette/transparency structure. Its original was 444 bytes. Original texture files are not included. These are native command-line and file-format checks; game reinsertion and Windows execution have not been tested.

References: [ImageMagick PNG options](https://imagemagick.org/script/defines.php), [PNG specification](https://www.w3.org/TR/png-3/), [Python zlib](https://docs.python.org/3/library/zlib.html).

## Optional coffee

If this saved you some time, a coffee is welcome, but entirely optional. The example is free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
