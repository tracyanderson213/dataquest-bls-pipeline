from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_sqs as sqs,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda_event_sources as lambda_event_sources,
    aws_iam as iam,
    aws_logs as logs,
    aws_sagemaker as sagemaker,
    RemovalPolicy,
)
from constructs import Construct

class RearcDataPipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 Bucket for storing BLS and population data
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

        # Dead Letter Queue for failed analytics processing
        analytics_dlq = sqs.Queue(
            self, "AnalyticsDLQ",
            queue_name="rearc-analytics-dlq",
            retention_period=Duration.days(14)
        )

        # SQS Queue for analytics processing (Part 4 requirement)
        analytics_queue = sqs.Queue(
            self, "AnalyticsQueue",
            queue_name="rearc-analytics-queue",
            visibility_timeout=Duration.minutes(15),  # Match Lambda timeout
            receive_message_wait_time=Duration.seconds(20),  # Long polling
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=analytics_dlq
            )
        )

        # IAM Role for data collection Lambda (Parts 1 & 2)
        data_collection_role = iam.Role(
            self, "DataCollectionLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # IAM Role for analytics Lambda (Part 3)
        analytics_role = iam.Role(
            self, "AnalyticsLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Grant S3 permissions to data collection Lambda
        data_bucket.grant_read_write(data_collection_role)

        # Grant S3 read permissions to analytics Lambda
        data_bucket.grant_read(analytics_role)

        # Grant SQS permissions to analytics Lambda
        analytics_queue.grant_consume_messages(analytics_role)
        analytics_dlq.grant_consume_messages(analytics_role)

        # Lambda function for data collection (Parts 1 & 2 combined)
        data_collection_lambda = _lambda.Function(
            self, "DataCollectionLambda",
            function_name="rearc-data-ingestion",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("."),
            handler="handler.lambda_handler",
            role=data_collection_role,
            timeout=Duration.minutes(15),
            memory_size=512,
            environment={
                'BUCKET_NAME': data_bucket.bucket_name,
                'BLS_API_KEY': '5ee32fa6e7da4ce490d27e198e912f08'
            },
            retry_attempts=2,
            description="Combined BLS economic data and population data collection"
        )

        # Lambda function for analytics processing (Part 3)
        analytics_lambda = _lambda.Function(
            self, "AnalyticsLambda",
            function_name="rearc-analytics-processor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("."),
            handler="analytics_lambda.lambda_handler",
            role=analytics_role,
            timeout=Duration.minutes(15),
            memory_size=1024,  # More memory for data processing
            environment={
                'BUCKET_NAME': data_bucket.bucket_name
            },
            retry_attempts=2,
            description="Automated analytics processing for economic data"
        )

        # EventBridge rule for daily data collection
        daily_rule = events.Rule(
            self, "DailyDataCollection",
            description="Trigger combined BLS and population data collection daily at 8 AM UTC",
            schedule=events.Schedule.cron(
                minute="0",
                hour="8",
                day="*",
                month="*",
                year="*"
            )
        )

        # Add data collection Lambda as target for daily schedule
        daily_rule.add_target(targets.LambdaFunction(data_collection_lambda))

        # Grant EventBridge permission to invoke data collection Lambda
        data_collection_lambda.add_permission(
            "AllowEventBridge",
            principal=iam.ServicePrincipal("events.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=daily_rule.rule_arn
        )

        # S3 Event Notification to SQS (Part 4 requirement)
        # Trigger analytics when population data is uploaded (signals completion)
        data_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SqsDestination(analytics_queue),
            s3.NotificationKeyFilter(
                prefix="datausa-api/population/",
                suffix=".json"
            )
        )

        # SQS Event Source for analytics Lambda
        analytics_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(
                analytics_queue,
                batch_size=1,  # Process one message at a time
                max_batching_window=Duration.seconds(5)
            )
        )

        # CloudWatch Log Groups with retention
        data_collection_log_group = logs.LogGroup(
            self, "DataCollectionLogGroup",
            log_group_name=f"/aws/lambda/{data_collection_lambda.function_name}",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY
        )

        analytics_log_group = logs.LogGroup(
            self, "AnalyticsLogGroup", 
            log_group_name=f"/aws/lambda/{analytics_lambda.function_name}",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY
        )

        # SageMaker Notebook Instance (for manual analytics)
        notebook_role = iam.Role(
            self, "SageMakerNotebookRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess")
            ]
        )

        # Grant S3 access to SageMaker notebook
        data_bucket.grant_read_write(notebook_role)

        sagemaker_notebook = sagemaker.NotebookInstance(
            self, "AnalyticsNotebook",
            instance_name="rearc-quest-notebook",
            instance_type=sagemaker.InstanceType.ML_T3_MEDIUM,
            role_arn=notebook_role.role_arn,
            default_code_repository="https://github.com/tracyanderson213/dataquest-bls-pipeline.git"
        )
