import hashlib
import os
import re
from pathlib import Path

import botocore
from boto3.session import Session
from cli import echo
from cli.colors import WARNING
from modules import Modules
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
from troposphere.iam import Policy, Role
from troposphere.s3 import Bucket, Private

API_DEPLOYMENT_STAGE = "v1"
PROJECT_ROOT = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "")

OUTPUT_API_GATEWAY_ENDPOINT = "APIGatewayEndpoint"
S3_TEPM_PREFIX = "tmp/"
S3_ENRICHED_PREFIX = "enriched/"
S3_DEPLOYMENT_PREFIX = f"{S3_TEPM_PREFIX}deployment/"

event_receiver_zip_path = Path(PROJECT_ROOT, "engine", "event_receiver", "dist", "event_receiver.zip")


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
        exit(1)

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

        # collect templates for enabled modules
        modules = Modules(self.cfg)
        for module_name, module_infos in modules.enabled().items():
            echo.enum_elm(f"running pre deploy code for module '{module_name}'...")
            if "pre_deploy" in module_infos:
                module_infos["pre_deploy"](self.boto_session)

        try:
            if not self.exists:
                echo.enum_elm("creating initial stack")
                stack_created = True
                params = {
                    "StackName": self.name,
                    "TemplateBody": self.template_initial.to_json(),
                    "Capabilities": ["CAPABILITY_IAM"],
                }
                cf_client.create_stack(**params)
                waiter = cf_client.get_waiter("stack_create_complete")
            else:
                echo.enum_elm("upload deployment artifacts")
                s3_bucket_name = self.get_output("S3BucketName")
                s3_client.upload_file(
                    str(event_receiver_zip_path),
                    s3_bucket_name,
                    f"{S3_DEPLOYMENT_PREFIX}{self.artifact_filename_hashed(event_receiver_zip_path)}",
                )

                echo.enum_elm("updating stack")
                params = {
                    "StackName": self.name,
                    "TemplateBody": self.template.to_json(),
                    "Capabilities": ["CAPABILITY_IAM"],
                }
                cf_client.update_stack(**params)
                waiter = cf_client.get_waiter("stack_update_complete")
            echo.enum_elm(f"waiting for stack to be ready...")
            waiter.wait(StackName=self.name)
        except (botocore.exceptions.ClientError, botocore.exceptions.WaiterError) as e:
            if hasattr(e, "response"):
                if e.response["Error"]["Message"] == "No updates are to be performed.":
                    echo.enum_elm("no changes to deploy", dash_color=WARNING)
                elif "DELETE_IN_PROGRESS" in e.response["Error"]["Message"]:
                    self.error_and_exit("stack already destroyed. Delete in progress...")
                elif (
                    "UPDATE_IN_PROGRESS" in e.response["Error"]["Message"]
                    or "UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS" in e.response["Error"]["Message"]
                    or "CREATE_IN_PROGRESS" in e.response["Error"]["Message"]
                ):
                    self.error_and_exit("stack is already updating...")
                else:
                    raise e
            else:
                self.error_and_exit(
                    "waiter encountered a terminal failure state. Run 'events' command to see latest Events"
                )
        else:
            if stack_created:
                # deploy rest
                self.deploy()
            else:
                # Deploy API
                echo.enum_elm("deploying API")
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

    def get_latest_events(self):
        cf_client = self.boto_session.client("cloudformation")
        stack_result = cf_client.describe_stack_events(StackName=self.name)
        return stack_result["StackEvents"]

    def destroy(self):
        cf_client = self.boto_session.client("cloudformation")

        if self.exists_or_exit():
            # empty bucket - only empty can be deleted afterwards
            bucket_name = self.get_output("S3BucketName")
            echo.enum_elm(f"deleting files in S3 Bucket {bucket_name}...")
            s3_resource = self.boto_session.resource("s3")
            bucket = s3_resource.Bucket(bucket_name)
            bucket.objects.all().delete()

            # run post deploy code enabled modules
            modules = Modules(self.cfg)
            for module_name, module_infos in modules.enabled().items():
                echo.enum_elm(f"run pre destroy code for module '{module_name}'")
                if "pre_destroy" in module_infos:
                    module_infos["pre_destroy"](self.boto_session)

            try:
                cf_client.delete_stack(**{"StackName": self.name})
                waiter = cf_client.get_waiter("stack_delete_complete")
                echo.enum_elm("waiting for stack to be destroyed...")
                waiter.wait(StackName=self.name)
            except (botocore.exceptions.ClientError, botocore.exceptions.WaiterError) as e:
                if hasattr(e, "response"):
                    if e.response["Error"]["Message"] == "No updates are to be performed.":
                        echo.enum_elm("no changes to deploy", dash_color=WARNING)
                    elif "DELETE_IN_PROGRESS" in e.response["Error"]["Message"]:
                        self.error_and_exit("stack already destroyed. Delete in progress...")
                    elif (
                        "UPDATE_IN_PROGRESS" in e.response["Error"]["Message"]
                        or "UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS" in e.response["Error"]["Message"]
                        or "CREATE_IN_PROGRESS" in e.response["Error"]["Message"]
                    ):
                        self.error_and_exit("stack is already updating...")
                    else:
                        raise e
                else:
                    self.error_and_exit(
                        "waiter encountered a terminal failure state. Run 'events' command to see latest Events"
                    )

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
                Prefix=S3_ENRICHED_PREFIX,
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
                    S3Key=f"{S3_DEPLOYMENT_PREFIX}{self.artifact_filename_hashed(event_receiver_zip_path)}",
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

        # collect templates for enabled modules
        if self.exists:
            modules = Modules(self.cfg)
            for module_name, module_infos in modules.enabled().items():
                echo.enum_elm(f"preparing stack for module '{module_name}'")
                stack_tpl = module_infos["stack"]["template"]

                for resource in stack_tpl.resources.values():
                    self.template.add_resource(resource)
                for output in stack_tpl.outputs.values():
                    self.template.add_output(output)
                for parameter in stack_tpl.parameters.values():
                    self.template.add_parameter(parameter)
                for name, mapping in stack_tpl.mappings.items():
                    self.template.add_mapping(name, mapping)
