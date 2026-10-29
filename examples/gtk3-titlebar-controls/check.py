#!/usr/bin/env python3
"""Run native checks on an isolated X11 desktop, with a preinstalled WhiteSur theme.

Intended for the disposable CI desktop in the accompanying workflow. Do not run
against an existing desktop: this changes xfwm4's theme in its D-Bus session.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pyatspi
from PIL import Image, ImageGrab

HERE = Path(__file__).resolve().parent
SENTINEL = "/* Existing user setting: retain this. */\n#ordinary-button { margin-left: 7px; }\n"
TEXT = "A small titlebar should not make this document harder to use.\n"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--data", type=Path, required=True, help="XDG data directory containing themes/")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
OUT = args.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
assert os.environ.get("DISPLAY") and os.environ.get("DBUS_SESSION_BUS_ADDRESS"), "Needs isolated X11 and D-Bus"
report = {"status": "running", "snapshots": {}, "state_differences": [], "checks": []}
processes = []

def command(*parts, check=True):
    return subprocess.run([str(x) for x in parts], check=check, text=True, capture_output=True).stdout.strip()

def wait_for(probe, message, seconds=15):
    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        try:
            result = probe()
            if result:
                return result
        except Exception as exc:
            last = repr(exc)
        time.sleep(.15)
    raise AssertionError(f"{message}; last error: {last}")

def require(condition, message):
    if not condition:
        raise AssertionError(message)
    report["checks"].append(message)

def descendants(node):
    yield node
    try:
        for index in range(node.childCount):
            yield from descendants(node.getChildAtIndex(index))
    except (RuntimeError, LookupError):
        return

def controls_for(pid):
    desktop = pyatspi.Registry.getDesktop(0)
    found = {}
    for app in desktop:
        if app.get_process_id() != pid:
            continue
        for node in descendants(app):
            name = (node.name or "").lower()
            if node.getRole() == pyatspi.ROLE_PUSH_BUTTON:
                state = node.getState()
                if not (state.contains(pyatspi.STATE_VISIBLE) and state.contains(pyatspi.STATE_SHOWING)):
                    continue
                for key in ("close", "minimize", "maximize", "restore"):
                    if name == key:
                        rect = node.queryComponent().getExtents(pyatspi.DESKTOP_COORDS)
                        if rect.x >= 0 and rect.y >= 0 and rect.width > 0 and rect.height > 0:
                            found["maximize" if key == "restore" else key] = [rect.x, rect.y, rect.width, rect.height]
    return found if len(found) == 3 else None

def window_for(pid):
    ids = command("xdotool", "search", "--onlyvisible", "--pid", pid, check=False).splitlines()
    for window in ids:
        if "_NET_WM_WINDOW_TYPE_NORMAL" in command("xprop", "-id", window, "_NET_WM_WINDOW_TYPE", check=False):
            return window

def click(rect):
    x, y, width, height = rect
    command("xdotool", "mousemove", "--sync", x + width // 2, y + height // 2)
    command("xdotool", "click", "1")

def activate(window):
    command("xdotool", "windowactivate", "--sync", window)
    command("xdotool", "mousemove", "--sync", "1100", "750")
    time.sleep(.3)

def snapshot(label, pid, window, hover=None, activate_window=True):
    if activate_window:
        activate(window)
    rects = wait_for(lambda: controls_for(pid), "Native three-control accessibility geometry")
    if hover:
        x, y, width, height = rects[hover]
        command("xdotool", "mousemove", "--sync", x + width // 2, y + height // 2)
        time.sleep(.35)
    image = ImageGrab.grab()
    image.save(OUT / f"{label}.png")
    measurements = {}
    for name, (x, y, width, height) in rects.items():
        crop = image.crop((x, y, x + width, y + height)).convert("RGB")
        crop.save(OUT / f"{label}-{name}.png")
        colored = [(px, py) for py in range(height) for px in range(width)
                   if max(crop.getpixel((px, py))) - min(crop.getpixel((px, py))) > 55]
        bounds = ([min(p[0] for p in colored), min(p[1] for p in colored),
                   max(p[0] for p in colored) + 1, max(p[1] for p in colored) + 1] if colored else None)
        measurements[name] = {"rect": [x, y, width, height], "painted":
                              [bounds[2] - bounds[0], bounds[3] - bounds[1]] if bounds else [0, 0],
                              "pixel_sha256": hashlib.sha256(crop.tobytes()).hexdigest()}
    report["snapshots"][label] = measurements
    return measurements

def geometry(items):
    return {k: {field: value[field] if field == "painted" else value[field][2:] for field in ("rect", "painted")}
            for k, value in items.items()}

def larger(current, baseline):
    return (all(current[k]["rect"][2] >= baseline[k]["rect"][2] + 6 and current[k]["rect"][3] >= baseline[k]["rect"][3] + 6 for k in baseline)
            and all(current[k]["painted"][0] >= baseline[k]["painted"][0] + 6 and current[k]["painted"][1] >= baseline[k]["painted"][1] + 6 for k in baseline))

def state_difference(before, after, control, message):
    first = Image.open(OUT / f"{before}-{control}.png").convert("RGB")
    second = Image.open(OUT / f"{after}-{control}.png").convert("RGB")
    require(first.size == second.size, f"Equal native control dimensions for {before}/{after}")
    # Compare aligned interior pixels: position, allocation changes and the
    # surrounding headerbar cannot create a false state-artwork difference.
    side = min(12, first.width, first.height)
    require(side >= 10, "Control interior is large enough for artwork comparison")
    left, top = (first.width - side) // 2, (first.height - side) // 2
    box = (left, top, left + side, top + side)
    first, second = first.crop(box), second.crop(box)
    changed = sum(max(abs(a - b) for a, b in zip(one, two)) > 12
                  for one, two in zip(first.getdata(), second.getdata()))
    report["state_differences"].append({"before": before, "after": after,
                                      "control": control, "interior_size": side, "changed_pixels": changed})
    require(changed >= 3, message)

def start_case(name, css, ssd=False):
    config = OUT / name / "config" / "gtk-3.0"
    config.mkdir(parents=True)
    (config / "settings.ini").write_text("[Settings]\ngtk-theme-name=WhiteSur-Dark-orange\ngtk-decoration-layout=close,minimize,maximize:\ngtk-xft-dpi=141312\n")
    (config / "gtk.css").write_text(SENTINEL + css)
    env = dict(os.environ, XDG_CONFIG_HOME=str(config.parent), XDG_DATA_HOME=str(args.data.resolve()),
               GTK_THEME="WhiteSur-Dark-orange", GTK_MODULES="gail:atk-bridge", NO_AT_BRIDGE="0", GDK_BACKEND="x11", GDK_SCALE="1", GDK_DPI_SCALE="1")
    stats = OUT / name / "preview.json"
    stderr = open(OUT / name / "preview.stderr", "w")
    preview = subprocess.Popen([sys.executable, str(HERE / "preview.py"), "--report", str(stats)] + (["--ssd"] if ssd else []), env=env, stderr=stderr)
    processes.append(preview)
    window = wait_for(lambda: window_for(preview.pid), "Preview visible")
    command("xdotool", "windowmove", "--sync", window, "900", "620")
    if ssd:
        return {"preview": preview, "window": window, "config": config, "stderr": stderr}
    wait_for(lambda: stats.exists() and len(json.loads(stats.read_text())["controls"]) == 3, "Native preview allocated controls")
    document = OUT / name / "sample.txt"
    document.write_text(TEXT)
    log = open(OUT / name / "gedit.stderr", "w")
    gedit = subprocess.Popen(["gedit", "--standalone", "--new-window", str(document)], env=env, stderr=log)
    processes.append(gedit)
    gwindow = wait_for(lambda: window_for(gedit.pid), "Real Gedit window visible")
    command("xdotool", "windowmove", "--sync", gwindow, "80", "80")
    wait_for(lambda: controls_for(gedit.pid), "Gedit native controls present")
    return {"preview": preview, "gedit": gedit, "window": gwindow, "preview_window": window,
            "config": config, "stats": stats, "document": document, "logs": [stderr, log]}

def finish_case(case):
    for key in ("gedit", "preview"):
        process = case.get(key)
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=8)
    for log in case.get("logs", [case.get("stderr")]):
        if log:
            log.close()

def wm_theme(name):
    command("xfconf-query", "-c", "xfwm4", "-p", "/general/theme", "-s", name)
    wait_for(lambda: command("xfconf-query", "-c", "xfwm4", "-p", "/general/theme") == name, "xfwm theme applied")
    time.sleep(.4)

def frame_extents(window):
    value = command("xprop", "-id", window, "_NET_FRAME_EXTENTS")
    return [int(n.strip()) for n in value.split("=", 1)[1].split(",")]

try:
    report["versions"] = {"gedit": command("gedit", "--version"), "xfwm": command("xfwm4", "--version", check=False), "python": sys.version}
    wm_theme("WhiteSur-Dark-orange")
    baseline = start_case("baseline", "")
    base = snapshot("baseline", baseline["gedit"].pid, baseline["window"])
    baseline_stats = json.loads(baseline["stats"].read_text())
    require(all(v["painted"][0] >= 12 for v in base.values()), "All three baseline painted controls are visible")
    require(baseline_stats["sentinel_margin"] == 7, "Existing user CSS is actually applied")
    ssd = start_case("ssd", "", ssd=True)
    ssd_extents = {}
    for variant in ("WhiteSur-Dark-orange", "WhiteSur-Dark-orange-hdpi", "WhiteSur-Dark-orange-xhdpi"):
        wm_theme(variant)
        current = snapshot("xfwm-" + variant, baseline["gedit"].pid, baseline["window"])
        require(geometry(current) == geometry(base), f"{variant} leaves Gedit client controls unchanged")
        ssd_extents[variant] = frame_extents(ssd["window"])
    report["ssd_extents"] = ssd_extents
    require(len({tuple(value) for value in ssd_extents.values()}) >= 2, "xfwm variants really change server decoration extents")
    finish_case(ssd)
    finish_case(baseline)
    wm_theme("WhiteSur-Dark-orange-hdpi")

    css = (HERE / "controls.css").read_text()
    for label, incomplete in (("allocation-only", css.replace("background-size: 24px 24px;", "")),
                               ("artwork-only", css.replace("min-width: 24px;", "").replace("min-height: 24px;", ""))):
        case = start_case(label, incomplete)
        got = snapshot(label, case["gedit"].pid, case["window"])
        require(not larger(got, base), f"Incomplete {label} CSS fails combined target and artwork acceptance")
        if label == "allocation-only":
            require(all(got[k]["rect"][2] >= base[k]["rect"][2] + 6 and got[k]["rect"][3] >= base[k]["rect"][3] + 6 for k in base),
                    "Allocation-only CSS actually enlarges all native targets")
            require(all(got[k]["painted"] == base[k]["painted"] for k in base),
                    "Allocation-only CSS keeps the original painted circle size")
        else:
            require(all(got[k]["rect"][2:] == base[k]["rect"][2:] for k in base),
                    "Artwork-only CSS keeps all original native target dimensions")
            require(all(base[k]["painted"][0] < got[k]["painted"][0] <= base[k]["rect"][2]
                        and base[k]["painted"][1] < got[k]["painted"][1] <= base[k]["rect"][3] for k in base),
                    "Artwork-only CSS paints larger circles clipped within the old targets")
        finish_case(case)

    case = start_case("resized", css)
    got = snapshot("resized", case["gedit"].pid, case["window"])
    require(larger(got, base), "Exact CSS enlarges both native Gedit hit targets and painted controls")
    stats = json.loads(case["stats"].read_text())
    require(all(stats["controls"][k][0] >= baseline_stats["controls"][k][0] + 6 for k in stats["controls"]), "Independent native GtkHeaderBar allocation also grows")
    require(stats["ordinary"] == baseline_stats["ordinary"] and stats["sentinel_margin"] == 7, "Ordinary widget allocation and existing CSS remain unchanged")
    activate(case["preview_window"])
    backdrop = snapshot("backdrop", case["gedit"].pid, case["window"], activate_window=False)
    state_difference("resized", "backdrop", "close", "Native backdrop control artwork remains distinct")
    before_text = stats["text"]
    activate(case["window"])
    text_nodes = [n for app in pyatspi.Registry.getDesktop(0) if app.get_process_id() == case["gedit"].pid
                  for n in descendants(app) if n.getRole() == pyatspi.ROLE_TEXT and n.getState().contains(pyatspi.STATE_EDITABLE)]
    require(bool(text_nodes), "Real Gedit editable document is accessible")
    text_nodes[0].queryComponent().grabFocus()
    command("xdotool", "key", "--clearmodifiers", "ctrl+End")
    added = "Added after resizing the titlebar."
    command("xdotool", "type", "--clearmodifiers", "--delay", "0", added)
    command("xdotool", "key", "--clearmodifiers", "ctrl+s")
    wait_for(lambda: case["document"].read_text() == TEXT + added, "Gedit edit/save completed")
    normal_hover = snapshot("maximize-hover", case["gedit"].pid, case["window"], "maximize")
    for repeat in range(2):
        click(wait_for(lambda: controls_for(case["gedit"].pid), "Controls before maximize")["maximize"])
        wait_for(lambda: "MAXIMIZED_HORZ" in command("xprop", "-id", case["window"], "_NET_WM_STATE"), "Gedit actually maximized")
        restored_hover = snapshot(f"restore-hover-{repeat}", case["gedit"].pid, case["window"], "maximize")
        state_difference("maximize-hover", f"restore-hover-{repeat}", "maximize", f"Native maximize-to-restore hover artwork changes, repeat {repeat + 1}")
        click(wait_for(lambda: controls_for(case["gedit"].pid), "Controls before restore")["maximize"])
        wait_for(lambda: "MAXIMIZED_HORZ" not in command("xprop", "-id", case["window"], "_NET_WM_STATE"), "Gedit actually restored")
    click(wait_for(lambda: controls_for(case["gedit"].pid), "Controls before minimize")["minimize"])
    wait_for(lambda: "Iconic" in command("xprop", "-id", case["window"], "WM_STATE"), "Gedit actually minimized")
    activate(case["window"])
    wait_for(lambda: "Normal" in command("xprop", "-id", case["window"], "WM_STATE"), "Gedit restored after minimize")
    require(text_nodes[0].queryText().getText(0, -1) == TEXT + added, "Document text survives repeated window operations")
    require(json.loads(case["stats"].read_text())["text"] == before_text, "Preview text remains intact")
    hover = snapshot("close-hover", case["gedit"].pid, case["window"], "close")
    normal = snapshot("close-normal", case["gedit"].pid, case["window"])
    state_difference("close-normal", "close-hover", "close", "Native hover artwork remains distinct")
    rect = controls_for(case["gedit"].pid)["close"]
    command("xdotool", "mousemove", "--sync", rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)
    command("xdotool", "mousedown", "1")
    time.sleep(.25)
    pressed = snapshot("close-pressed", case["gedit"].pid, case["window"], activate_window=False)
    state_difference("close-hover", "close-pressed", "close", "Native pressed artwork remains distinct")
    command("xdotool", "mouseup", "1")
    wait_for(lambda: case["gedit"].poll() is not None, "Native close control closes the saved throwaway document")
    require(case["document"].read_text() == TEXT + added, "Saved document preserved after native close")
    require((case["config"] / "gtk.css").read_text() == SENTINEL + css, "Existing CSS and exact snippet preserved")
    finish_case(case)

    reverted = start_case("reverted", "")
    reverted_controls = snapshot("reverted", reverted["gedit"].pid, reverted["window"])
    require(geometry(reverted_controls) == geometry(base), "Removing only the snippet restores native baseline dimensions")
    require(json.loads(reverted["stats"].read_text())["sentinel_margin"] == 7, "Existing CSS still applies after removal")
    finish_case(reverted)
    errors = [(str(p.relative_to(OUT)), p.read_text()) for p in OUT.rglob("*.stderr") if "Theme parsing error" in p.read_text()]
    require(not errors, "No GTK theme parsing errors in native app logs")
    report["status"] = "passed"
except Exception as exc:
    report["status"] = "failed"
    report["error"] = repr(exc)
    raise
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    (OUT / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]), "output": str(OUT)}))
