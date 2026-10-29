from datadog_lambda.metric import lambda_metric


def handler(event, context=None):
    count = len(event["records"])
    lambda_metric("records.processed", count, tags=["queue:example"])
    return {"processed": count}
