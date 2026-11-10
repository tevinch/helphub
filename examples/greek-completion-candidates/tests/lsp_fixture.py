"""Deterministic completion responses and an independent stdio wire log."""
import json
import sys

log_path, scenario = sys.argv[1:]
documents = {}


def record(direction, message):
    with open(log_path, "a") as log:
        log.write(json.dumps({"direction": direction, "message": message}, ensure_ascii=False) + "\n")


def send(message):
    record("out", message)
    payload = json.dumps(message).encode()
    sys.stdout.buffer.write(f"Content-Length: {len(payload)}\r\n\r\n".encode() + payload)
    sys.stdout.buffer.flush()


while True:
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            sys.exit(0)
        if line in (b"\r\n", b"\n"):
            break
        key, value = line.decode().split(":", 1)
        headers[key.lower()] = value.strip()
    message = json.loads(sys.stdin.buffer.read(int(headers["content-length"])))
    record("in", message)
    method, params = message.get("method"), message.get("params", {})
    if method == "exit":
        break
    if method == "textDocument/didOpen":
        documents[params["textDocument"]["uri"]] = params["textDocument"]["text"]
    elif method == "textDocument/didChange":
        documents[params["textDocument"]["uri"]] = params["contentChanges"][-1]["text"]
    if "id" not in message:
        continue
    result = None
    if method == "initialize":
        result = {"capabilities": {"textDocumentSync": 1, "completionProvider": {
            "triggerCharacters": ["γ"] if scenario in ("cached", "incomplete") else ["."]
        }}}
    elif method == "textDocument/completion":
        position = params["position"]
        line = documents[params["textDocument"]["uri"]].splitlines()[position["line"]]
        # All fixture characters are in the BMP: Python code points equal UTF-16 units.
        end = position["character"]
        start = line.rfind(" ", 0, end) + 1
        labels = ["café", "cafeteria"] if scenario == "ascii-limit" else ["λογία", "λογια"]
        result = {"isIncomplete": scenario == "incomplete", "items": [
            {"label": label, "kind": 6, "sortText": f"{index:03}",
             "data": {"source": "ranked-word", "rank": index},
             "textEdit": {"range": {"start": {"line": position["line"], "character": start},
                                       "end": position}, "newText": label}}
            for index, label in enumerate(labels)
        ]}
    send({"jsonrpc": "2.0", "id": message["id"], "result": result})
