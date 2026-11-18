#!/usr/bin/env python3
"""Check native text selection on the disposable X11 desktop in the workflow.

Requires Linux, a fresh CI runner, Xvfb and a private D-Bus session. Never run
this against your normal desktop. All Byobu settings and sockets are temporary.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
from urllib.parse import unquote_to_bytes

TOKENS = ("COPYALPHA427", "COPYBRAVO638", "COPYCHARLIE951")
KEEP = "ORIGINAL CONTENT REMAINS"
PREFIX = "Existing recipient content\n"
INITIAL_CONFIG = "# Preserve this existing configuration.\nset -g status-left-length 41\nset -g mouse on\n"


def source_fixture(observation):
    """Render source text and record the actual launcher's exported context."""
    context = {"backend": os.environ.get("BYOBU_BACKEND"),
               "inside_tmux": bool(os.environ.get("TMUX")),
               "inside_screen": bool(os.environ.get("STY")),
               "config_dir": os.environ.get("BYOBU_CONFIG_DIR")}
    observation.write_text(json.dumps(context))
    print("\033[2J\033[H" + "\n".join((*TOKENS, KEEP)), flush=True)
    while True:
        time.sleep(1)


def recipient_fixture(destination):
    """Receive actual terminal input; do not insert source tokens here."""
    with destination.open("w", buffering=1) as received:
        received.write(PREFIX)
        print("Paste into this terminal, then press Enter.", flush=True)
        for line in sys.stdin:
            received.write(line)
            print("Received one line.", flush=True)


