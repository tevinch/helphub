# Native check scope

The example's native verification is pending. No successful run is claimed by this draft.

The workflow uses Ubuntu 24.04, GTK3 Gedit, PyGObject, AT-SPI, Xvfb and xfwm4. It installs WhiteSur's stable 2026-09-10 source at commit `99247ecd219bdc1c7409baff062b4aafcf1102a7`, checking the archive SHA-256 before running the official installer on a disposable runner.

The intended acceptance covers the real Gedit button allocations from accessibility geometry, painted control dimensions from screenshots, the normal/hdpi/xhdpi distinction from an actual server-decorated window, two maximize/restore cycles, minimize/restore, hover/restore artwork, close, real document editing/saving and preservation, an independent GtkHeaderBar preview, unchanged ordinary widgets, retained pre-existing CSS and exact removal. Incomplete allocation-only and artwork-only settings must fail the combined acceptance.

The check is software-operated native X11 validation. It is not human manual testing, a physical 4K display test, or validation of GTK4/libadwaita, Wayland or sandbox-specific configuration. Xft.dpi is 138 and GTK scale is 1 in the isolated session. Screenshots and measurements are retained as workflow artifacts.
