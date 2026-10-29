import datadog_lambda.metric as metric


def handler(event, context=None):
    count = len(event["records"])
    metric.lambda_metric("records.processed", count, tags=["queue:example"])
    return {"processed": count}
