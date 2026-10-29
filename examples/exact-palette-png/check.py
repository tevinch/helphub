"""Exercise the consumer CLI with synthetic PNGs and an independent PNG reader."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
PALETTE = bytes(45) + b"\xff\xff\xff"
TRANSPARENCY = b"\xff" * 16


def chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))


def chunks(data):
    assert len(data) <= 1024 * 1024, "PNG exceeds 1 MiB checker limit"
    assert data.startswith(SIGNATURE), "PNG signature"
    result, offset = [], 8
    while offset < len(data):
        assert offset + 12 <= len(data), "truncated chunk"
        length = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        assert offset + 12 + length <= len(data), "chunk bounds"
        crc = struct.unpack_from(">I", data, offset + 8 + length)[0]
        assert zlib.crc32(kind + payload) & 0xffffffff == crc, "chunk CRC"
        result.append((kind, payload))
        offset += 12 + length
    assert result[0][0] == b"IHDR" and result[-1] == (b"IEND", b""), "chunk order"
    for unique in (b"IHDR", b"PLTE", b"tRNS", b"IEND"):
        assert sum(k == unique for k, _ in result) <= 1, "duplicate chunk"
    return result


def decode(data):
    parts = chunks(data)
    header = struct.unpack(">IIBBBBB", parts[0][1])
    width, height, depth, color, compression, filtering, interlace = header
    assert (width, height) == (64, 64), "checker requires 64x64 pixels before decompression"
    assert color == 3 and depth in (4, 8), "checker expects indexed 4/8 PNG"
    assert (compression, filtering, interlace) == (0, 0, 0), "PNG methods"
    kinds = [k for k, _ in parts]
    first, last = kinds.index(b"IDAT"), len(kinds) - 1 - kinds[::-1].index(b"IDAT")
    assert all(k == b"IDAT" for k in kinds[first:last + 1]), "contiguous IDAT"
    assert kinds.index(b"PLTE") < first, "palette before pixels"
    if b"tRNS" in kinds:
        assert kinds.index(b"PLTE") < kinds.index(b"tRNS") < first, "transparency order"
    palette = next(p for k, p in parts if k == b"PLTE")
    alpha = next((p for k, p in parts if k == b"tRNS"), b"")
    assert len(palette) % 3 == 0 and 0 < len(palette) <= 768, "palette length"
    assert len(alpha) <= len(palette) // 3, "transparency length"
    stride = (width * depth + 7) // 8
    expected = height * (stride + 1)
    decoder = zlib.decompressobj()
    raw = decoder.decompress(b"".join(p for k, p in parts if k == b"IDAT"), expected + 1)
    assert len(raw) == expected, "scanline length or decompression overflow"
    assert decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail, "one zlib stream"
    previous = bytearray(stride)
    pixels, indices = bytearray(), []
    for y in range(height):
        start = y * (stride + 1)
        method = raw[start]
        assert method <= 4, "filter type"
        row = bytearray(raw[start + 1:start + 1 + stride])
        for x in range(stride):
            left, up = row[x - 1] if x else 0, previous[x]
            upper_left = previous[x - 1] if x else 0
            predictor = 0
            if method == 1:
                predictor = left
            elif method == 2:
                predictor = up
            elif method == 3:
                predictor = (left + up) // 2
            elif method == 4:
                p = left + up - upper_left
                distances = (abs(p - left), abs(p - up), abs(p - upper_left))
                predictor = (left, up, upper_left)[distances.index(min(distances))]
            row[x] = (row[x] + predictor) & 255
        for x in range(width):
            index = row[x] if depth == 8 else (row[x // 2] >> (4 if x % 2 == 0 else 0)) & 15
            assert index * 3 + 3 <= len(palette), "palette index bounds"
            indices.append(index)
            pixels.extend(palette[index * 3:index * 3 + 3])
            pixels.append(alpha[index] if index < len(alpha) else 255)
        previous = row
    return header, palette, alpha, bytes(pixels), indices


def make_png(indices, width=64, height=64, depth=8, palette=PALETTE, alpha=b"", level=6):
    rows = []
    for y in range(height):
        row = indices[y * width:(y + 1) * width]
        packed = bytes(row) if depth == 8 else bytes((row[x] << 4) | row[x + 1] for x in range(0, width, 2))
        rows.append(b"\0" + packed)
    result = SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, depth, 3, 0, 0, 0))
    result += chunk(b"PLTE", palette)
    if alpha:
        result += chunk(b"tRNS", alpha)
    return result + chunk(b"IDAT", zlib.compress(b"".join(rows), level)) + chunk(b"IEND", b"")


def native_rgba(magick, path):
    return subprocess.check_output([magick, "-regard-warnings", str(path), "-depth", "8", "RGBA:-"], timeout=30)


def inspect(reference, edited, output, magick):
    ref, source, data = reference.read_bytes(), edited.read_bytes(), output.read_bytes()
    header, palette, alpha, rgba, indices = decode(data)
    assert header == (64, 64, 4, 3, 0, 0, 0), "exact 4-bit indexed header"
    assert palette == decode(ref)[1] == PALETTE, "exact 16-entry palette"
    assert alpha == decode(ref)[2] == TRANSPARENCY, "explicit opaque tRNS"
    assert set(indices) <= {0, 15}, "packed 0/15 indices"
    assert rgba == decode(source)[3], "independently decoded edited pixels"
    assert len(data) <= min(444, len(ref)), "file size cap"
    assert native_rgba(magick, edited) == rgba, "native source decode"
    assert native_rgba(magick, output) == rgba, "independent native output decode"
    formats = []
    for path in (reference, output):
        formats.append(subprocess.check_output(
            [magick, "identify", "-format", "%[colorspace]|%[channels]", str(path)], text=True, timeout=30))
    assert formats[0] == formats[1] and formats[1].startswith("sRGB|"), "same native color interpretation"
    return {"bytes": len(data), "rgba_sha256": hashlib.sha256(rgba).hexdigest(),
            "png_sha256": hashlib.sha256(data).hexdigest(), "native_color": formats[1]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--magick", default="magick")
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--edited", type=Path)
    args = parser.parse_args()
    if bool(args.reference) != bool(args.edited):
        parser.error("--reference and --edited are used together")
    converter = Path(__file__).with_name("convert.py")
    with tempfile.TemporaryDirectory(prefix="palette-check-") as temporary:
        directory = Path(temporary)
        base_indices = [15 if (x in (8, 55) or y in (8, 55)) else 0 for y in range(64) for x in range(64)]
        edit_indices = [15 if (x in (8, 55) or y in (8, 55) or x == y) else 0 for y in range(64) for x in range(64)]
        reference = directory / "reference.png"
        edited = directory / "edited.png"
        reference.write_bytes(make_png(base_indices, depth=4, alpha=TRANSPARENCY, level=0))
        edited.write_bytes(make_png(edit_indices))
        snapshots = {p: p.read_bytes() for p in (reference, edited)}
        checks = []

        def invoke(source, destination, extra=(), executable=args.magick, ref=reference):
            return subprocess.run([sys.executable, str(converter), "--magick", executable,
                                   "--reference", str(ref), *extra, str(source), str(destination)],
                                  capture_output=True, text=True, timeout=45)

        output = directory / "output.png"
        result = invoke(edited, output)
        assert result.returncode == 0, result.stderr
        synthetic = inspect(reference, edited, output, args.magick)
        checks.append("synthetic complete CLI and independent PNG/native decode")
        repeated = directory / "repeated.png"
        assert invoke(edited, repeated).returncode == 0
        assert repeated.read_bytes() == output.read_bytes(), "repeat determinism"
        checks.append("repeated conversion")

        def must_fail(label, source=edited, extra=(), executable=args.magick, ref=reference, destination=None):
            target = destination or directory / (label + ".png")
            before = target.read_bytes() if target.exists() else None
            source_before = {path: path.read_bytes() for path in (source, ref)}
            outcome = invoke(source, target, extra, executable, ref)
            assert outcome.returncode != 0, label + " unexpectedly succeeded"
            assert (target.read_bytes() if target.exists() else None) == before, label + " changed output"
            assert all(path.read_bytes() == data for path, data in source_before.items()), label + " changed source"
            checks.append(label)

        must_fail("existing-output", destination=output)
        must_fail("same-input-output", destination=edited)
        must_fail("missing-native", executable=str(directory / "missing-magick"))
        must_fail("size-cap", extra=("--max-bytes", "1"))
        must_fail("cap-above444", extra=("--max-bytes", "445"))
        bad = directory / "bad.png"
        bad.write_bytes(b"not a PNG")
        must_fail("malformed-input", source=bad)
        bad.write_bytes(make_png([0] * (63 * 64), width=63))
        must_fail("wrong-dimensions", source=bad)
        bad.write_bytes(make_png(edit_indices, alpha=b"\xff" * 15 + b"\x80"))
        must_fail("partial-alpha", source=bad)
        bad.write_bytes(make_png(edit_indices, alpha=b"\xff" * 15 + b"\0"))
        must_fail("transparent-pixel", source=bad)
        bad.write_bytes(make_png(edit_indices, palette=bytes(45) + b"\x80\x80\x80"))
        must_fail("non-bilevel", source=bad)
        for label, pixel in [("sixteen-bit-near-gray", (1, 1, 1, 65535)),
                             ("sixteen-bit-near-opaque-alpha", (0, 0, 0, 65534))]:
            raw = b"".join(b"\0" + struct.pack(">HHHH", *pixel) * 64 for _ in range(64))
            bad.write_bytes(SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 16, 6, 0, 0, 0))
                            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
            must_fail(label, source=bad)
        bad.write_bytes(make_png(base_indices, depth=4))
        must_fail("reference-missing-trns", ref=bad)
        bad.write_bytes(edited.read_bytes() + bytes(1024 * 1024))
        must_fail("oversized-input", source=bad)

        # Each omission control remains a valid generated PNG where possible.
        controls = {
            "missing-duplicate-palette": make_png([1 if i else 0 for i in edit_indices], depth=4,
                                                  palette=b"\0\0\0\xff\xff\xff", alpha=b"\xff\xff"),
            "wrong-white-index": make_png([1 if i else 0 for i in edit_indices], depth=4,
                                          palette=b"\0\0\0\xff\xff\xff" + bytes(42), alpha=TRANSPARENCY),
            "wrong-depth": make_png(edit_indices, depth=8, alpha=TRANSPARENCY),
            "missing-trns": make_png(edit_indices, depth=4),
            "changed-pixel": make_png([15 - edit_indices[0]] + edit_indices[1:], depth=4, alpha=TRANSPARENCY),
            "index-out-of-bounds": make_png(edit_indices, depth=4, palette=b"\0\0\0\xff\xff\xff", alpha=b"\xff\xff"),
        }
        valid_parts = chunks(output.read_bytes())
        controls["oversized-output"] = output.read_bytes()[:-12] + chunk(b"tEXt", b"Note\0" + b"x" * 500) + chunk(b"IEND", b"")
        controls["invalid-crc"] = output.read_bytes()[:-1] + bytes([output.read_bytes()[-1] ^ 1])
        for label, replacement in [("invalid-zlib", b"invalid"),
                                   ("decompression-overflow", zlib.compress(bytes(100000)))]:
            controls[label] = SIGNATURE + b"".join(chunk(kind, replacement if kind == b"IDAT" else payload)
                                                   for kind, payload in valid_parts)
        for label, content in controls.items():
            candidate = directory / (label + ".png")
            candidate.write_bytes(content)
            try:
                inspect(reference, edited, candidate, args.magick)
            except (AssertionError, zlib.error, subprocess.CalledProcessError):
                checks.append("reject-output-" + label)
            else:
                raise AssertionError("checker accepted omitted requirement: " + label)
        for path, content in snapshots.items():
            assert path.read_bytes() == content, "source changed"
        checks.append("source files unchanged")
        report = {"synthetic": synthetic, "checks": checks}
        if args.reference:
            original = args.reference.resolve()
            edit = args.edited.resolve()
            saved = {p: p.read_bytes() for p in (original, edit)}
            real_output = directory / "supplied-output.png"
            result = invoke(edit, real_output, ref=original)
            assert result.returncode == 0, result.stderr
            report["supplied"] = inspect(original, edit, real_output, args.magick)
            assert all(p.read_bytes() == data for p, data in saved.items()), "supplied source changed"
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
