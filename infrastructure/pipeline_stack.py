from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    RemovalPolicy,
)
from constructs import Construct

class RearcDataPipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 Bucket for storing BLS data
        data_bucket = s3.Bucket(
            self, "BLSDataBucket",
            bucket_name="dataquest-gov-bls-timeseries",
            versioning=True,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    noncurrent_version_expiration=Duration.days(90),
                    abort_incomplete_multipart_upload_after=Duration.days(7)
                )
            ]
        )

        # IAM Role for Lambda
        lambda_role = iam.Role(
            self, "BLSLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add S3 permissions to Lambda role
        data_bucket.grant_read_write(lambda_role)

        # Lambda function for BLS data ingestion
        bls_lambda = _lambda.Function(
            self, "BLSDataIngestion",
            function_name="rearc-data-ingestion",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("."),
            handler="handler.lambda_handler",
            role=lambda_role,
            timeout=Duration.minutes(15),
            memory_size=512,
            environment={
                'BUCKET_NAME': data_bucket.bucket_name,
                'BLS_API_KEY': '5ee32fa6e7da4ce490d27e198e912f08'
            },
            retry_attempts=2
        )

        # EventBridge rule for daily execution
        daily_rule = events.Rule(
            self, "DailyBLSIngestion",
            description="Trigger BLS data ingestion daily at 8 AM UTC",
            schedule=events.Schedule.cron(
                minute="0",
                hour="8",
                day="*",
                month="*",
                year="*"
            )
        )

        # Add Lambda as target
        daily_rule.add_target(targets.LambdaFunction(bls_lambda))

        # Grant EventBridge permission to invoke Lambda
        bls_lambda.add_permission(
            "AllowEventBridge",
            principal=iam.ServicePrincipal("events.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=daily_rule.rule_arn
        )
