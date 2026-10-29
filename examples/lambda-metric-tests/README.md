# Lambda metric tests

Restore `lambda_metric` assertions in bare pytest functions by patching the name your handler looks up. Configure local tracing before pytest starts to stop trace payload flushing during unit tests.

## Run the example

Use Python 3.10–3.14. This example was checked with Python 3.12.4, `datadog-lambda` 8.130.0, `ddtrace` 4.16.1 and pytest 9.1.1.

On macOS or Linux, from this directory:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
DD_TRACE_ENABLED=false \
DD_INSTRUMENTATION_TELEMETRY_ENABLED=false \
DD_REMOTE_CONFIGURATION_ENABLED=false \
DD_FLUSH_TO_LOG=true \
python -m pytest -q -p no:ddtrace
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
$env:DD_TRACE_ENABLED = "false"
$env:DD_INSTRUMENTATION_TELEMETRY_ENABLED = "false"
$env:DD_REMOTE_CONFIGURATION_ENABLED = "false"
$env:DD_FLUSH_TO_LOG = "true"
.\.venv\Scripts\python -m pytest -q -p no:ddtrace
```

These settings belong in the local test launcher. A fixture that sets them after importing the application can be too late; a pytest plugin can also import tracing before test fixtures run. `-p no:ddtrace` disables that pytest integration for this example. Keep the production configuration in the deployment.

`DD_FLUSH_TO_LOG=true` is used here only to keep the deliberately **wrong patch target** demonstration local: its unmocked custom metric is written to captured stdout. It does not disable metrics. The correctly patched tests never call a metric transport.

## Patch the lookup location

If the application uses a direct import:

```python
# app_direct.py
from datadog_lambda.metric import lambda_metric
```

Patch its local binding:

```python
from unittest.mock import patch
import app_direct

with patch.object(app_direct, "lambda_metric", autospec=True) as metric:
    assert app_direct.handler({"records": ["alpha", "beta"]}) == {"processed": 2}
    metric.assert_called_once_with("records.processed", 2, tags=["queue:example"])
```

If it imports the module:

```python
# app_module.py
import datadog_lambda.metric as metric
```

Patch the function on that module:

```python
import app_module

with patch.object(app_module.metric, "lambda_metric", autospec=True) as metric:
    assert app_module.handler({"records": ["alpha", "beta"]}) == {"processed": 2}
    metric.assert_called_once_with("records.processed", 2, tags=["queue:example"])
```

After a direct import, patching `datadog_lambda.metric.lambda_metric` does not replace the already-bound `app_direct.lambda_metric`. The negative-control test demonstrates that with the real metric function and captured log output. Each context manager restores its patch automatically.

The sample handler reports the number of input records. Tests cover a two-record batch, an empty batch, and a missing `records` key, where no success metric should be sent. Replace the example names, values and tags with your application's actual metric contract.

## Traces and process exit

A message containing `/v0.5/traces` comes from trace export. Mocking a custom metric call does not configure that exporter. `DD_TRACE_ENABLED=false` disables trace submission; the other two tracing settings disable instrumentation telemetry and remote configuration for these local checks.

The process tests use real installed packages and a local HTTP receiver. A trace-enabled control must submit a trace, proving the receiver can detect native export. With tracing disabled, a fresh child runs the metric tests, creates a real span and exits without a trace or telemetry submission. Separate checks hold the discovery response open and use an unavailable local endpoint; each child has a five-second deadline and must exit without a dropped-trace message.

**This is not a fully offline configuration.** With the pinned `ddtrace` 4.16.1 release, the native exporter can still request `GET /info` during initialization. The checks account for this discovery request explicitly. Python socket audit hooks do not see this native request, so the independent HTTP receiver is the primary export check. A separate local HTTP request verifies that the Python audit hook also detects connections. In one measured run, the normal and unavailable-endpoint children exited in about 0.2 seconds; holding `/info` open still added about 3.2 seconds with this release. The settings therefore do not guarantee zero discovery latency. No AWS account or Datadog ingestion is used.

Scripted verification: **12 tests passed** on macOS with the versions above. The tests check local application behavior and process exit; the reporter's application and deployment have not been validated.

## References

- Python's [where to patch](https://docs.python.org/3/library/unittest.mock.html#where-to-patch) guidance.
- Datadog's [tracing configuration](https://ddtrace.readthedocs.io/en/stable/configuration.html) and [pytest integration](https://ddtrace.readthedocs.io/en/stable/integrations.html#pytest).
- The historical [X-Ray context fix in PR18](https://github.com/DataDog/datadog-lambda-python/pull/18/files) guards Lambda-specific operations; it does not choose the application's mock target.

## Optional coffee

This example is free. If it saved you time, buying me a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
