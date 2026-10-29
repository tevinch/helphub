# Native check results

The [native workflow](https://github.com/tevinch/helphub/actions/runs/40924787784) completed successfully with **38 assertions** on Ubuntu 24.04, Gedit **46.2**, GTK **3.24.41**, xfwm4 **4.18.0** and Python **3.12.3**. WhiteSur's stable **2026-09-10** source was installed through its unmodified official installer at commit `99247ecd219bdc1c7409baff062b4aafcf1102a7`, after checking the archive SHA-256.

All three real Gedit headerbar controls produced these measurements:

| Configuration | Native control rectangle | Painted circle |
| --- | --- | --- |
| Original theme | 18 × 16 px | 14 × 14 px |
| Only minimum dimensions enlarged | 26 × 24 px | 14 × 14 px |
| Only background artwork enlarged | 18 × 16 px | 16 × 16 px, clipped |
| Exact controls.css | 26 × 24 px | 22 × 22 px |
| CSS snippet removed | 18 × 16 px | 14 × 14 px |

The CSS minimum dimensions and background canvas change from 16 to 24 logical pixels. Theme styling adds to the minimum; the source artwork has transparent padding, so its colored circle is slightly smaller than its canvas. AT-SPI supplied the real Gedit allocations; screenshots independently supplied the colored pixel bounds. The two incomplete settings failed the acceptance that requires both a larger target and larger artwork while producing their expected individual effects.

Switching xfwm4 between normal, hdpi and xhdpi changed a real server-decorated window's top frame extent from 28 to 42 to 56 pixels. Gedit's client-side rectangles and painted circles stayed unchanged. The independent native GtkHeaderBar preview reproduced the enlargement, while its ordinary button stayed 600 × 26 pixels and its existing CSS margin stayed 7 pixels.

The same native Gedit document was edited and saved, maximized/restored twice, minimized/restored and closed through its window controls. Exact buffer text and saved file bytes were preserved. The check kept Gedit's default implicit final newline; it did not change editor settings or normalize away differences. Equal-sized, aligned 12 × 12 interior crops showed distinct backdrop, maximize/restore, hover and pressed artwork. The retained CSS sentinel still applied after removal/relaunch, and native app logs contained no theme parsing errors.

These are scripted checks of native X11 applications under Xvfb, with Xft.dpi **138**, GTK scale **1** and a **1600 × 1000** virtual display. They are not human manual testing or a physical 4K monitor test. GTK4/libadwaita, Wayland and sandbox-specific configuration were not tested. Screenshots, raw measurements, sample files and logs are retained in the workflow artifact.
