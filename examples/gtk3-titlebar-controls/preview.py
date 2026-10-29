#!/usr/bin/env python3
"""A native GTK3 preview; --ssd uses the window manager's titlebar instead."""
import argparse
import json
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ssd", action="store_true")
parser.add_argument("--report", type=Path)
args = parser.parse_args()

window = Gtk.Window(title="Titlebar preview SSD" if args.ssd else "Titlebar preview CSD")
window.set_default_size(640, 320)
window.connect("destroy", Gtk.main_quit)
if not args.ssd:
    header = Gtk.HeaderBar(title="Titlebar preview CSD", show_close_button=True)
    header.set_decoration_layout("close,minimize,maximize:")
    header.set_has_subtitle(False)
    window.set_titlebar(header)
box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=20)
ordinary = Gtk.Button(label="Ordinary button")
ordinary.set_name("ordinary-button")
box.pack_start(ordinary, False, False, 0)
text = Gtk.TextView()
text.get_buffer().set_text("Keep this text while maximizing, minimizing and restoring.\n")
box.pack_start(text, True, True, 0)
window.add(box)
window.show_all()

def children(widget):
    yield widget
    if isinstance(widget, Gtk.Container):
        # GtkHeaderBar's native decoration controls are internal children.
        nested = []
        widget.forall(lambda child, *unused: nested.append(child))
        for child in nested:
            yield from children(child)

def report():
    if args.report:
        controls = {}
        for widget in children(window):
            context = widget.get_style_context()
            for name in ("close", "minimize", "maximize"):
                if context.has_class("titlebutton") and context.has_class(name):
                    allocation = widget.get_allocation()
                    controls[name] = [allocation.width, allocation.height]
        allocation = ordinary.get_allocation()
        buffer = text.get_buffer()
        value = {"controls": controls, "ordinary": [allocation.width, allocation.height],
                 "sentinel_margin": ordinary.get_style_context().get_margin(Gtk.StateFlags.NORMAL).left,
                 "text": buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True),
                 "maximized": window.is_maximized(), "gtk": [Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()]}
        temporary = args.report.with_suffix(".tmp")
        temporary.write_text(json.dumps(value))
        temporary.replace(args.report)
    return True

GLib.timeout_add(150, report)
Gtk.main()
