"""Small deterministic stdio LSP server for completion acceptance checks."""

import json
import sys

log_path = sys.argv[1]
supports_completion = sys.argv[2] == "completion"


def send(message):
    data = json.dumps(message).encode()
    sys.stdout.buffer.write(f"Content-Length: {len(data)}\r\n\r\n".encode() + data)
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
    with open(log_path, "a") as log:
        log.write(json.dumps(message) + "\n")
    method = message.get("method")
    if method == "exit":
        break
    if "id" not in message:
        continue
    result = None
    if method == "initialize":
        capabilities = {"textDocumentSync": 1}
        if supports_completion:
            capabilities["completionProvider"] = {"triggerCharacters": ["."]}
        result = {"capabilities": capabilities}
    elif method == "textDocument/completion":
        result = {
            "isIncomplete": False,
            "items": [{"label": "alpha", "kind": 6}, {"label": "beta", "kind": 6}],
        }
    send({"jsonrpc": "2.0", "id": message["id"], "result": result})
