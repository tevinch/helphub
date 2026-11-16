"""Scripted real-PTY checks for the standalone Ruby app console."""

import errno
import os
from pathlib import Path
import pty
import re
import select
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUBY = os.environ.get("RUBY", "ruby")
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class Terminal:
    def __init__(self, args):
        self.output = b""
        self.tmp = tempfile.TemporaryDirectory(prefix="console-check-")
        rc = Path(self.tmp.name) / "irbrc"
        rc.write_text(
            "IRB.conf[:SAVE_HISTORY] = 0\n"
            "IRB.conf[:USE_COLORIZE] = false\n"
            "IRB.conf[:PROMPT_MODE] = :SIMPLE\n"
        )
        env = dict(os.environ, TERM="dumb", NO_COLOR="1", IRBRC=str(rc))
        self.master, slave = pty.openpty()
        self.process = subprocess.Popen(
            [RUBY, "-rbundler/setup", "app.rb", *args],
            cwd=ROOT,
            env=env,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            start_new_session=True,
        )
        os.close(slave)

    @property
    def text(self):
        return ANSI.sub("", self.output.decode(errors="replace")).replace("\r", "")

    def send(self, command):
        self.read_until(r">> \Z")
        os.write(self.master, (command + "\n").encode())

    def read_until(self, pattern, timeout=12):
        deadline = time.monotonic() + timeout
        while True:
            if re.search(pattern, self.text, re.MULTILINE):
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(f"Timed out waiting for {pattern!r}:\n{self.text}")
            if select.select([self.master], [], [], min(remaining, 0.1))[0]:
                try:
                    data = os.read(self.master, 65536)
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    data = b""
                if not data:
                    raise AssertionError(f"Terminal closed before {pattern!r}:\n{self.text}")
                self.output += data

    def finish(self, completion):
        self.read_until(completion, timeout=12)
        self.process.wait(timeout=12)
        # Drain the PTY after process exit, including any final diagnostic.
        while select.select([self.master], [], [], 0)[0]:
            try:
                data = os.read(self.master, 65536)
            except OSError as exc:
                if exc.errno != errno.EIO:
                    raise
                break
            if not data:
                break
            self.output += data
        return self.process.returncode

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        os.close(self.master)
        self.tmp.cleanup()


class ConsoleTest(unittest.TestCase):
    def test_inspect_mutate_return_and_reenter(self):
        args = ["console", "--twice", "--keep", "demo"]
        terminal = Terminal(args)
        try:
            terminal.read_until(r"^CONSOLE session=1$")
            terminal.send('puts ["VALUE", app.value].join(":")')
            terminal.read_until(r"^VALUE:2$")
            # A failing manual assertion must not be mistaken for a passed check.
            terminal.send('raise "incorrect doubled value" unless app.doubled == 4; puts "CHECK:" + (2 + 2).to_s')
            terminal.read_until(r"^CHECK:4$")
            terminal.send('puts ["ARGS", ARGV.inspect].join(":")')
            terminal.read_until(r'^ARGS:\["console", "--twice", "--keep", "demo"\]$')
            terminal.send('app.add(3); local_note = "edited"; puts ["MUTATED", app.value, local_note].join(":")')
            terminal.read_until(r"^MUTATED:5:edited$")
            terminal.send("exit")
            terminal.read_until(r'^RESUMED session=1 value=5 note=edited argv=\["console", "--twice", "--keep", "demo"\]$')
            terminal.read_until(r"^CONSOLE session=2$")
            terminal.send('raise "incorrect second value" unless app.doubled == 10; puts ["REENTRY", app.value, local_note].join(":")')
            terminal.read_until(r"^REENTRY:5:edited$")
            terminal.send('app.add(-1); local_note = "again"; puts ["MUTATED", app.value, local_note].join(":")')
            terminal.read_until(r"^MUTATED:4:again$")
            terminal.send("exit")
            terminal.read_until(r'^RESUMED session=2 value=4 note=again argv=\["console", "--twice", "--keep", "demo"\]$')
            self.assertEqual(terminal.finish(r"^COMPLETE value=4 note=again argv=\[.*\]$"), 0, terminal.text)
            self.assertNotRegex(terminal.text, r"NameError|RuntimeError|SyntaxError|LoadError|NoMethodError")
            self.assertEqual(terminal.text.count("RESUMED session="), 2, terminal.text)
        finally:
            transcript = os.environ.get("CONSOLE_TRANSCRIPT")
            if transcript:
                Path(transcript).write_text(terminal.text)
            terminal.close()

    def test_default_console_returns_after_one_session(self):
        terminal = Terminal(["console", "--keep", "demo"])
        try:
            terminal.read_until(r"^CONSOLE session=1$")
            terminal.send('puts ["DEFAULT", app.value, local_note].join(":")')
            terminal.read_until(r"^DEFAULT:2:ready$")
            terminal.send("exit")
            self.assertEqual(
                terminal.finish(r'^COMPLETE value=2 note=ready argv=\["console", "--keep", "demo"\]$'),
                0,
                terminal.text,
            )
            self.assertEqual(terminal.text.count("RESUMED session="), 1, terminal.text)
            self.assertNotIn("CONSOLE session=2", terminal.text)
        finally:
            terminal.close()

    def test_normal_status_does_not_open_console(self):
        result = subprocess.run(
            [RUBY, "-rbundler/setup", "app.rb", "status"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=12,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "STATUS value=2 doubled=4\n")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
