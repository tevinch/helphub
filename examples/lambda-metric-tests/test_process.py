"""Check the complete process, including the real tracer's exit handlers."""
import json
import os
from pathlib import Path
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
import time

import pytest


@pytest.fixture
def trace_receiver():
    class Receiver(ThreadingHTTPServer):
        daemon_threads = True

        def get_request(self):
            connection, address = super().get_request()
            self.connections.append(address)
            return connection, address

    class Handler(BaseHTTPRequestHandler):
        def parse_request(self):
            ok = super().parse_request()
            if ok:
                self.server.requests.append((self.command, self.path))
            return ok

        def do_GET(self):
            self.server.info_requested.set()
            self.server.release_info.wait(timeout=10)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                self.wfile.write(b'{"endpoints":["/v0.4/traces","/v0.5/traces"]}')
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.server.paths.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *_args):
            pass

    server = Receiver(("127.0.0.1", 0), Handler)
    server.connections = []
    server.paths = []
    server.requests = []
    server.info_requested = Event()
    server.release_info = Event()
    server.release_info.set()
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.release_info.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def run_probe(tmp_path, receiver, *, tracing, run_tests=False, audit_control=False):
    audit_file = tmp_path / "network-attempts.json"
    env = os.environ.copy()
    env.update({
        "DD_TRACE_ENABLED": "true" if tracing else "false",
        "DD_INSTRUMENTATION_TELEMETRY_ENABLED": "false",
        "DD_REMOTE_CONFIGURATION_ENABLED": "false",
        "DD_FLUSH_TO_LOG": "true",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "DD_TRACE_AGENT_URL": f"http://127.0.0.1:{receiver.server_port}",
        "NETWORK_AUDIT_FILE": str(audit_file),
    })
    start = time.monotonic()
    child = subprocess.run(
        [sys.executable, "process_probe.py", *(["--pytest"] if run_tests else []),
         *(["--audit-control"] if audit_control else [])],
        cwd=Path(__file__).parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
    )
    elapsed = time.monotonic() - start
    assert child.returncode == 0, child.stdout + child.stderr
    assert audit_file.is_file(), "The audit hook never persisted its evidence"
    return child, json.loads(audit_file.read_text()), elapsed


def test_enabled_trace_control_reaches_the_independent_receiver(tmp_path, trace_receiver):
    # This fails if the probe never creates a real span or the receiver is inert.
    child, _attempts, _elapsed = run_probe(tmp_path, trace_receiver, tracing=True)
    assert trace_receiver.connections
    assert any(path.startswith("/v0.") for path in trace_receiver.paths)
    assert "PROBE_OK" in child.stdout


def test_disabled_tracer_runs_metric_tests_without_delivery(tmp_path, trace_receiver):
    # Removing the before-start disable setting must produce a trace POST.
    child, attempts, elapsed = run_probe(
        tmp_path, trace_receiver, tracing=False, run_tests=True
    )
    assert "7 passed" in child.stdout
    assert attempts == []
    # ddtrace 4.16.1 may perform native GET /info during initialization even
    # when trace submission is disabled. Account for it rather than hide it.
    assert all(request == ("GET", "/info") for request in trace_receiver.requests)
    assert trace_receiver.paths == []
    assert "failed to send" not in child.stderr.lower()
    assert "dropping" not in child.stderr.lower()
    assert elapsed < 5


def test_disabled_tracer_exits_while_info_response_is_delayed(tmp_path, trace_receiver):
    # A responsive local receiver must not be hiding a shutdown timeout.
    trace_receiver.release_info.clear()
    child, attempts, elapsed = run_probe(tmp_path, trace_receiver, tracing=False)
    assert trace_receiver.info_requested.is_set()
    assert trace_receiver.paths == []
    assert attempts == []
    assert "PROBE_OK" in child.stdout
    assert "failed to send" not in child.stderr.lower()
    assert "dropping" not in child.stderr.lower()
    assert elapsed < 5


def test_disabled_tracer_exits_when_trace_endpoint_is_unavailable(tmp_path):
    import socket
    from types import SimpleNamespace

    # Reserve then release an unused loopback port. No external endpoint is used.
    with socket.socket() as unused:
        unused.bind(("127.0.0.1", 0))
        port = unused.getsockname()[1]
    child, attempts, elapsed = run_probe(
        tmp_path, SimpleNamespace(server_port=port), tracing=False
    )
    assert attempts == []
    assert "PROBE_OK" in child.stdout
    assert "failed to send" not in child.stderr.lower()
    assert "dropping" not in child.stderr.lower()
    assert elapsed < 5


def test_socket_audit_control_detects_python_network_attempt(tmp_path, trace_receiver):
    # Prove that the additional Python-level observer actually detects a connection.
    _child, attempts, _elapsed = run_probe(
        tmp_path, trace_receiver, tracing=False, audit_control=True
    )
    assert ("GET", "/audit-control") in trace_receiver.requests
    assert any(attempt["event"] == "socket.connect" for attempt in attempts)
