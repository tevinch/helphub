"""Export one 64x64 opaque black/white PNG with an exact legacy palette."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
HEADER = (64, 64, 4, 3, 0, 0, 0)
PALETTE = bytes(45) + b"\xff\xff\xff"
ALPHA = b"\xff" * 16
MAX_SOURCE_BYTES = 1024 * 1024


def read_png(path):
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("Input PNG must be at most 1 MiB")
    data = path.read_bytes()
    if not data.startswith(SIGNATURE):
        raise ValueError("Input is not a PNG")
    result, offset = [], 8
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("Truncated PNG chunk")
        length = struct.unpack_from(">I", data, offset)[0]
        if offset + 12 + length > len(data):
            raise ValueError("Truncated PNG payload")
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        checksum = struct.unpack_from(">I", data, offset + 8 + length)[0]
        if zlib.crc32(kind + payload) & 0xffffffff != checksum:
            raise ValueError("PNG chunk CRC mismatch")
        if kind in (b"acTL", b"fcTL", b"fdAT"):
            raise ValueError("Animated PNG is outside this example's scope")
        if not kind[0] & 32 and kind not in (b"IHDR", b"PLTE", b"IDAT", b"IEND"):
            raise ValueError("Unsupported critical PNG chunk")
        result.append((kind, payload))
        offset += 12 + length
    if not result or result[0][0] != b"IHDR" or len(result[0][1]) != 13 or result[-1] != (b"IEND", b""):
        raise ValueError("Invalid PNG boundaries")
    kinds = [kind for kind, _ in result]
    for kind in (b"IHDR", b"PLTE", b"tRNS", b"IEND"):
        if kinds.count(kind) > 1:
            raise ValueError("Duplicate PNG chunk")
    if b"IDAT" not in kinds:
        raise ValueError("PNG has no image data")
    first = kinds.index(b"IDAT")
    last = len(kinds) - 1 - kinds[::-1].index(b"IDAT")
    if any(kind != b"IDAT" for kind in kinds[first:last + 1]):
        raise ValueError("PNG image data must be contiguous")
    if b"PLTE" in kinds and kinds.index(b"PLTE") > first:
        raise ValueError("Palette must precede image data")
    if b"tRNS" in kinds and kinds.index(b"tRNS") > first:
        raise ValueError("Transparency must precede image data")
    header = struct.unpack(">IIBBBBB", result[0][1])
    if header[:2] != (64, 64):
        raise ValueError("This example requires exactly 64x64 pixels")
    return data, result, header


def rgba(magick, path):
    decoded = subprocess.run([magick, "-regard-warnings", str(path), "-depth", "8", "RGBA:-"],
                             capture_output=True, timeout=30, check=True)
    if len(decoded.stdout) != 64 * 64 * 4:
        raise ValueError("Native decoder did not return one 64x64 RGBA image")
    return decoded.stdout


def chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))


def export(magick, reference, edited, output, requested_cap):
    reference, edited, output = reference.resolve(), edited.resolve(), output.absolute()
    if output.resolve() in (reference, edited):
        raise ValueError("Output must be different from both source files")
    if os.path.lexists(output):
        raise ValueError("Output already exists; choose a new filename")
    ref_data, parts, header = read_png(reference)
    fields = dict(parts)
    if (header != HEADER or fields.get(b"PLTE") != PALETTE or fields.get(b"tRNS") != ALPHA
            or any(kind not in (b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND") for kind, _ in parts)
            or [kind for kind, _ in parts].index(b"tRNS") < [kind for kind, _ in parts].index(b"PLTE")):
        raise ValueError("Reference must be 4-bit indexed 64x64 with 15 black entries, white at 15, and 16 opaque tRNS bytes")
    _, _, edited_header = read_png(edited)
    if edited_header[2] > 8:
        raise ValueError("Edited input must have a PNG bit depth of 8 or less; 16-bit inputs are not quantized")
    rgba(magick, reference)  # Reject reference streams that the native PNG decoder cannot read.
    pixels = rgba(magick, edited)
    indices = []
    for offset in range(0, len(pixels), 4):
        pixel = pixels[offset:offset + 4]
        if pixel == b"\0\0\0\xff":
            indices.append(0)
        elif pixel == b"\xff\xff\xff\xff":
            indices.append(15)
        else:
            raise ValueError("Edited pixels must be opaque #000000FF or #FFFFFFFF; no thresholding is performed")
    rows = []
    for y in range(64):
        rows.append(b"\0" + bytes((indices[y * 64 + x] << 4) | indices[y * 64 + x + 1]
                                  for x in range(0, 64, 2)))
    raw = b"".join(rows)
    compressed = []
    for strategy in (zlib.Z_DEFAULT_STRATEGY, zlib.Z_FILTERED, zlib.Z_HUFFMAN_ONLY, zlib.Z_RLE, zlib.Z_FIXED):
        compressor = zlib.compressobj(9, zlib.DEFLATED, 15, 8, strategy)
        compressed.append(compressor.compress(raw) + compressor.flush())
    image_data = min(compressed, key=len)
    candidate = (SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", *HEADER))
                 + chunk(b"PLTE", fields[b"PLTE"]) + chunk(b"tRNS", fields[b"tRNS"])
                 + chunk(b"IDAT", image_data) + chunk(b"IEND", b""))
    cap = min(len(ref_data), 444, requested_cap if requested_cap is not None else 444)
    if len(candidate) > cap:
        raise ValueError(f"Lossless output is {len(candidate)} bytes; limit is {cap}. Nothing was written")
    # Verify before making the destination visible. Hard-link publication is atomic and never replaces a file.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix="palette-", suffix=".png", dir=output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(candidate)
            stream.flush()
            os.fsync(stream.fileno())
        if rgba(magick, temporary) != pixels:
            raise ValueError("Native round-trip changed edited RGBA pixels")
        color = subprocess.check_output([magick, "identify", "-format", "%[colorspace]|%[channels]", str(temporary)],
                                        text=True, timeout=30)
        reference_color = subprocess.check_output([magick, "identify", "-format", "%[colorspace]|%[channels]", str(reference)],
                                                  text=True, timeout=30)
        if color != reference_color or not color.startswith("sRGB|"):
            raise ValueError("Output color interpretation differs from reference")
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {"bytes": len(candidate), "limit": cap, "width": 64, "height": 64,
            "bit_depth": 4, "color_type": 3, "palette_entries": 16, "opaque_trns_entries": 16,
            "rgba_sha256": hashlib.sha256(pixels).hexdigest(), "native_color": color}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--magick", default="magick", help="ImageMagick 7 executable or full path")
    parser.add_argument("--reference", required=True, type=Path, help="Original matching PNG")
    parser.add_argument("--max-bytes", type=int, help="Optional stricter cap; never exceeds original size or 444")
    parser.add_argument("edited", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.max_bytes is not None and not 1 <= args.max_bytes <= 444:
        parser.error("--max-bytes must be between 1 and 444")
    try:
        result = export(args.magick, args.reference, args.edited, args.output, args.max_bytes)
    except (OSError, ValueError, struct.error, subprocess.SubprocessError) as error:
        parser.exit(1, f"Conversion failed: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