def desktop_context():
    """Reject accidental use outside the hosted workflow's new display/session.

    Environment checks are not a security boundary. Process ownership and
    ancestry are checked before importing AT-SPI or sending desktop input.
    """
    if not (sys.platform == "linux" and os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
            and os.environ.get("RUNNER_OS") == "Linux"
            and os.environ.get("RUNNER_TEMP")):
        raise SystemExit("Requires the hosted Linux/Xvfb workflow; no desktop check ran.")
    root = Path(os.environ.get("SELECTION_DESKTOP_ROOT", "/nonexistent")).resolve()
    if root.parent != Path(os.environ["RUNNER_TEMP"]).resolve() or not root.name.startswith("selection-desktop."):
        raise SystemExit("Missing workflow-owned desktop tree; no desktop check ran.")
    expected = {"HOME": "profile", "XDG_CONFIG_HOME": "config", "XDG_CACHE_HOME": "cache",
                "XDG_DATA_HOME": "data", "XDG_STATE_HOME": "state", "XDG_RUNTIME_DIR": "runtime"}
    for name, suffix in ((None, ""), *expected.items()):
        path = root / suffix
        if (name and os.environ.get(name) != str(path)) or path.is_symlink():
            raise SystemExit("Desktop profile paths do not match the workflow tree.")
        info = path.stat()
        if not path.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise SystemExit("Desktop profile directory ownership/permissions mismatch.")
    if any(os.environ.get(name) for name in ("AT_SPI_BUS_ADDRESS", "SESSION_MANAGER", "WAYLAND_DISPLAY")):
        raise SystemExit("Inherited desktop-session pointer present; no desktop check ran.")

    def process(pid):
        proc = Path("/proc") / str(pid)
        args = proc.joinpath("cmdline").read_bytes().rstrip(b"\0").split(b"\0")
        parent = int(re.search(r"^PPid:\s+(\d+)", proc.joinpath("status").read_text(), re.M)[1])
        if proc.stat().st_uid != os.getuid():
            raise SystemExit("Desktop service is not owned by the workflow user.")
        return args, parent

    ancestors, current = set(), os.getpid()
    while current > 1:
        ancestors.add(current)
        current = int(re.search(r"^PPid:\s+(\d+)", Path(f"/proc/{current}/status").read_text(), re.M)[1])
    display = os.environ.get("DISPLAY", "")
    if not re.fullmatch(r":\d+", display):
        raise SystemExit("Expected the workflow's local Xvfb display.")
    xargs, xparent = process(int(Path(f"/tmp/.X{display[1:]}-lock").read_text().strip()))
    authority = root / "runtime" / "Xauthority"
    if (Path(os.fsdecode(xargs[0])).name != "Xvfb" or xparent not in ancestors
            or display.encode() not in xargs or b"-auth" not in xargs
            or xargs[xargs.index(b"-auth") + 1] != os.fsencode(authority)
            or os.environ.get("XAUTHORITY") != str(authority) or authority.is_symlink()
            or authority.stat().st_uid != os.getuid() or authority.stat().st_mode & 0o077):
        raise SystemExit("Xvfb process or private authority file does not match the workflow.")
    # Check the local bus peer's process, without importing a desktop client.
    address = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "").split(";", 1)[0]
    kind, _, fields = address.partition(":")
    values = dict(field.split("=", 1) for field in fields.split(",") if "=" in field)
    if kind != "unix" or not ({"path", "abstract"} & values.keys()):
        raise SystemExit("Expected the workflow's private Unix D-Bus session.")
    endpoint = unquote_to_bytes(values["path"]) if "path" in values else b"\0" + unquote_to_bytes(values["abstract"])
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
        peer.settimeout(3)
        peer.connect(endpoint)
        bus_pid, bus_uid, _ = struct.unpack("3i", peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    bus_args, bus_parent = process(bus_pid)
    parent_args, _ = process(bus_parent)
    if (bus_uid != os.getuid() or Path(os.fsdecode(bus_args[0])).name != "dbus-daemon"
            or bus_parent not in ancestors or Path(os.fsdecode(parent_args[0])).name != "dbus-run-session"):
        raise SystemExit("D-Bus process does not belong to this workflow session.")
    return root


def run_desktop(output):
    desktop_root = desktop_context()
    import pyatspi
    from PIL import ImageGrab

    for tool in ("byobu-tmux", "tmux", "xfce4-terminal", "xdotool", "xclip", "xprop"):
        if not shutil.which(tool):
            raise SystemExit(f"Missing dependency: {tool}")
    # Byobu's distro dirs script can reuse its /dev/shm cache. Refuse an
    # existing cache rather than reading or deleting somebody else's state.
    existing = list(Path("/dev/shm").glob(f"byobu-{os.environ['USER']}-*"))
    if existing:
        raise SystemExit("Requires a fresh runner with no existing Byobu runtime cache.")

    output.mkdir(parents=True, exist_ok=False)
    report = {"status": "running", "checks": [], "transfers": []}
    processes, logs = [], []
    scratch = tempfile.TemporaryDirectory(prefix="selection-case-", dir=desktop_root)
    work = Path(scratch.name)
    profile = Path(os.environ["HOME"])
    config = profile / ".byobu"
    config.mkdir(parents=True)
    runtime = work / "runtime"
    runtime.mkdir(mode=0o700)
    tmux_tmp = work / "tmux"
    tmux_tmp.mkdir(mode=0o700)
    socket = work / "selection.socket"
    observed = work / "observed.json"
    recipient = work / "received.txt"
    config_file = config / ".tmux.conf"
    config_file.write_text(INITIAL_CONFIG)
    unrelated_file = profile / "unrelated-note.txt"
    unrelated_file.write_bytes(b"A separate existing note.\nKeep its second line too.\n")
    unrelated_before = unrelated_file.read_bytes()
    report["unrelated_before"] = unrelated_before.decode()
    env = {name: os.environ[name] for name in
           ("DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS", "USER", "LOGNAME", "HOME",
            "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_RUNTIME_DIR",
            "XDG_CONFIG_DIRS", "XDG_DATA_DIRS")
           if name in os.environ}
    env.update(PATH="/usr/bin:/bin", LANG="C.UTF-8", BYOBU_CONFIG_DIR=str(config), BYOBU_RUN_DIR=str(runtime),
               BYOBU_PREFIX="/usr", BYOBU_BACKEND="tmux", BYOBU_NO_TITLE="1", SHELL="/bin/sh",
               TMUX_TMPDIR=str(tmux_tmp), NO_AT_BRIDGE="0", GDK_BACKEND="x11",
               GTK_MODULES="gail:atk-bridge")

    def command(*parts, check=True):
        result = subprocess.run([str(x) for x in parts], env=env, capture_output=True,
                                text=True, check=check, timeout=15)
        return result.stdout.rstrip("\n")

    def tmux(*parts, check=True):
        return command("tmux", "-S", socket, *parts, check=check)

    def require(condition, description):
        if not condition:
            raise AssertionError(description)
        report["checks"].append(description)

    def save_report():
        pending = output / "result.tmp"
        pending.write_text(json.dumps(report, indent=2) + "\n")
        pending.replace(output / "result.json")

    def diagnostic_state(case, stage, text):
        """Observe owned fixture state without changing selection or acceptance."""
        snapshot = {"stage": stage}

        def observe(*parts):
            try:
                result = subprocess.run([str(x) for x in parts], env=env, capture_output=True,
                                        text=True, timeout=4)
                return {"returncode": result.returncode, "stdout": result.stdout[:2048],
                        "stderr": result.stderr[:2048]}
            except Exception as exc:
                return {"error": repr(exc)}

        snapshot["clipboard"] = observe("xclip", "-selection", "clipboard", "-o")
        snapshot["mouse"] = observe("tmux", "-S", socket, "show-options", "-gqv", "mouse")
        fields = ("pane_in_mode", "pane_mode", "selection_present", "selection_active",
                  "selection_start_x", "selection_start_y", "selection_end_x", "selection_end_y",
                  "copy_cursor_x", "copy_cursor_y", "mouse_any_flag")
        snapshot["pane_fields"] = list(fields)
        snapshot["pane_state"] = observe("tmux", "-S", socket, "display-message", "-p",
                                         "-t", "selection:0.0", "|".join("#{" + x + "}" for x in fields))
        snapshot["buffers"] = observe("tmux", "-S", socket, "list-buffers", "-F",
                                      "#{buffer_name}|#{buffer_size}|#{buffer_sample}")
        snapshot["pointer"] = observe("xdotool", "getmouselocation", "--shell")
        try:
            count = text.getNSelections()
            selections = []
            for index in range(min(count, 4)):
                start, end = text.getSelection(index)
                selections.append({"start": start, "end": end, "text": text.getText(start, end)[:2048]})
            snapshot["atspi_selection"] = {"count": count, "selections": selections}
        except Exception as exc:
            snapshot["atspi_selection"] = {"error": repr(exc)}
        case["snapshots"].append(snapshot)
        save_report()
        print(json.dumps({"case": case["case"], "diagnostic": snapshot}), flush=True)

    def wait_for(probe, description, seconds=20):
        deadline, last = time.monotonic() + seconds, None
        while time.monotonic() < deadline:
            try:
                value = probe()
                if value:
                    return value
            except (RuntimeError, LookupError, subprocess.SubprocessError, OSError, json.JSONDecodeError) as exc:
                last = str(exc)
            time.sleep(.15)
        raise AssertionError(f"{description}: {last}")

    def launch_terminal(label, geometry, arguments):
        log = (output / f"{label}.stderr").open("w")
        logs.append(log)
        proc = subprocess.Popen(["xfce4-terminal", "--disable-server", "--hide-menubar",
                                 "--hide-toolbar", "--hide-scrollbar", "--font=Monospace 14",
                                 f"--title={label}", f"--geometry={geometry}", "-x", *arguments],
                                env=env, stdout=log, stderr=log)
        processes.append(proc)

        def window_for():
            for wid in command("xdotool", "search", "--onlyvisible", "--pid", proc.pid,
                               check=False).splitlines():
                if "_NET_WM_WINDOW_TYPE_NORMAL" in command("xprop", "-id", wid,
                                                           "_NET_WM_WINDOW_TYPE", check=False):
                    return wid
        return proc, wait_for(window_for, f"Visible {label} window")

    def descendants(node):
        yield node
        for index in range(node.childCount):
            yield from descendants(node.getChildAtIndex(index))

    def source_text(pid, token):
        for app in pyatspi.Registry.getDesktop(0):
            if app.get_process_id() != pid:
                continue
            for node in descendants(app):
                if node.getRole() == pyatspi.ROLE_TERMINAL:
                    text = node.queryText()
                    contents = text.getText(0, -1)
                    if token in contents:
                        return text, contents.index(token)

    def activate(wid):
        command("xdotool", "windowactivate", "--sync", wid)

    def baseline_clipboard():
        log = (output / "clipboard.stderr").open("a")
        logs.append(log)
        proc = subprocess.Popen(["xclip", "-selection", "clipboard", "-i", "-quiet"],
                                env=env, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log)
        processes.append(proc)
        # A distinct baseline prevents stale success from satisfying a new case.
        proc.stdin.write(b"UNCHANGED BASELINE")
        proc.stdin.close()
        wait_for(lambda: command("xclip", "-selection", "clipboard", "-o", check=False)
                 == "UNCHANGED BASELINE", "Fresh clipboard baseline")

    def transfer(source_proc, source_wid, target_wid, token, expected, label):
        diagnostic = {"case": label, "expected_transfer": expected, "snapshots": []}
        report.setdefault("diagnostics", []).append(diagnostic)
        baseline_clipboard()
        activate(source_wid)
        text, offset = wait_for(lambda: source_text(source_proc.pid, token), "Source accessibility text")
        first = text.getCharacterExtents(offset, pyatspi.DESKTOP_COORDS)
        last = text.getCharacterExtents(offset + len(token) - 1, pyatspi.DESKTOP_COORDS)
        diagnostic["coordinates"] = {"first_character": list(first), "last_character": list(last),
                                     "text_offset": offset, "text_length": len(token)}
        diagnostic_state(diagnostic, "before-drag", text)
        require(first[2] > 0 and first[3] > 0 and first[1] == last[1], "Visible single-line drag geometry")
        command("xdotool", "mousemove", "--sync", first[0] + 1, first[1] + first[3] // 2)
        command("xdotool", "mousedown", "1")
        try:
            for step in range(1, 9):
                end_x = last[0] + last[2] - 1
                command("xdotool", "mousemove", "--sync",
                        first[0] + 1 + (end_x - first[0] - 1) * step // 8,
                        first[1] + first[3] // 2)
                time.sleep(.04)
            diagnostic_state(diagnostic, "drag-held", text)
        finally:
            command("xdotool", "mouseup", "1")
        diagnostic_state(diagnostic, "after-drag", text)
        try:
            ImageGrab.grab().save(output / f"{label}-after-drag.png")
        except Exception as screenshot_error:
            diagnostic["after_drag_screenshot_error"] = repr(screenshot_error)
            save_report()
        command("xdotool", "key", "--clearmodifiers", "ctrl+shift+c")
        diagnostic_state(diagnostic, "after-copy-command", text)
        if expected:
            copied = wait_for(lambda: (value if (value := command("xclip", "-selection", "clipboard", "-o"))
                                      == token else None), "Terminal copied exact selected text")
        else:
            time.sleep(.3)
            copied = command("xclip", "-selection", "clipboard", "-o")
            diagnostic["copied_at_assertion"] = copied
            save_report()
            print(json.dumps({"case": label, "copied_at_assertion": copied}), flush=True)
            require(copied == "UNCHANGED BASELINE", "Mouse-on control cannot copy source token")
        previous = recipient.read_text()
        activate(target_wid)
        command("xdotool", "key", "--clearmodifiers", "ctrl+shift+v")
        command("xdotool", "key", "Return")
        wanted = previous + copied + "\n"
        wait_for(lambda: recipient.read_text() == wanted, "Second program received actual pasted input")
        require((token in recipient.read_text()) == expected,
                f"{label}: recipient content agrees with expected transfer")
        report["transfers"].append({"case": label, "mouse": tmux("show-options", "-gqv", "mouse"),
                                    "clipboard": copied, "recipient": recipient.read_text(),
                                    "drag_completed": True, "copy_and_paste_keys_completed": True})
        ImageGrab.grab().save(output / f"{label}.png")

    def start_source():
        observed.unlink(missing_ok=True)
        proc, wid = launch_terminal("Selection source", "80x16+20+20",
                                    ["byobu-tmux", "-S", str(socket), "new-session", "-s", "selection",
                                     sys.executable, str(Path(__file__).resolve()), "--source", str(observed)])
        context = wait_for(lambda: json.loads(observed.read_text()) if observed.exists() else None,
                           "Real Byobu source program started")
        require(context == {"backend": "tmux", "inside_tmux": True,
                            "inside_screen": False, "config_dir": str(config)}, "Actual Byobu tmux context")
        require(tmux("display-message", "-p", "#{socket_path}") == str(socket), "Explicit owned tmux socket")
        require(tmux("show-options", "-gqv", "status-left-length") == "41", "Existing config actually loaded")
        wait_for(lambda: KEEP in tmux("capture-pane", "-p", "-t", "selection:0.0"), "Original pane content visible")
        return proc, wid

    try:
        report["versions"] = {"packages": command("dpkg-query", "-W", "-f=${Package} ${Version}\n",
                                                  "byobu", "tmux", "xfce4-terminal", "xclip"),
                              "python": sys.version}
        source_proc, source_wid = start_source()
        original_lines = tmux("capture-pane", "-p", "-t", "selection:0.0").splitlines()[:4]
        require(original_lines == [*TOKENS, KEEP], "All original source lines present")
        report["source_before"] = original_lines
        require(tmux("show-options", "-gqv", "mouse") == "on", "Mouse-on control loaded from config")
        _, target_wid = launch_terminal("Paste destination", "80x12+20+520",
                                        [sys.executable, str(Path(__file__).resolve()), "--recipient", str(recipient)])
        wait_for(lambda: recipient.exists() and recipient.read_text() == PREFIX, "Existing recipient content present")
        transfer(source_proc, source_wid, target_wid, TOKENS[0], False, "mouse-on-control")
        tmux("send-keys", "-t", "selection:0.0", "-X", "cancel", check=False)
        tmux("set-option", "-g", "mouse", "off")
        require(tmux("show-options", "-gqv", "mouse") == "off", "Immediate native mouse-off command ran")
        transfer(source_proc, source_wid, target_wid, TOKENS[0], True, "first-copy")
        transfer(source_proc, source_wid, target_wid, TOKENS[1], True, "repeated-copy")
        report["source_after"] = tmux("capture-pane", "-p", "-t", "selection:0.0").splitlines()[:4]
        require(report["source_after"] == original_lines, "All original pane content retained")
        report["unrelated_before_teardown"] = unrelated_file.read_text()
        require(unrelated_file.read_bytes() == unrelated_before, "Unrelated file retained before server teardown")
        require(config_file.read_text() == INITIAL_CONFIG, "Immediate command left config untouched")
        config_file.write_text(INITIAL_CONFIG + "\nset -g mouse off\n")
        retained_config = config_file.read_text()
        # Shutdown is restricted to the socket created inside this scratch tree.
        tmux("kill-server")
        source_proc.wait(timeout=10)
        wait_for(lambda: not socket.exists(), "Owned server stopped before new-server check")
        source_proc, source_wid = start_source()
        require(tmux("show-options", "-gqv", "mouse") == "off", "Fresh Byobu server loaded persistent override")
        transfer(source_proc, source_wid, target_wid, TOKENS[2], True, "fresh-server-copy")
        report["unrelated_after_restart"] = unrelated_file.read_text()
        require(unrelated_file.read_bytes() == unrelated_before, "Unrelated file retained after persistence check")
        require(config_file.read_text() == retained_config and retained_config.startswith(INITIAL_CONFIG),
                "Original config settings and comments retained")
        report["config_before"] = INITIAL_CONFIG
        report["config_after"] = config_file.read_text()
        require(len(report["transfers"]) == 4 and recipient.read_text().startswith(PREFIX),
                "All four complete transfers ran and existing recipient content remains")
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = repr(exc)
        save_report()
        print(json.dumps(report, indent=2), flush=True)
        try:
            ImageGrab.grab().save(output / "failure.png")
        except Exception as screenshot_error:
            report["failure_screenshot_error"] = repr(screenshot_error)
            save_report()
        raise
    finally:
        save_report()
        cleanup_errors = []
        try:
            if socket.exists():
                tmux("kill-server", check=False)
        except Exception as cleanup_error:
            cleanup_errors.append(repr(cleanup_error))
        for proc in reversed(processes):
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
            except Exception as cleanup_error:
                cleanup_errors.append(repr(cleanup_error))
        for log in logs:
            try:
                log.close()
            except Exception as cleanup_error:
                cleanup_errors.append(repr(cleanup_error))
        try:
            scratch.cleanup()
        except Exception as cleanup_error:
            cleanup_errors.append(repr(cleanup_error))
        if cleanup_errors:
            report["status"] = "failed"
            report["cleanup_errors"] = cleanup_errors
        save_report()
        print(json.dumps(report, indent=2), flush=True)
        if cleanup_errors:
            raise RuntimeError("Owned fixture cleanup failed; see result.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--output", type=Path)
    modes.add_argument("--source", type=Path, help=argparse.SUPPRESS)
    modes.add_argument("--recipient", type=Path, help=argparse.SUPPRESS)
    options = parser.parse_args()
    if options.source:
        source_fixture(options.source)
    elif options.recipient:
        recipient_fixture(options.recipient)
    else:
        run_desktop(options.output.resolve())
