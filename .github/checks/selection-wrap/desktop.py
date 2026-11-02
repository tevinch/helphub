"""Observe installation controls and native Save As; do not execute a macro."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

import gi
gi.require_version("Atspi", "2.0")
from gi.repository import Atspi, GLib
from PIL import ImageGrab, features


STARTUP_NOTICE = (
    "No LaTeX distribution was found on your system. As a result, the corresponding commands are not configured. "
    "This means, that you cannot compile your documents to the desired output format (e.g. pdf).\n\n"
    "If you intend to work with LaTeX, you'll most certainly want to install a LaTeX distribution."
)


def startup_notice_controls(records):
    if not records or records[0]["role"] != "alert" or records[0]["name"] != "TeXstudio":
        raise RuntimeError("Unexpected native startup modal")
    labels = [row["name"] for row in records if row["role"] == "label"]
    buttons = [i for i, row in enumerate(records) if row["role"] == "push button"]
    checkboxes = [i for i, row in enumerate(records) if row["role"] == "check box"]
    if (labels != [STARTUP_NOTICE] or len(buttons) != 1 or records[buttons[0]]["name"] != "OK"
            or len(checkboxes) != 1 or records[checkboxes[0]]["name"] != "Do not warn again."
            or records[checkboxes[0]]["checked"]):
        raise RuntimeError("Unknown or ambiguous native startup notice; leave it untouched")
    return {"message": labels[0], "okIndex": buttons[0], "checkboxIndex": checkboxes[0],
            "doNotWarnAgainBefore": False}


def run(argv, timeout=8, check=True, input_text=None):
    result = subprocess.run(argv, input=input_text, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"{argv[0]} failed: {result.stderr[-1000:]}")
    return result.stdout


def wait_for(operation, description, seconds=12):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            result = operation()
        except (GLib.Error, ProcessLookupError):
            result = None
        if result:
            return result
        time.sleep(0.15)
    raise RuntimeError("Native observation missing: " + description)


def nodes(root):
    pending, count = [(root, 0)], 0
    while pending:
        node, depth = pending.pop()
        if node is None:
            continue
        count += 1
        if count > 2500 or depth > 25:
            raise RuntimeError("Native accessibility tree exceeds the small probe bound")
        try:
            yield node
            children = node.get_child_count()
            if children > 500:
                raise RuntimeError("Unexpected native accessibility child count")
            pending.extend((node.get_child_at_index(i), depth + 1) for i in reversed(range(children)))
        except GLib.Error:
            continue


def showing(node):
    try:
        return node.get_state_set().contains(Atspi.StateType.SHOWING)
    except GLib.Error:
        return False


def find(root, name, roles=None):
    for node in nodes(root):
        if showing(node) and re.search(name, node.get_name() or "", re.I):
            if roles is None or node.get_role_name() in roles:
                return node
    return None


def click(node):
    rect = node.get_component_iface().get_extents(Atspi.CoordType.SCREEN)
    if rect.width <= 0 or rect.height <= 0:
        raise RuntimeError("Native control has no visible screen bounds")
    x, y = rect.x + rect.width // 2, rect.y + rect.height // 2
    if not 0 <= x < 1600 or not 0 <= y < 1000:
        raise RuntimeError("Native control is outside the owned screen")
    run(["xdotool", "mousemove", "--sync", str(x), str(y), "click", "1"])


def key(*keys):
    run(["xdotool", "key", "--clearmodifiers", *keys])


def record_tree(root, path):
    values = []
    for node in nodes(root):
        try:
            values.append({"name": (node.get_name() or "")[:300], "role": node.get_role_name(), "showing": showing(node), "focused": node.get_state_set().contains(Atspi.StateType.FOCUSED), "checked": node.get_state_set().contains(Atspi.StateType.CHECKED)})
        except GLib.Error:
            pass
    path.write_text(json.dumps(values, ensure_ascii=False, indent=2) + "\n")


def macro_rows(tree):
    table = tree.get_table_iface()
    count = table.get_n_rows()
    if not 0 <= count <= 500:
        raise RuntimeError("Unexpected native macro tree row count")
    rows = []
    for index in range(count):
        cell = table.get_accessible_at(index, 0)
        if cell is None:
            raise RuntimeError("Native macro tree row is not independently accessible")
        rows.append({"name": cell.get_name() or "", "checked": cell.get_state_set().contains(Atspi.StateType.CHECKED)})
    return {"rowCount": count, "selectedRows": list(table.get_selected_rows()), "rows": rows}


def observed_added_row(before, after):
    count = before["rowCount"]
    if (after["rowCount"] != count + 1 or len(after["rows"]) != count + 1
            or after["rows"][:count] != before["rows"]
            or after["selectedRows"] != [count]
            or not after["rows"][count]["checked"]):
        return None
    return {"rowIndex": count, "newSelectedCheckedRow": after["rows"][count]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("app", "work", "output", "fixture"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if not features.check_feature("xcb"):
        raise RuntimeError("Ubuntu Pillow lacks native XCB screen capture")
    if not os.environ.get("DISPLAY") or not os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        raise RuntimeError("A task-owned X11 display and D-Bus session are required")
    output, work = args.output.resolve(strict=True), args.work.resolve(strict=True)
    expected = args.fixture.read_bytes()
    if not expected.endswith(b"\n"):
        raise RuntimeError("The reviewed fixture must retain its final newline")
    original = work / "baseline.tex"
    original.write_bytes(expected)
    saved = work / "native-saved.tex"
    if saved.exists():
        raise RuntimeError("The native save checkpoint must be a fresh path")
    observed = {"stage": "native GUI prerequisite only", "macroExecuted": False, "nativeSave": False, "addAndScriptControls": False, "status": "unknown"}
    app = wm = None
    clipboard_owners = []
    desktop = Atspi.get_desktop(0)

    def screenshot(name):
        ImageGrab.grab(xdisplay=os.environ["DISPLAY"]).save(output / name)

    def clipboard(text):
        # Keep a foreground clipboard owner alive while the native application requests it.
        # Capturing the stdout pipes of a forking xclip process can otherwise deadlock.
        owner = subprocess.Popen(["xclip", "-selection", "clipboard", "-in", "-quiet"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        clipboard_owners.append(owner)
        owner.stdin.write(text)
        owner.stdin.close()
        wait_for(lambda: run(["xclip", "-selection", "clipboard", "-out"]) == text, "task clipboard owner")

    def app_tree():
        for child in (desktop.get_child_at_index(i) for i in range(desktop.get_child_count())):
            if "texstudio" in (child.get_name() or "").lower():
                return child
        return None

    try:
        with (output / "window-manager.log").open("w") as log:
            wm = subprocess.Popen(["openbox", "--sm-disable"], stdout=log, stderr=subprocess.STDOUT)
        wait_for(lambda: "window id" in run(["xprop", "-root", "_NET_SUPPORTING_WM_CHECK"], check=False), "window manager")
        version = run([str(args.app), "--version"], timeout=20).strip()
        if not re.search(r"\bTeXstudio 4\.9\.9\b", version):
            raise RuntimeError("The official runtime did not report TeXstudio4.9.9")
        observed["version"] = version
        app = subprocess.Popen([str(args.app), "--start-always", "--no-session", "--config", str(work / "editor-config"), str(original)])

        def main_window():
            found = run(["xdotool", "search", "--onlyvisible", "--class", "[Tt]e[Xx]studio"], check=False).split()
            for window in found:
                pid_text = run(["xprop", "-id", window, "_NET_WM_PID"], check=False)
                match = re.search(r"=\s*(\d+)\s*$", pid_text)
                if not match:
                    continue
                try:
                    if os.getpgid(int(match[1])) == os.getpgrp():
                        if "baseline.tex" in run(["xdotool", "getwindowname", window], check=False):
                            return window
                except ProcessLookupError:
                    pass
            return None

        main_id = wait_for(main_window, "owned native TeXstudio window", seconds=25)
        run(["xdotool", "windowactivate", "--sync", main_id])
        root = wait_for(app_tree, "native Qt accessibility application", seconds=20)
        screenshot("01-editor.png")
        record_tree(root, output / "01-editor-tree.json")
        observed["initialWindowTitle"] = run(["xdotool", "getwindowname", main_id]).strip()

        def visible_modals():
            return [node for node in nodes(root) if showing(node) and
                    (node.get_role_name() in {"alert", "dialog", "file chooser"}
                     or node.get_state_set().contains(Atspi.StateType.MODAL))]

        def startup_notice():
            modals = visible_modals()
            if not modals:
                return None
            if len(modals) != 1:
                raise RuntimeError("Ambiguous native startup modals; leave them untouched")
            modal = modals[0]
            controls = [node for node in nodes(modal) if showing(node)]
            records = [{"name": node.get_name() or "", "role": node.get_role_name(),
                        "checked": node.get_state_set().contains(Atspi.StateType.CHECKED)}
                       for node in controls]
            return modal, controls, startup_notice_controls(records)

        notice, notice_controls, notice_proof = wait_for(
            startup_notice, "the observed missing-LaTeX startup notice", seconds=25)
        screenshot("01a-startup-notice.png")
        record_tree(notice, output / "01a-startup-notice-tree.json")
        observed["startupNotice"] = notice_proof
        click(notice_controls[notice_proof["okIndex"]])
        wait_for(lambda: not showing(notice), "native startup notice dismissal")
        if visible_modals():
            raise RuntimeError("Unexpected native modal after startup notice dismissal")
        observed["startupNotice"]["dismissed"] = True
        observed["startupNotice"]["checkboxClicked"] = False

        # Use the observed native View menu command, without a window-manager shortcut.
        run(["xdotool", "windowactivate", "--sync", main_id])
        click(wait_for(lambda: find(root, r"^View$", {"menu item"}), "native View menu"))
        focus_command = wait_for(lambda: find(root, r"^Focus Editor$", {"menu item"}), "native Focus Editor command")
        click(focus_command)

        def focused_editor():
            if visible_modals():
                raise RuntimeError("Unexpected native modal before editor input")
            if run(["xdotool", "getactivewindow"]).strip() != main_id:
                return None
            for node in nodes(root):
                if (showing(node) and node.get_role_name() in {"text", "unknown"}
                        and node.get_state_set().contains(Atspi.StateType.FOCUSED)):
                    return {"role": node.get_role_name(), "name": node.get_name() or "",
                            "nativeCommand": "View > Focus Editor", "activeWindow": main_id}
            return None

        observed["editorFocus"] = wait_for(focused_editor, "native editor focus after View > Focus Editor")
        screenshot("01b-editor-ready.png")
        record_tree(root, output / "01b-editor-ready-tree.json")
        # Seed a different clipboard value so an omitted editor copy cannot pass.
        clipboard("selection prerequisite sentinel")
        key("ctrl+Home", "ctrl+a", "ctrl+c")
        wait_for(lambda: run(["xclip", "-selection", "clipboard", "-out"]).encode("utf-8") == expected, "independent native full-buffer copy")
        copied = run(["xclip", "-selection", "clipboard", "-out"])
        if copied.encode("utf-8") != expected:
            raise RuntimeError("Independent native full-buffer copy differs from the complete fixture")
        key("Right")
        observed["fullBufferSha256"] = hashlib.sha256(copied.encode("utf-8")).hexdigest()

        # Qt's native Save As is Ctrl+Alt+S; Ctrl+Shift+S means Save All here.
        key("ctrl+alt+s")
        dialog = wait_for(lambda: find(root, r"Save As", {"dialog", "file chooser", "frame"}), "native Save As dialog")
        screenshot("02-save-dialog.png")
        record_tree(dialog, output / "02-save-dialog-tree.json")
        filename = wait_for(lambda: find(dialog, r"file\s*name", {"text", "entry"}), "native filename field")
        click(filename)
        key("ctrl+a")
        clipboard(str(saved))
        key("ctrl+v")
        wait_for(lambda: filename.get_text_iface().get_text(0, -1) == str(saved), "native Save As filename contents")
        save_button = wait_for(lambda: find(dialog, r"^Save$", {"push button"}), "native Save button")
        click(save_button)
        wait_for(lambda: saved.exists(), "fresh native save checkpoint")
        if saved.read_bytes() != expected:
            raise RuntimeError("Fresh native saved file differs from the full original fixture")
        (output / "native-saved.tex").write_bytes(saved.read_bytes())
        observed["nativeSave"] = True
        observed["nativeSavedSha256"] = hashlib.sha256(saved.read_bytes()).hexdigest()

        # Open the actual menu and dialog, not an imported configuration file.
        run(["xdotool", "windowactivate", "--sync", main_id])
        key("alt+c")
        wait_for(lambda: find(root, r"Edit.*Macros", {"menu item"}), "native Edit Macros menu item")
        screenshot("03-macro-menu.png")
        key("m")
        macro_dialog = wait_for(lambda: find(root, r"Edit User.*Tags|Edit Macros", {"dialog", "frame"}), "native macro editor dialog")
        screenshot("04-macro-editor.png")
        record_tree(macro_dialog, output / "04-macro-editor-tree.json")
        add_button = wait_for(lambda: find(macro_dialog, r"^Add$", {"push button"}), "native Add button")
        macro_tree = wait_for(lambda: find(macro_dialog, r".*", {"tree table"}), "native macro tree table")
        before_add = macro_rows(macro_tree)
        observed["macroAdd"] = {"before": before_add}
        click(add_button)

        def observe_added_row():
            after_add = macro_rows(macro_tree)
            observed["macroAdd"]["after"] = after_add
            return observed_added_row(before_add, after_add)

        added = wait_for(observe_added_row, "one new selected checked native macro row after Add")
        observed["macroAdd"]["proof"] = added
        script_radio = wait_for(lambda: find(macro_dialog, r"^Script$", {"radio button"}), "native Script radio")
        click(script_radio)
        wait_for(lambda: script_radio.get_state_set().contains(Atspi.StateType.CHECKED), "native Script selection")
        after_script = macro_rows(macro_tree)
        if after_script["selectedRows"] != [added["rowIndex"]] or not after_script["rows"][added["rowIndex"]]["checked"]:
            raise RuntimeError("Script was not selected on the newly added checked macro row")
        observed["macroAdd"]["afterScript"] = after_script
        wait_for(lambda: find(macro_dialog, r"Shortcut", {"label"}), "native Shortcut label")
        wait_for(lambda: find(macro_dialog, r"^Name$", {"label"}), "native Name label")
        screenshot("05-script-controls.png")
        record_tree(macro_dialog, output / "05-script-controls-tree.json")
        observed["addAndScriptControls"] = True
        cancel_button = wait_for(lambda: find(macro_dialog, r"^Cancel$", {"push button"}), "native macro editor Cancel button")
        click(cancel_button)
        wait_for(lambda: not showing(macro_dialog), "native macro editor dismissal")
        screenshot("06-editor-return.png")
        if saved.read_bytes() != expected:
            raise RuntimeError("The control probe unexpectedly changed saved user content")
        run(["xdotool", "windowactivate", "--sync", main_id])
        key("ctrl+q")
        wait_for(lambda: not run(["xdotool", "getwindowname", main_id], check=False), "native application window close")
        app.wait(timeout=15)
        if app.returncode:
            raise RuntimeError("Native application did not close normally")
        observed["status"] = "native menu, Add/Script controls and independent Save As observed; wrapping not tested"
    finally:
        try:
            screenshot("last-screen.png")
            record_tree(desktop, output / "last-tree.json")
        except Exception as error:
            observed["finalObservationError"] = str(error)
        for child in (app, wm, *clipboard_owners):
            if child and child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
        (output / "native-observations.json").write_text(json.dumps(observed, ensure_ascii=False, indent=2) + "\n")
        print(observed["status"], flush=True)


if __name__ == "__main__":
    main()
