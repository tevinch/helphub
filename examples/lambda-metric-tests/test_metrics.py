"""Metric assertions belong at the application's external telemetry boundary."""
from unittest.mock import patch

import pytest

import app_direct
import app_module


@pytest.mark.parametrize("app", [app_direct, app_module], ids=["direct", "module"])
def test_processed_records_submit_exact_metric(app):
    # Removing the call, changing its value/tags, or returning the wrong count fails.
    target = app if app is app_direct else app.metric
    with patch.object(target, "lambda_metric", autospec=True) as metric:
        assert app.handler({"records": ["alpha", "beta"]}) == {"processed": 2}
        metric.assert_called_once_with("records.processed", 2, tags=["queue:example"])


@pytest.mark.parametrize("app", [app_direct, app_module], ids=["direct", "module"])
def test_empty_batch_reports_zero(app):
    target = app if app is app_direct else app.metric
    with patch.object(target, "lambda_metric", autospec=True) as metric:
        assert app.handler({"records": []}) == {"processed": 0}
        metric.assert_called_once_with("records.processed", 0, tags=["queue:example"])


@pytest.mark.parametrize("app", [app_direct, app_module], ids=["direct", "module"])
def test_invalid_event_does_not_report_success(app):
    target = app if app is app_direct else app.metric
    with patch.object(target, "lambda_metric", autospec=True) as metric:
        with pytest.raises(KeyError, match="records"):
            app.handler({})
        metric.assert_not_called()


def test_patching_source_after_direct_import_does_not_intercept(capsys):
    # DD_FLUSH_TO_LOG=true keeps this real unmocked metric local to stdout.
    # Replacing this test with a patched local binding would hide the mistake.
    with patch.object(app_module.metric, "lambda_metric", autospec=True) as wrong_target:
        assert app_direct.handler({"records": ["alpha", "beta", "gamma"]}) == {"processed": 3}
        wrong_target.assert_not_called()
    import json
    payload = json.loads(capsys.readouterr().out)
    assert payload["m"] == "records.processed"
    assert payload["v"] == 3
    assert "queue:example" in payload["t"]

