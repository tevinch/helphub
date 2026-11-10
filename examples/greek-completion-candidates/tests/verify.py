"""Check Greek popup filtering and acceptance in real stable Neovim."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time

import pynvim

parser = argparse.ArgumentParser()
parser.add_argument("nvim")
parser.add_argument("--omit-conversion", action="store_true")
parser.add_argument("--result")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]


def wait(predicate, detail):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError(detail)


def run(scenario):
    report = {"scenario": scenario, "omit_conversion": args.omit_conversion, "steps": []}
    with tempfile.TemporaryDirectory(prefix="greek-completion-") as temp:
        temp = Path(temp)
        for key in ["XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME"]:
            os.environ[key] = str(temp / key)
        nvim = pynvim.attach("child", argv=[args.nvim, "--embed", "--headless", "-u", "NONE", "-i", "NONE", "--noplugin"])
        wire_path = temp / "wire.jsonl"

        def wire():
            return [json.loads(line) for line in wire_path.read_text().splitlines()] if wire_path.exists() else []

        def requests():
            return [entry["message"] for entry in wire() if entry["direction"] == "in" and entry["message"].get("method") == "textDocument/completion"]

        def menu():
            information = nvim.eval("complete_info(['items','matches','selected'])")
            information["items"] = [item for item in information["items"] if item["match"]]
            return information

        def words():
            return [item["word"] for item in menu()["items"]]

        def invoke():
            nvim.input("<C-e>")
            wait(lambda: nvim.eval("pumvisible()") == 1, "completion menu missing")

        def accept(suffix):
            index = words().index("λογία")
            nvim.input("<C-n>" * (index + 1) + "<C-y>" + suffix)

        try:
            nvim.ui_attach(100, 40, rgb=True, ext_linegrid=True, ext_messages=True)
            version = nvim.exec_lua("return vim.version()")
            assert (version["major"], version["minor"], version["patch"]) == (0, 12, 6)
            report["version"] = version
            nvim.command("set completeopt=menu,menuone,noselect")
            original_completeopt = nvim.eval("&completeopt")
            report["completeopt"] = original_completeopt
            nvim.exec_lua("_G.attaches=0; _G.converted={}; _G.compared=0; _G.options={autotrigger=true,convert=function(item) table.insert(_G.converted,item.label); return {abbr='display:'..item.label,menu='existing converter'} end}; if ... then _G.options.cmp=function(a,b) _G.compared=_G.compared+1; return a.user_data.nvim.lsp.completion_item.data.rank>b.user_data.nvim.lsp.completion_item.data.rank end end", scenario == "callbacks")
            if not args.omit_conversion:
                nvim.exec_lua("_G.options=assert(loadfile(...))(_G.options)", str(root / "conversion.lua"))
            nvim.exec_lua("vim.api.nvim_create_autocmd('LspAttach',{callback=function(event) _G.attaches=_G.attaches+1; vim.lsp.completion.enable(true,event.data.client_id,event.buf,_G.options); vim.keymap.set('i','<C-e>',vim.lsp.completion.get,{buffer=event.buf}) end})")
            sample = temp / "sample.txt"
            sample.write_text("original header\nkeep: ")
            nvim.command(f"edit {sample}")
            nvim.exec_lua("return vim.lsp.start({name='greek-fixture',cmd=...,root_dir=vim.fn.getcwd()})", [sys.executable, str(root / "tests/lsp_fixture.py"), str(wire_path), scenario])
            wait(lambda: nvim.exec_lua("return _G.attaches") == 1, "LspAttach did not run")
            wait(lambda: any(e["message"].get("method") == "textDocument/didOpen" for e in wire()), "server did not receive didOpen")
            nvim.current.window.cursor = (2, len("keep: ".encode()) - 1)

            if scenario in ("cached", "incomplete"):
                nvim.input("Aλογ")
                wait(lambda: nvim.eval("pumvisible()") == 1, "autotrigger=true did not request the advertised Greek trigger character")
                before = len(requests())
                assert before == 1 and requests()[0]["params"]["context"]["triggerKind"] == 2
                nvim.input("ι")
                wait(lambda: nvim.current.line == "keep: λογι", "continued Greek prefix missing")
                if scenario == "incomplete":
                    wait(lambda: len(requests()) == before + 1, "incomplete list did not trigger a fresh request")
                    wait(lambda: nvim.exec_lua("return #_G.converted") >= 4, "fresh incomplete response was not converted")
                    assert requests()[-1]["params"]["context"]["triggerKind"] == 3
                else:
                    time.sleep(0.15)
                    assert len(requests()) == before, "complete list unexpectedly re-requested while narrowing"
                report["steps"].append("advertised Greek character triggered completion; continued prefix distinguished cached list from incomplete re-request")
            else:
                prefix = "cafe" if scenario == "ascii-limit" else "λογι"
                nvim.input("A" + prefix)
                wait(lambda: nvim.current.line == "keep: " + prefix, "initial prefix missing")
                assert not requests(), "unexpected automatic request"
                invoke()

            assert nvim.eval("&completeopt") == original_completeopt
            assert nvim.exec_lua("return _G.options.autotrigger") is True
            report["visible_matches"] = words()
            if scenario == "ascii-limit":
                assert "café" not in words() and "cafeteria" in words(), "ASCII counterexample no longer establishes the earlier Lua-filter limitation"
                report["steps"].append("ASCII prefix cafe still drops café before conversion; no universal bypass claim")
            else:
                observed_words = words()
                assert "λογία" in observed_words, "accented λογία missing from actual menu after prefix λογι"
                assert "λογια" in observed_words
                assert observed_words[0] == ("λογια" if scenario == "callbacks" else "λογία"), "existing/default ordering changed"
                candidate = next(item for item in menu()["items"] if item["word"] == "λογία")
                assert candidate["abbr"] == "display:λογία" and candidate["menu"] == "existing converter"
                original_item = candidate["user_data"]["nvim"]["lsp"]["completion_item"]
                assert original_item["data"] == {"source": "ranked-word", "rank": 0}
                assert original_item["textEdit"]["newText"] == "λογία"
                if scenario == "callbacks":
                    assert nvim.exec_lua("return _G.compared") > 0
                accept("!")
                wait(lambda: nvim.current.line == "keep: λογία!", "accepted Unicode textEdit did not replace the full prefix and permit continued editing")
                report["steps"].append("accented candidate present; original item/textEdit and caller converter preserved; accepted exact Unicode and continued editing")

                if scenario in ("cached", "incomplete"):
                    nvim.input("<CR>πριν: λογ")
                    wait(lambda: nvim.eval("pumvisible()") == 1, "repeat automatic completion missing")
                    count_before_edit = len(requests())
                    nvim.input("ι")
                    wait(lambda: nvim.current.line == "πριν: λογι", "second edited prefix missing")
                    if scenario == "incomplete":
                        wait(lambda: len(requests()) == count_before_edit + 1, "repeat incomplete response missing")
                        wait(lambda: nvim.exec_lua("return #_G.converted") >= 8, "repeat incomplete response not converted")
                    else:
                        time.sleep(0.15)
                        assert len(requests()) == count_before_edit
                else:
                    nvim.input("<CR>πριν: λογι")
                    wait(lambda: nvim.current.line == "πριν: λογι", "second edited prefix missing")
                    invoke()
                assert "λογία" in words(), "accented candidate absent after continued editing"
                accept("?")
                nvim.input("<Esc>")
                wait(lambda: nvim.eval("mode()") == "n", "failed to leave insert mode")
                expected = ["original header", "keep: λογία!", "πριν: λογία?"]
                assert list(nvim.current.buffer[:]) == expected
                nvim.command("write")
                nvim.command("edit!")
                assert list(nvim.current.buffer[:]) == expected
                assert sample.read_text() == "original header\nkeep: λογία!\nπριν: λογία?\n"
                assert nvim.eval("&completeopt") == original_completeopt
                report["steps"].append("repeated after editing a new Greek prefix; save/reopen preserved header and both complete Unicode lines")
                nvim.command("enew")
                assert not nvim.eval("maparg('<C-e>', 'i', 0, 1)"), "completion setup leaked to an unrelated buffer"
            report["result"] = "pass"
        except Exception as error:
            report["result"] = "fail"
            report["error"] = str(error)
        finally:
            report["wire"] = wire()
            try:
                report["converter_calls"] = nvim.exec_lua("return _G.converted")
                report["messages"] = nvim.command_output("messages")
                nvim.command("qa!")
            except (EOFError, OSError):
                pass
    return report


reports = []
for scenario in ["fresh", "cached", "incomplete", "callbacks", "ascii-limit"]:
    report = run(scenario)
    reports.append(report)
    print(json.dumps({key: value for key, value in report.items() if key != "wire"}, ensure_ascii=False))
    if report["result"] != "pass":
        break
if args.result:
    Path(args.result).write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n")
sys.exit(0 if all(report["result"] == "pass" for report in reports) and len(reports) == 5 else 1)
