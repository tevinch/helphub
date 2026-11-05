# Raw DEFLATE with the Huffman-only strategy

Compress a local file with zlib's `Z_HUFFMAN_ONLY` strategy, decompress it, and compare every restored byte with the original. The example keeps the input unchanged and requires two new output paths.

## Build and run

A C11 compiler and zlib development headers/library are required. The test runner needs Python 3.9 or later.

```sh
cc -std=c11 -Wall -Wextra -Werror -O2 huffman_roundtrip.c -lz -o huffman_roundtrip
./huffman_roundtrip input.bin packed.deflate restored.bin
python3 test_roundtrip.py ./huffman_roundtrip
```

Use different, nonexistent paths for both outputs. Existing files are refused. A failed run removes only the output files it created. Files are processed in 16 KiB chunks; their total size is not cast to zlib's `uInt` input-length field. The input and outputs must support seeking because the program checks the complete result before reporting success.

The final line reports the input, compressed and restored byte counts and says `verified byte for byte`. Empty input is valid: its completed compressed stream still contains bytes.

## The important API choices

- `deflateInit2(..., -MAX_WBITS, 8, Z_HUFFMAN_ONLY)` selects **raw DEFLATE** and the Huffman-only compression strategy. Raw DEFLATE still has DEFLATE block framing; it is not a standalone Huffman coding format. The encoder can choose stored blocks when compression would be larger.
- `Z_NO_FLUSH` can buffer the input and produce no output for a short message. At end of input, call `deflate(..., Z_FINISH)` and drain output until it returns `Z_STREAM_END`. `deflateEnd()` frees the stream; it does not finish pending output.
- Decode this raw stream with `inflateInit2(..., -MAX_WBITS)` and continue until `Z_STREAM_END`. The decoder does not need a Huffman-only setting. `uncompress()` expects the zlib wrapper and does not match this raw format.
- Treat `Z_STREAM_END` as successful completion. Check failures before using a returned byte count in a write operation.

If the consumer expects the **zlib wrapper**, use positive `MAX_WBITS` on both sides instead. Raw DEFLATE has no wrapper checksum; this example checks equality against the original local file rather than adding one to the format.

## When a second run reports zero input bytes

A log saying `Compressed 0 to 2` reports zero input bytes before compression. Check the file and its size before changing the compressor again.

A filename helper that calls `strcat(dest + strlen(suffix), suffix)` can leave the original filename unchanged when the suffix is longer than the filename. Opening that returned name with `"wb"` can truncate the input. Append to the actual destination string, check allocation and I/O results, and keep input/output paths distinct. This example avoids suffix construction entirely and refuses existing output paths.

This explains a possible cause in the [complete example linked from discussion 1370](https://github.com/madler/zlib/discussions/1370); it does not establish what happened to someone else's local file.

## Validation and scope

The 12 scripted CLI tests cover empty and one-byte files, 445-byte text, binary data with NULs, a 524,317-byte input crossing many chunks, short filenames, spaces in paths, existing files, path collisions and missing arguments/input. They compare the input and restored files in full and independently decode the compressed output with Python's raw DEFLATE decoder. A repetitive-input check distinguishes the requested Huffman-only strategy from default string-matching compression.

Verified with zlib **1.4** and Clang on macOS, including AddressSanitizer and UndefinedBehaviorSanitizer for this consumer. Temporary omission checks for finishing, raw decoder setup, input consumption, restored writes and the selected strategy all fail the corresponding tests. These are scripted local checks; Windows and the original requester's environment have not been tested.

This is a small file round-trip example, not a general archive utility. It does not modify zlib or claim an upstream library defect.

References: [zlib 1.4 API header](https://github.com/madler/zlib/blob/v1.4/zlib.h), [annotated zlib usage](https://zlib.net/zlib_how.html), [zlib FAQ](https://zlib.net/zlib_faq.html).

## Optional coffee

This example is free. If it saved you time, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
