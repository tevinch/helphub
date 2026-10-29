"""Test helper launched only in a fresh, explicitly configured process."""
import atexit
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

attempts = []


def record_network(event, arguments):
    if event in {"socket.connect", "socket.sendto"}:
        attempts.append({"event": event, "address": str(arguments[1])})


sys.addaudithook(record_network)
# Registered before imports, so this runs after the tracer's exit handlers.
atexit.register(
    lambda: Path(os.environ["NETWORK_AUDIT_FILE"]).write_text(json.dumps(attempts))
)

# These are real installed release packages, with environment set by the parent.
import app_direct
import app_module
from ddtrace.trace import tracer

with tracer.trace("example.unit_test"):
    for app in (app_direct, app_module):
        target = app if app is app_direct else app.metric
        with patch.object(target, "lambda_metric", autospec=True) as metric:
            assert app.handler({"records": ["alpha", "beta"]}) == {"processed": 2}
            metric.assert_called_once_with("records.processed", 2, tags=["queue:example"])

if "--audit-control" in sys.argv:
    from urllib.request import urlopen
    with urlopen(os.environ["DD_TRACE_AGENT_URL"] + "/audit-control", timeout=2) as response:
        assert response.status == 200

if "--pytest" in sys.argv:
    import pytest
    raise SystemExit(pytest.main(["test_metrics.py", "-q", "-p", "no:ddtrace"]))

print("PROBE_OK")
