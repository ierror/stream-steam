import hashlib
import os
import re

import botocore
from boto3.session import Session
from cli import echo
from troposphere import GetAtt, Join, Output, Ref, Template
from troposphere.apigateway import (
    ApiStage,
    Deployment,
    Integration,
    Method,
    QuotaSettings,
    Resource,
    RestApi,
    Stage,
    ThrottleSettings,
    UsagePlan,
)
from troposphere.awslambda import Code, Environment, Function
from troposphere.firehose import BufferingHints, DeliveryStream, S3DestinationConfiguration
from troposphere.glue import Crawler, Database, DatabaseInput, S3Target, Schedule, SchemaChangePolicy, Targets
from troposphere.iam import Policy, Role
from troposphere.s3 import Bucket, Private

API_DEPLOYMENT_STAGE = "v1"
PROJECT_ROOT = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "")

OUTPUT_API_GATEWAY_ENDPOINT = "APIGatewayEndpoint"

event_receiver_zipfile = os.path.join("event_receiver", "dist", "event_receiver.zip")


class CloudformationStack:
    def __init__(self, name, cfg):
        # check for valid stack name
        if not re.match("^[a-z-]+$", name):
            self.error_and_exit(f"Invalid Stack name '{name}' provided. Only characters a-z and - are allowed")
        self.name = name
        self.cfg = cfg
        self.region_name = cfg.get("aws_region_name")
        self.boto_session = Session(
            region_name=self.region_name,
            aws_access_key_id=cfg.get("aws_access_key_id"),
            aws_secret_access_key=cfg.get("aws_secret_access_key"),
        )
        self._build_resources()

    def error_and_exit(self, msg):
        echo.error(msg)
        exit(0)

    def normalize_resource_name(self, name):
        # e.g. glue-database => stream-steam-dev-glue-database
        if name:
            return f"{self.name}-{name}"
        return self.name

    @classmethod
    def artifact_filename_hashed(cls, artifact_file):
        """
        :param artifact_file: e.g. ./foo/event_receiver.zip
        :return: ./foo/event_receiver-<hash>.zip
        """
        hash_md5 = hashlib.md5()
        with open(artifact_file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        artifact_file = os.path.basename(artifact_file)
        basename, ext = os.path.splitext(artifact_file)
        return f"{basename}_{hash_md5.hexdigest()}{ext}"

    @property
    def stack_id(self):
        cloudformation_client = self.boto_session.client("cloudformation")
        paginator = cloudformation_client.get_paginator("list_stacks")
        page_iterator = paginator.paginate()

        for stack_batch in page_iterator:
            stacks = stack_batch["StackSummaries"]
            for stack in stacks:
                if stack["StackStatus"] == "DELETE_COMPLETE":
                    continue
                if self.name == stack["StackName"]:
                    return stack["StackId"]

    def deploy(self):
        cf_client = self.boto_session.client("cloudformation")
        api_gateway_client = self.boto_session.client("apigateway")
        s3_client = self.boto_session.client("s3")
        stack_created = False

        try:
            if not self.exists:
                echo.info("creating initial stack")
                stack_created = True
                params = {
                    "StackName": self.name,
                    "TemplateBody": self.template_initial.to_json(),
                    "Capabilities": ["CAPABILITY_IAM"],
                }
                cf_client.create_stack(**params)
                waiter = cf_client.get_waiter("stack_create_complete")
            else:
                echo.info("upload deployment artifacts")
                s3_bucket_name = self.get_output("S3BucketName")
                s3_client.upload_file(
                    event_receiver_zipfile,
                    s3_bucket_name,
                    f"deployment/artifacts/{self.artifact_filename_hashed(event_receiver_zipfile)}",
                )

                echo.info("updating stack")
                params = {
                    "StackName": self.name,
                    "TemplateBody": self.template.to_json(),
                    "Capabilities": ["CAPABILITY_IAM"],
                }
                cf_client.update_stack(**params)
                waiter = cf_client.get_waiter("stack_update_complete")
            echo.info(f"waiting for stack to be ready...")
            waiter.wait(StackName=self.name)
        except (botocore.exceptions.ClientError, botocore.exceptions.WaiterError) as ex:
            if hasattr(ex, "response"):
                if ex.response["Error"]["Message"] == "No updates are to be performed.":
                    echo.warning("no changes to deploy")
                elif "DELETE_IN_PROGRESS" in ex.response["Error"]["Message"]:
                    self.error_and_exit("Stack already destroyed. Delete in progress...")
                elif "UPDATE_IN_PROGRESS" in ex.response["Error"]["Message"]:
                    echo.warning("Stack is already updating...")
                    exit(0)
                else:
                    raise ex
            else:
                raise ex
        else:
            if stack_created:
                # deploy rest
                self.deploy()
            else:
                # Deploy API
                echo.info("deploying API")
                api_id = self.get_output("APIId")
                api_gateway_client.create_deployment(restApiId=api_id, stageName=API_DEPLOYMENT_STAGE)

    @property
    def exists(self):
        return self.stack_id

    def exists_or_exit(self):
        if not self.exists:
            self.error_and_exit(f"Stack '{self.name}' does not exist")
        return True

    def get_outputs(self):
        if self.exists_or_exit():
            cf_client = self.boto_session.client("cloudformation")
            stack_result = cf_client.describe_stacks(StackName=self.name)
            return stack_result["Stacks"][0]["Outputs"]

    def get_output(self, output_key):
        return [o for o in self.get_outputs() if o["OutputKey"] == output_key][0]["OutputValue"]

    def destroy(self):
        cf_client = self.boto_session.client("cloudformation")

        # empty bucket - only empty can be deleted afterwards
        bucket_name = self.get_output("S3BucketName")
        echo.info(f"deleting files in S3 Bucket {bucket_name}...")
        s3_resource = self.boto_session.resource("s3")
        bucket = s3_resource.Bucket(bucket_name)
        bucket.objects.all().delete()

        if self.exists_or_exit():
            cf_client.delete_stack(**{"StackName": self.name})
            waiter = cf_client.get_waiter("stack_delete_complete")
            echo.info("waiting for stack to be deleted...")
            waiter.wait(StackName=self.name)

    def _build_resources(self):
        self.template = Template()
        self.template_initial = Template()

        # S3 Bucket
        s3_bucket_obj = Bucket("S3Bucket", AccessControl=Private)
        s3_bucket = self.template.add_resource(s3_bucket_obj)
        s3_bucket_output_res = Output("S3BucketName", Value=Ref(s3_bucket), Description="S3 bucket")
        self.template.add_output(s3_bucket_output_res)

        self.template_initial.add_resource(s3_bucket_obj)
        self.template_initial.add_output(s3_bucket_output_res)

        # Kinesis Firehose event_in compressor
        event_compressor_name = self.normalize_resource_name("event-compressor")
        event_compressor = DeliveryStream(
            "EventCompressor",
            DeliveryStreamName=event_compressor_name,
            S3DestinationConfiguration=S3DestinationConfiguration(
                BucketARN=GetAtt("S3Bucket", "Arn"),
                BufferingHints=BufferingHints(IntervalInSeconds=60, SizeInMBs=25),
                # TODO
                # CloudWatchLoggingOptions=CloudWatchLoggingOptions(
                #     Enabled=True, LogGroupName="FirehosEventCompressor", LogStreamName="FirehosEventCompressor",
                # ),
                CompressionFormat="GZIP",
                Prefix="enriched/",
                RoleARN=GetAtt("LambdaExecutionRole", "Arn"),
            ),
        )
        self.template.add_resource(event_compressor)

        # Lambda Execution Role
        self.template.add_resource(
            Role(
                "LambdaExecutionRole",
                Path="/",
                Policies=[
                    Policy(
                        PolicyName="root",
                        PolicyDocument={
                            "Version": "2012-10-17",
                            "Statement": [
                                {"Action": ["logs:*"], "Resource": "arn:aws:logs:*:*:*", "Effect": "Allow"},
                                {"Action": ["lambda:*"], "Resource": "*", "Effect": "Allow"},
                                {
                                    "Action": ["s3:*"],
                                    "Resource": Join("", [GetAtt("S3Bucket", "Arn"), "/*"]),
                                    "Effect": "Allow",
                                },
                                {"Action": ["firehose:PutRecord"], "Resource": "*", "Effect": "Allow"},
                            ],
                        },
                    )
                ],
                AssumeRolePolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["sts:AssumeRole"],
                            "Effect": "Allow",
                            "Principal": {
                                "Service": [
                                    "lambda.amazonaws.com",
                                    "apigateway.amazonaws.com",
                                    "firehose.amazonaws.com",
                                ]
                            },
                        }
                    ],
                },
            )
        )

        # Event Receiver Lambda
        event_receiver_lambda_name = self.normalize_resource_name("event-receiver")

        self.template.add_resource(
            Function(
                "LambdaEventReceiver",
                FunctionName=event_receiver_lambda_name,
                Code=Code(
                    S3Bucket=Ref(s3_bucket),
                    S3Key=f"deployment/artifacts/{self.artifact_filename_hashed(event_receiver_zipfile)}",
                ),
                Handler="lambda.lambda_handler",
                Environment=Environment(
                    Variables={
                        "S3_BUCKET": Ref(s3_bucket),
                        "DELIVERY_STREAM_NAME": event_compressor_name,
                        "IP_GEOCODING_ENABLED": self.cfg.get("ip_geocoding_enabled"),
                        "IP_INFO_API_TOKEN": self.cfg.get("ip_info_api_token"),
                        "USERSTACK_API_TOKEN": self.cfg.get("userstack_api_token"),
                        "DEVICE_DETECTION_ENABLED": self.cfg.get("device_detection_enabled"),
                    }
                ),
                Role=GetAtt("LambdaExecutionRole", "Arn"),
                Runtime="python3.7",
            )
        )

        # API Gateway
        api_gateway = self.template.add_resource(
            RestApi("APIGateway", Name=self.normalize_resource_name("api-gateway"))
        )

        # API Gateway Stage
        api_gateway_deployment = self.template.add_resource(
            Deployment(
                f"APIGatewayDeployment{API_DEPLOYMENT_STAGE}",
                DependsOn="APIGatewayLambdaEventReceiverMain",
                RestApiId=Ref(api_gateway),
            )
        )
        api_gateway_stage = self.template.add_resource(
            Stage(
                f"APIGatewayStage{API_DEPLOYMENT_STAGE}",
                StageName=API_DEPLOYMENT_STAGE,
                RestApiId=Ref(api_gateway),
                DeploymentId=Ref(api_gateway_deployment),
            )
        )

        # API Gateway usage plan
        self.template.add_resource(
            UsagePlan(
                "APIGatewayUsagePlan",
                UsagePlanName="APIGatewayUsagePlan",
                Quota=QuotaSettings(Limit=50000, Period="MONTH"),
                Throttle=ThrottleSettings(BurstLimit=500, RateLimit=5000),
                ApiStages=[ApiStage(ApiId=Ref(api_gateway), Stage=Ref(api_gateway_stage))],
            )
        )

        # API Gateway resource to map the lambda function to
        def _lambda_method_obj(resource, suffix):
            resource = self.template.add_resource(resource)

            return self.template.add_resource(
                Method(
                    f"APIGatewayLambdaEventReceiver{suffix}",
                    DependsOn="LambdaEventReceiver",
                    RestApiId=Ref(api_gateway),
                    AuthorizationType="NONE",
                    ResourceId=Ref(resource),
                    HttpMethod="ANY",
                    Integration=Integration(
                        Credentials=GetAtt("LambdaExecutionRole", "Arn"),
                        Type="AWS_PROXY",
                        IntegrationHttpMethod="POST",
                        Uri=Join(
                            "",
                            [
                                f"arn:aws:apigateway:{self.region_name}:lambda:path/2015-03-31/functions/",
                                GetAtt("LambdaEventReceiver", "Arn"),
                                "/invocations",
                            ],
                        ),
                    ),
                )
            )

        # API Gateway Lambda method
        _lambda_method_obj(
            Resource(
                "APIGatewayResourceEventReceiverMain",
                RestApiId=Ref(api_gateway),
                PathPart="event-receiver",
                ParentId=GetAtt("APIGateway", "RootResourceId"),
            ),
            "Main",
        )

        # matomo.php path alias for the event receiver lambda
        _lambda_method_obj(
            Resource(
                "APIGatewayResourceEventReceiverMatomo",
                RestApiId=Ref(api_gateway),
                PathPart="matomo.php",
                ParentId=GetAtt("APIGateway", "RootResourceId"),
            ),
            "Matomo",
        )

        self.template.add_output(
            [
                Output(
                    OUTPUT_API_GATEWAY_ENDPOINT,
                    Value=Join(
                        "",
                        [
                            "https://",
                            Ref(api_gateway),
                            f".execute-api.{self.region_name}.amazonaws.com/",
                            API_DEPLOYMENT_STAGE,
                        ],
                    ),
                    Description="API Endpoint",
                ),
                Output("APIId", Value=Ref(api_gateway), Description="API ID"),
            ]
        )

        # Glue Execution Role
        self.template.add_resource(
            Role(
                "GlueExecutionRole",
                Path="/",
                Policies=[
                    Policy(
                        PolicyName="root",
                        PolicyDocument={
                            "Version": "2012-10-17",
                            "Statement": [
                                {"Action": ["logs:*"], "Resource": "arn:aws:logs:*:*:*", "Effect": "Allow"},
                                {
                                    "Effect": "Allow",
                                    "Action": [
                                        "glue:*",
                                        "s3:GetBucketLocation",
                                        "s3:ListBucket",
                                        "s3:ListAllMyBuckets",
                                        "s3:GetBucketAcl",
                                        "iam:ListRolePolicies",
                                        "iam:GetRole",
                                        "iam:GetRolePolicy",
                                        "cloudwatch:PutMetricData",
                                    ],
                                    "Resource": ["*"],
                                },
                                {
                                    "Effect": "Allow",
                                    "Action": ["s3:CreateBucket"],
                                    "Resource": ["arn:aws:s3:::aws-glue-*"],
                                },
                                {
                                    "Effect": "Allow",
                                    "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                                    "Resource": ["arn:aws:s3:::aws-glue-*/*", "arn:aws:s3:::*/*aws-glue-*/*"],
                                },
                                {
                                    "Effect": "Allow",
                                    "Action": ["s3:GetObject"],
                                    "Resource": ["arn:aws:s3:::crawler-public*", "arn:aws:s3:::aws-glue-*"],
                                },
                                {
                                    "Effect": "Allow",
                                    "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                                    "Resource": ["arn:aws:logs:*:*:/aws-glue/*"],
                                },
                                {
                                    "Action": ["s3:*"],
                                    "Resource": Join("", [GetAtt("S3Bucket", "Arn"), "/*"]),
                                    "Effect": "Allow",
                                },
                                {
                                    "Action": ["iam:PassRole"],
                                    "Effect": "Allow",
                                    "Resource": ["arn:aws:iam::*:role/service-role/AWSGlueServiceRole*"],
                                    "Condition": {"StringLike": {"iam:PassedToService": ["glue.amazonaws.com"]}},
                                },
                                {
                                    "Action": ["iam:PassRole"],
                                    "Effect": "Allow",
                                    "Resource": "arn:aws:iam::*:role/AWSGlueServiceRole*",
                                    "Condition": {"StringLike": {"iam:PassedToService": ["glue.amazonaws.com"]}},
                                },
                            ],
                        },
                    )
                ],
                AssumeRolePolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["sts:AssumeRole"],
                            "Effect": "Allow",
                            "Principal": {"Service": ["glue.amazonaws.com"]},
                        }
                    ],
                },
            )
        )

        # Glue Database
        glue_catalog_id = Ref("AWS::AccountId")
        glue_database_name = self.normalize_resource_name("")
        self.template.add_resource(
            Database(
                "GlueDatabase",
                CatalogId=glue_catalog_id,
                DatabaseInput=DatabaseInput(
                    Name=glue_database_name, LocationUri=Join("", ["s3://", Ref(s3_bucket), "/tmp/glue/"]),
                ),
            )
        )

        # Glue Crawler
        self.template.add_resource(
            Crawler(
                "GlueCrawler",
                Name=self.normalize_resource_name("events-enriched"),
                DatabaseName=glue_database_name,
                Role=GetAtt("GlueExecutionRole", "Arn"),
                Targets=Targets(S3Targets=[S3Target(Path=Join("", ["s3://", Ref(s3_bucket), "/enriched/"]))]),
                SchemaChangePolicy=SchemaChangePolicy(
                    UpdateBehavior="UPDATE_IN_DATABASE", DeleteBehavior="DELETE_FROM_DATABASE",
                ),
                Schedule=Schedule(ScheduleExpression="cron(00 */1 * * ? *)"),
            )
        )
