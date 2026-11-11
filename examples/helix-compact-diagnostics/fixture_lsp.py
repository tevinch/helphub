#!/usr/bin/env python3
"""An inert stdio language server used only by the terminal acceptance test."""
import json
import os
import sys
from pathlib import Path

events = Path(os.environ['FIXTURE_EVENTS'])
documents = {}
revisions = {}


def record(kind, payload):
    with events.open('a') as f:
        f.write(json.dumps({'kind': kind, 'payload': payload}) + '\n')


def send(message):
    body = json.dumps(message).encode()
    sys.stdout.buffer.write(f'Content-Length: {len(body)}\r\n\r\n'.encode() + body)
    sys.stdout.buffer.flush()


def publish(uri):
    text = documents[uri]
    diagnostics = [
        {'range': {'start': {'line': 0, 'character': 0}, 'end': {'line': len(text.splitlines()) - 1, 'character': 0}},
         'severity': 2, 'source': 'fixture', 'code': 'FILE_WARNING',
         'message': '\n'.join(f'LONG_FILE_WARNING r{revisions[uri]} line {n:02}: this useful diagnostic describes the whole file.' for n in range(1, 25))},
        {'range': {'start': {'line': 10, 'character': 0}, 'end': {'line': 10, 'character': 8}},
         'severity': 1, 'source': 'fixture', 'code': 'LOCAL_ERROR', 'message': 'LOCAL_ERROR remains available.'},
        {'range': {'start': {'line': 14, 'character': 0}, 'end': {'line': 14, 'character': 8}},
         'severity': 3, 'source': 'fixture', 'code': 'LOCAL_INFO', 'message': 'LOCAL_INFO remains available.'},
    ]
    send({'jsonrpc': '2.0', 'method': 'textDocument/publishDiagnostics', 'params': {'uri': uri, 'diagnostics': diagnostics}})
    record('publishDiagnostics', {'uri': uri, 'revision': revisions[uri], 'codes': [d['code'] for d in diagnostics], 'text': text})


while True:
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            sys.exit(0)
        if line in (b'\r\n', b'\n'):
            break
        key, value = line.decode().split(':', 1)
        headers[key.lower()] = value.strip()
    message = json.loads(sys.stdin.buffer.read(int(headers['content-length'])))
    method = message.get('method')
    params = message.get('params', {})
    if method:
        record(method, params)
    if method == 'initialize':
        send({'jsonrpc': '2.0', 'id': message['id'], 'result': {'capabilities': {'textDocumentSync': {'openClose': True, 'change': 1, 'save': {'includeText': True}}}, 'serverInfo': {'name': 'diagnostic-fixture', 'version': '1'}}})
    elif method == 'textDocument/didOpen':
        item = params['textDocument']
        documents[item['uri']] = item['text']
        revisions[item['uri']] = 0
        publish(item['uri'])
    elif method == 'textDocument/didChange':
        uri = params['textDocument']['uri']
        documents[uri] = params['contentChanges'][-1]['text']
        revisions[uri] += 1
        publish(uri)
    elif method == 'textDocument/didSave':
        record('savedText', {'uri': params['textDocument']['uri'], 'text': documents[params['textDocument']['uri']]})
    elif method == 'shutdown':
        send({'jsonrpc': '2.0', 'id': message['id'], 'result': None})
    elif method == 'exit':
        break
    elif 'id' in message:
        send({'jsonrpc': '2.0', 'id': message['id'], 'result': None})
