import aws_cdk as cdk
import boto3

from alarming_business.alarming_business_stack import AlarmingBusinessStack

app = cdk.App()
environment = app.node.try_get_context("environment")
account = boto3.client("sts").get_caller_identity()["Account"]
AlarmingBusinessStack(
    app,
    "AlarmingBusinessStack",
    env=cdk.Environment(account=account, region=environment["AWS_REGION"]),
    environment=environment,
)
app.synth()
