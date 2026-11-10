"""Exercise the copyable config through real Neovim input and stdio LSP."""

import argparse
import faulthandler
import json
import os
from pathlib import Path
import sys
import tempfile
import time

import pynvim


parser = argparse.ArgumentParser()
parser.add_argument("nvim")
parser.add_argument("--variant", choices=["current", "old", "disabled"], default="current")
parser.add_argument("--result")
args = parser.parse_args()
faulthandler.dump_traceback_later(20, exit=True)
root = Path(__file__).resolve().parents[1]


def wait_for(predicate, detail):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.02)
    raise AssertionError(detail)


with tempfile.TemporaryDirectory(prefix="completion-check-") as temp:
    temp = Path(temp)
    for key, folder in [("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"),
                        ("XDG_STATE_HOME", "state"), ("XDG_CACHE_HOME", "cache")]:
        os.environ[key] = str(temp / folder)
    nvim = pynvim.attach("child", argv=[args.nvim, "--embed", "--headless", "-u", "NONE", "-i", "NONE", "--noplugin"])
    report = {"variant": args.variant, "mode": "software-operated embedded/headless Neovim with attached UI", "steps": []}
    try:
        nvim.ui_attach(100, 40, rgb=True, ext_linegrid=True, ext_messages=True)
        report["version"] = nvim.exec_lua("return vim.version()")
        assert report["version"]["major"] == 0 and report["version"]["minor"] == 12 and report["version"]["patch"] == 6
        assert nvim.exec_lua("return type(vim.lsp.completion.trigger)") == "nil"
        assert nvim.exec_lua("return type(vim.lsp.completion.get)") == "function"
        nvim.command("set completeopt=menu,menuone,noselect")
        nvim.exec_lua("_G.attach_count=0; vim.api.nvim_create_autocmd('LspAttach', {callback=function() _G.attach_count=_G.attach_count+1 end})")
        config = (root / "manual-completion.lua").read_text()
        if args.variant == "old":
            config = config.replace("vim.lsp.completion.get()", "vim.lsp.completion.trigger()")
        elif args.variant == "disabled":
            config = config.replace("vim.lsp.completion.enable(true, client.id, event.buf, { autotrigger = false })", "-- completion.enable deliberately omitted by the absence control")
        nvim.exec_lua(config)
        workfile = temp / "sample.txt"
        workfile.write_text("keep: ")
        nvim.command(f"edit {workfile}")
        request_log = temp / "requests.jsonl"

        def requests():
            return [json.loads(line) for line in request_log.read_text().splitlines()] if request_log.exists() else []

        def completions():
            return [request for request in requests() if request.get("method") == "textDocument/completion"]

        client_id = nvim.exec_lua("return vim.lsp.start({name='local-completion-fixture',cmd=...,root_dir=vim.fn.getcwd()})", [sys.executable, str(root / "tests/lsp_fixture.py"), str(request_log), "completion"])
        assert client_id
        wait_for(lambda: nvim.exec_lua("return _G.attach_count") == 1, "LspAttach did not execute")
        wait_for(lambda: any(r.get("method") == "textDocument/didOpen" for r in requests()), "server did not receive didOpen")
        mapping = nvim.eval("maparg('<C-e>', 'i', 0, 1)")
        assert mapping.get("buffer") == 1, "Ctrl-E must be buffer-local"
        report["steps"].append("initialize, didOpen, LspAttach and buffer-local Ctrl-E independently observed")

        nvim.input("Aalp")
        wait_for(lambda: nvim.current.line == "keep: alp" and nvim.eval("mode()") == "i", "typing did not enter the original prefix")
        time.sleep(0.15)
        assert not completions(), "typing triggered an LSP request despite autotrigger=false"
        assert nvim.eval("pumvisible()") == 0
        nvim.input("<C-e>")
        wait_for(lambda: nvim.eval("pumvisible()") == 1, "manual keypress did not produce a completion popup; " + nvim.eval("v:errmsg"))
        menu = nvim.eval("complete_info(['items','selected'])")
        assert "alpha" in [item["word"] for item in menu["items"]]
        first = completions()
        assert len(first) == 1 and first[0]["params"]["context"]["triggerKind"] == 1
        nvim.input("<C-n><C-y>.")
        wait_for(lambda: nvim.current.line == "keep: alpha.", "accept did not preserve the prefix and allow continued typing")
        time.sleep(0.15)
        assert len(completions()) == 1, "server trigger character caused an automatic request"
        report["steps"].append("typed prefix without request; Ctrl-E requested Invoked completion; popup alpha accepted; continued typing preserved keep: alpha.")

        nvim.input("<CR>bet")
        wait_for(lambda: nvim.current.line == "bet", "second prefix missing")
        nvim.input("<C-e>")
        wait_for(lambda: nvim.eval("pumvisible()") == 1, "second manual completion popup missing")
        assert "beta" in [item["word"] for item in nvim.eval("complete_info(['items'])")["items"]]
        nvim.input("<C-n><C-y>!<Esc>")
        wait_for(lambda: list(nvim.current.buffer[:]) == ["keep: alpha.", "beta!"] and nvim.eval("mode()") == "n", "repeat acceptance or continued edit failed")
        nvim.command("write")
        assert workfile.read_text() == "keep: alpha.\nbeta!\n"
        nvim.command("edit!")
        assert list(nvim.current.buffer[:]) == ["keep: alpha.", "beta!"]
        report["steps"].append("second Ctrl-E accepted beta; continued edit, save and reopen retained both complete lines")

        nvim.command("enew")
        assert not nvim.eval("maparg('<C-e>', 'i', 0, 1)"), "recipe leaked into a buffer without LSP"
        before = nvim.exec_lua("return _G.attach_count")
        no_completion_log = temp / "no-completion.jsonl"
        nvim.exec_lua("return vim.lsp.start({name='no-completion-fixture',cmd=...,root_dir=vim.fn.getcwd()})", [sys.executable, str(root / "tests/lsp_fixture.py"), str(no_completion_log), "none"])
        wait_for(lambda: nvim.exec_lua("return _G.attach_count") == before + 1, "no-completion client never attached")
        assert not nvim.eval("maparg('<C-e>', 'i', 0, 1)"), "recipe mapped Ctrl-E for a client without completion support"
        report["steps"].append("unrelated buffer and attached non-completion server retain their own Ctrl-E behavior")
        report["completion_requests"] = completions()
        assert len(report["completion_requests"]) == 2
        report["result"] = "pass"
    except Exception as error:
        report["result"] = "fail"
        report["error"] = str(error)
        try:
            report["messages"] = nvim.command_output("messages")
            report["completion_requests"] = completions()
        except Exception:
            pass
    finally:
        try:
            nvim.command("qa!")
        except (EOFError, OSError):
            pass
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.result:
        Path(args.result).write_text(output + "\n")
    print(output)
    sys.exit(0 if report["result"] == "pass" else 1)
