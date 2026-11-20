# Integer scaling for a Wayland window

Keep the same SCTK `Window` and `wl_surface` when its scale changes. Resize the shared-memory buffer to match the new pixel density. For example, a 256 × 160 logical window at 2× needs a 512 × 320 pixel buffer. It still takes up 256 × 160 logical units.

## Run the example

Use a current stable Rust toolchain and a Linux Wayland session with `xdg-shell` and shared-memory support. Run the sample from this directory.

```sh
cargo run --locked
```

The window paints a checkerboard with 32 × 32 logical cells. On a mixed-DPI desktop, move it between outputs set to 1× and 2×. The checkerboard keeps its logical cell size as the buffer gains or loses pixels. Resizing the window updates the logical dimensions, and closing it exits the app. The example uses SCTK 0.21.1 and integer scales.

## Adapt `simple_window`

1. Initialize the scale to `1` and keep the width and height from `WindowHandler::configure` in logical units. A zero dimension in the configure event leaves the size up to the client. In this example, SCTK exposes that as `None` and the last chosen dimension is retained.
2. In `CompositorHandler::scale_factor_changed`, check that the callback belongs to your window and store the new scale. Request a redraw if the initial configure has arrived. Keep a scale received before the first configure and use it for the first buffer.
3. Render an ARGB8888 buffer at `logical_width * scale` by `logical_height * scale`, with a stride of `pixel_width * 4`. If you use `SlotPool` from `simple_window`, discard the cached buffer on scale or size changes and allocate at those pixel dimensions. Respect `SlotPool::canvas` returning `None` while the compositor is still reading a buffer.
4. Set `wl_surface.set_buffer_scale(scale)`, attach the new buffer, and damage the rectangle in pixel units with `damage_buffer`. Commit those changes together. Keep the old buffer's storage available until the compositor releases it. The example allocates a fresh slot for each redraw and lets `SlotPool` reclaim it on release.

| Logical size | Buffer scale | Buffer size | ARGB8888 stride |
| --- | --- | --- | --- |
| 256 × 160 | 1 | 256 × 160 | 1024 bytes |
| 256 × 160 | 2 | 512 × 320 | 2048 bytes |
| 256 × 160 | 1 | 256 × 160 | 1024 bytes |

`set_buffer_scale` requires `wl_surface` v3. `damage_buffer` requires v4. For older `wl_surface` versions, the example uses a 1× buffer when scale is unavailable and sends logical damage coordinates through `damage`. The example redraws on configure and scale changes. If your app animates, schedule the redraw through its existing frame callback path. Fractional scaling uses a separate protocol, typically with a viewport.

## Verification

A local protocol test sent `xdg-shell` configure and `wl_surface.preferred_buffer_scale` events to the running example. It checked that 1× → 2× → 1× used the same surface, each visible commit paired its scale with a matching buffer and pixel damage, the sampled checkerboard edges stayed at matching logical coordinates, and the original window still resized and closed. A second test sent the 2× scale before the initial configure. Both checks used a test compositor over a Unix socket.

See the [SCTK 0.21.1 window example](https://github.com/Smithay/client-toolkit/blob/v0.21.1/examples/simple_window.rs), [compositor callbacks](https://docs.rs/smithay-client-toolkit/0.21.1/smithay_client_toolkit/compositor/trait.CompositorHandler.html), and [Wayland surface protocol](https://smithay.github.io/wayland-rs/wayland_client/protocol/wl_surface/struct.WlSurface.html).

## Optional coffee

If this saved you time and you'd like to buy me a coffee, contributions are entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
