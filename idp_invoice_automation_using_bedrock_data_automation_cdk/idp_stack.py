## Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
## Licensed under the Amazon Software License  https://aws.amazon.com/asl/
from aws_cdk import (
    RemovalPolicy,
    Stack,
    Duration,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_lambda_python_alpha as _alambda,
    aws_lambda_event_sources as lambda_event_sources,
    aws_sqs as sqs,
    aws_ec2 as ec2,
    aws_kms as kms,
    aws_s3_notifications,
    aws_lambda_event_sources as lambda_event_sources,
    custom_resources,
    CustomResource,
    aws_events as events,
    aws_events_targets as targets,
)

from constructs import Construct
from cdk_nag import NagSuppressions
import json


class IDPStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        with open('project_config.json', 'r') as file:
            variables = json.load(file)

        ssm_parameter_name = variables["invoices"]["ssm_parameter_name"]
        invoices_blueprint_name = variables["invoices"]["blueprint_name"]
        invoices_doc_type = variables["invoices"]["doc_type"]

        # Create a VPC (if you don't already have one)
        public_subnet = ec2.SubnetConfiguration(
            name="PublicSubnet", 
            subnet_type=ec2.SubnetType.PUBLIC, 
            cidr_mask=variables["vpc"]["cidr_mask"]
        )
        private_subnet = ec2.SubnetConfiguration(
            name="PrivateSubnet", 
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, 
            cidr_mask=variables["vpc"]["cidr_mask"]
        )
        vpc = ec2.Vpc(
            scope=self,
            id="DemoVPC",
            ip_addresses=ec2.IpAddresses.cidr(variables["vpc"]["cidr_range"]),
            subnet_configuration=[public_subnet, private_subnet],
            flow_logs={
                "cloudwatch":ec2.FlowLogOptions(
                    destination=ec2.FlowLogDestination.to_cloud_watch_logs()
             )
            }
        )


        # Create an S3 VPC Endpoint
        s3_endpoint = ec2.GatewayVpcEndpoint(
            self,
            "S3VpcEndpoint",
            vpc=vpc,
            service=ec2.GatewayVpcEndpointAwsService.S3
        )

        # Create the access logs bucket
        # amazonq-ignore-next-line
        access_logs_bucket = s3.Bucket(
            self,
            "AccessLogsBucket",
            removal_policy=RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            auto_delete_objects=True,
            object_ownership=s3.ObjectOwnership.OBJECT_WRITER,
        )

        # Grant CloudFront permission to write logs to the bucket
        access_logs_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudFrontLogDelivery",
                actions=["s3:PutObject"],
                principals=[iam.ServicePrincipal("delivery.logs.amazonaws.com")],
                resources=[access_logs_bucket.arn_for_objects("*")]
            )
        )

        # Create the input bucket
        input_bucket_s3 = s3.Bucket(
            self,
            "InputBucket",
            removal_policy=RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            server_access_logs_bucket=access_logs_bucket,
            enforce_ssl=True,
            auto_delete_objects=True,
        )
        # Create the stagging bucket
        stagging_bucket_s3 = s3.Bucket(
            self,
            "StaggingBucket",
            removal_policy=RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            server_access_logs_bucket=access_logs_bucket,
            enforce_ssl=True,
            auto_delete_objects=True,
        )
        # Create the output bucket
        output_bucket_s3  = s3.Bucket(
            self,
            "OutputBucket",
            removal_policy= RemovalPolicy.DESTROY,
            block_public_access= s3.BlockPublicAccess.BLOCK_ALL,
            encryption= s3.BucketEncryption.S3_MANAGED,
            server_access_logs_bucket=access_logs_bucket,
            enforce_ssl=True,
            auto_delete_objects=True,
        )

        # # Add a policy to allow access through the VPC Endpoint for the access logs bucket
        # access_logs_bucket.add_to_resource_policy(
        #     iam.PolicyStatement(
        #         effect=iam.Effect.DENY,
        #         actions=["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
        #         resources=[access_logs_bucket.bucket_arn, f"{access_logs_bucket.bucket_arn}/*"],
        #         principals=[iam.AnyPrincipal()],
        #         conditions={
        #             "StringNotEquals": {
        #                 "aws:SourceVpce": s3_endpoint.vpc_endpoint_id
        #             }
        #         }
        #     )
        # )

        # # Add a policy to input bucket to allow access through the VPC Endpoint
        # input_bucket_s3.add_to_resource_policy(
        #     iam.PolicyStatement(
        #         effect=iam.Effect.DENY,
        #         actions=["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
        #         resources=[input_bucket_s3.bucket_arn, f"{input_bucket_s3.bucket_arn}/*"],
        #         principals=[iam.AnyPrincipal()],
        #         conditions={
        #             "StringNotEquals": {
        #                 "aws:SourceVpce": s3_endpoint.vpc_endpoint_id
        #             }
        #         }
        #     )
        # )

        # # Add a policy to stagging bucket to allow access through the VPC Endpoint
        # stagging_bucket_s3.add_to_resource_policy(
        #     iam.PolicyStatement(
        #         effect=iam.Effect.DENY,
        #         actions=["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
        #         resources=[stagging_bucket_s3.bucket_arn, f"{stagging_bucket_s3.bucket_arn}/*"],
        #         principals=[iam.AnyPrincipal()],
        #         conditions={
        #             "StringNotEquals": {
        #                 "aws:SourceVpce": s3_endpoint.vpc_endpoint_id
        #             }
        #         }
        #     )
        # )

        # # Add a policy to output bucket to allow access through the VPC Endpoint
        # output_bucket_s3.add_to_resource_policy(
        #     iam.PolicyStatement(
        #         effect=iam.Effect.DENY,
        #         actions=["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
        #         resources=[output_bucket_s3.bucket_arn, f"{output_bucket_s3.bucket_arn}/*"],
        #         principals=[iam.AnyPrincipal()],
        #         conditions={
        #             "StringNotEquals": {
        #                 "aws:SourceVpce": s3_endpoint.vpc_endpoint_id
        #             }
        #         }
        #     )
        # )

        ######################### Lambda Layers  #########################
        langchain_core_layer =_alambda.PythonLayerVersion(self, 'langchain-core-layer',
            entry = './lambda/lambda_layer/langchain_core_layer/',
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            compatible_architectures=[_lambda.Architecture.ARM_64],
        )

        pypdfium2_layer = _alambda.PythonLayerVersion(self, 'pypdfium2-layer',
            entry = './lambda/lambda_layer/pypdfium2_layer/',
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            compatible_architectures=[_lambda.Architecture.ARM_64],
        )

        pillow_layer = _alambda.PythonLayerVersion(self, 'pillow-layer',
            entry = './lambda/lambda_layer/pillow_layer/',
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            compatible_architectures=[_lambda.Architecture.ARM_64],
        )

        boto3_layer = _alambda.PythonLayerVersion(self, 'boto3-layer',
            entry = './lambda/lambda_layer/boto3_layer/',
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            compatible_architectures=[_lambda.Architecture.ARM_64],
        )
        ######################### SQS and DLQ  #########################
        # Create a KMS key for encryption
        kms_key = kms.Key(self, "SQSEncryptionKey",
            description="KMS key for SQS queue encryption",
            enable_key_rotation=True
        )

        ############ Invoices BDA Queue ############
        #### DLQ
        invoices_bda_dlq_ = sqs.Queue(
            self,
            id="InvoicesBDADLQ",
            retention_period=Duration.days(7),
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            encryption=sqs.QueueEncryption.SQS_MANAGED,
        )
        invoices_bda_dlq = sqs.DeadLetterQueue(
            max_receive_count=3,
            queue=invoices_bda_dlq_,
        )
        #### SQS
        invoices_bda_queue = sqs.Queue(
            self,
            "InvoicesBDAQueue",
            receive_message_wait_time=Duration.seconds(5), #Time that the poller waits for new messages before returning a response
            visibility_timeout = Duration.minutes(3),  # This should be bingger than Lambda time out
            dead_letter_queue=invoices_bda_dlq,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=kms_key,
        )
        #### Enable CloudWatch Logs to send messages to the queue
        invoices_bda_queue.add_to_resource_policy(
            iam.PolicyStatement(
                actions=['sqs:SendMessage'],
                principals=[iam.ServicePrincipal('cloudwatch.amazonaws.com')],
                resources=[invoices_bda_queue.queue_arn]
            )
        )

        ######################################################################
        ############################ Lambda ##################################
        ######################################################################
        ##################### Create Blurprint Lambda #####################
        create_blueprint_cr_lambda = _lambda.Function(self, 
                                "create_blueprint_cr",
                                code=_lambda.Code.from_asset("./lambda/create_blueprint_cr"),
                                runtime=_lambda.Runtime.PYTHON_3_12,
                                architecture=_lambda.Architecture.ARM_64,
                                memory_size=512,
                                timeout=Duration.seconds(30),
                                handler="index.lambda_handler",
                                layers=[boto3_layer],
                                vpc=vpc,
                                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                                environment={
                                    "SSM_PARAMETER_NAME": ssm_parameter_name,
                                }
                            )
        bda_list_blueprint_policy_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:ListBlueprints",
                "bedrock:GetBlueprint",
            ],
            resources= [f"arn:aws:bedrock:{self.region}:{self.account}:blueprint/*"]
        )
        bda_create_blueprint_cr_policy_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:CreateBlueprint",],
            resources= ["*"]
        )
        ssm_put_policy_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["ssm:PutParameter",],
            resources= ["*"]
        )
        create_blueprint_cr_lambda.add_to_role_policy(bda_list_blueprint_policy_statement)
        create_blueprint_cr_lambda.add_to_role_policy(bda_create_blueprint_cr_policy_statement)
        create_blueprint_cr_lambda.add_to_role_policy(ssm_put_policy_statement)
        
        res_provider = custom_resources.Provider(scope=self,
                                                 id='CustomResourceBlueprintCreate',
                                                 on_event_handler=create_blueprint_cr_lambda)

        blueprint_create_cr = CustomResource(scope=self,
                                       id='BlueprintCreateCR',
                                       service_token=res_provider.service_token,
                                       properties={'inovices_blueprint_name': invoices_blueprint_name}) # you can also pass this as environment variable and read in lambda
        
        ##################### Process Input Files Lambda #####################
        process_input_files_lambda = _lambda.Function(self, 
                                "process_input_files",
                                code=_lambda.Code.from_asset("./lambda/process_input_files"),
                                runtime=_lambda.Runtime.PYTHON_3_12,
                                architecture=_lambda.Architecture.ARM_64,
                                memory_size=512,
                                timeout=Duration.seconds(30),
                                handler="index.lambda_handler",
                                vpc=vpc,
                                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                                environment={
                                    "INVOICES_BDA_QUEUE_URL": invoices_bda_queue.queue_url,
                                }
                            )
        invoices_bda_queue.grant_send_messages(process_input_files_lambda)
        input_bucket_s3.grant_read(process_input_files_lambda)
        kms_key.grant_encrypt_decrypt(process_input_files_lambda)

        input_bucket_s3.add_event_notification(
                s3.EventType.OBJECT_CREATED,
                aws_s3_notifications.LambdaDestination(process_input_files_lambda),
                s3.NotificationKeyFilter(
                                    prefix="",
                                    suffix=".png",
                                ),
            )
        input_bucket_s3.add_event_notification(
                s3.EventType.OBJECT_CREATED, 
                aws_s3_notifications.LambdaDestination(process_input_files_lambda),
                s3.NotificationKeyFilter(
                                    prefix="",
                                    suffix=".pdf",
                                ),
            )
        input_bucket_s3.add_event_notification(
                s3.EventType.OBJECT_CREATED, 
                aws_s3_notifications.LambdaDestination(process_input_files_lambda),
                s3.NotificationKeyFilter(
                                    prefix="",
                                    suffix=".jpg",
                                ),
            )

        ##################### Process Invoices BDA Lambda #####################
        process_invoices_bda_lambda = _lambda.Function(self, 
                                "process_invoices_bda",
                                code=_lambda.Code.from_asset("./lambda/process_invoices_bda"),
                                runtime=_lambda.Runtime.PYTHON_3_12,
                                architecture=_lambda.Architecture.ARM_64,
                                memory_size=512,
                                timeout=Duration.minutes(3),
                                handler="index.lambda_handler",
                                layers=[boto3_layer, pypdfium2_layer, pillow_layer],
                                environment={
                                    "STAGGING_BUCKET":stagging_bucket_s3.bucket_name,
                                    "OUTPUT_BUCKET":output_bucket_s3.bucket_name,
                                    "SSM_PARAMETER_NAME": ssm_parameter_name,
                                }
                            )
        input_bucket_s3.grant_read(process_invoices_bda_lambda)
        stagging_bucket_s3.grant_read_write(process_invoices_bda_lambda)
        output_bucket_s3.grant_read_write(process_invoices_bda_lambda)

        bda_invoke_job_policy_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeDataAutomationAsync","bedrock:GetDataAutomationStatus",],
            resources= [f"arn:aws:bedrock:{self.region}:{self.account}:blueprint/*",
                        f"arn:aws:bedrock:{self.region}:{self.account}:data-automation-project/*",
                        f"arn:aws:bedrock:{self.region}:{self.account}:data-automation-invocation/*",]
        )
        ssm_get_policy_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["ssm:GetParameter"],
            resources= [f"arn:aws:ssm:{self.region}:{self.account}:parameter{ssm_parameter_name}",]
        )
        process_invoices_bda_lambda.add_to_role_policy(bda_invoke_job_policy_statement)
        process_invoices_bda_lambda.add_to_role_policy(ssm_get_policy_statement)
        invoices_bda_queue.grant_consume_messages(process_invoices_bda_lambda)

        ## This event will be triggered by SQS when a new message is received
        invoke_event_source = lambda_event_sources.SqsEventSource(invoices_bda_queue, batch_size=1)
        process_invoices_bda_lambda.add_event_source(invoke_event_source)

        ##################### Dummy Lambda #####################
        draw_bboxes_invoices_lambda = _lambda.Function(self, 
                                "draw_bboxes_invoices",
                                code=_lambda.Code.from_asset("./lambda/draw_bboxes_invoices"),
                                runtime=_lambda.Runtime.PYTHON_3_12,
                                architecture=_lambda.Architecture.ARM_64,
                                memory_size=512,
                                timeout=Duration.minutes(3),
                                handler="index.lambda_handler",
                                layers=[langchain_core_layer, pypdfium2_layer, pillow_layer, boto3_layer],
                                environment={
                                    "DOC_TYPE": invoices_doc_type,
                                }
                            )
        input_bucket_s3.grant_read(draw_bboxes_invoices_lambda)
        stagging_bucket_s3.grant_read(draw_bboxes_invoices_lambda)
        output_bucket_s3.grant_read_write(draw_bboxes_invoices_lambda)
        
        event_bridge_job_completion_rule = events.Rule(
            self, 
            'EventBridgeJobCompletionRule',
            description='EventBridge rule to trigger Lambda when BDA job completes',
            rule_name="BDAJobCompletionRule",
            event_pattern=events.EventPattern(
                source=["aws.bedrock-data-insights"],
                detail_type= ["Insights Extraction Job Completed"]
            )
        )

        # Add State Change Lambda function as a target to the EventBridge rule
        event_bridge_job_completion_rule.add_target(targets.LambdaFunction(draw_bboxes_invoices_lambda))

        #######################################################################
        ######################### CDK Nag Suppression #########################
        #######################################################################
        NagSuppressions.add_resource_suppressions([create_blueprint_cr_lambda.role, 
                                                   process_input_files_lambda.role,
                                                   process_invoices_bda_lambda.role,
                                                   draw_bboxes_invoices_lambda.role,
                                                   ],
                            suppressions=[ {
                                                "id": "AwsSolutions-IAM4",
                                                "reason": "This code is for demo purposes. So granted full access to Bedrock service.",
                                            },
                                            {
                                                "id": "AwsSolutions-IAM5",
                                                "reason": "This code is for demo purposes. So granted access to all indices of S3 bucket.",
                                            },
                                        ],
                            apply_to_children=True)
        
        # CDK NAG suppression
        NagSuppressions.add_resource_suppressions([create_blueprint_cr_lambda, 
                                                   process_input_files_lambda,
                                                   process_invoices_bda_lambda,
                                                   draw_bboxes_invoices_lambda,
                                                   ],
                            suppressions=[  {   "id": "AwsSolutions-L1", 
                                                "reason": "This code is for demo purposes. So using Python 3.12."
                                             }
                                        ],
                            apply_to_children=True)
        
        # CDK NAG suppression
        NagSuppressions.add_resource_suppressions([res_provider],
                            suppressions=[  {
                                                "id": "AwsSolutions-IAM5",
                                                "reason": "This code is for demo purposes. So granted access to all indices of S3 bucket.",
                                            },
                                        ],
                            apply_to_children=True)
        # CDK NAG suppression
        NagSuppressions.add_stack_suppressions(self, 
                                        [
                                            {
                                                "id": 'AwsSolutions-IAM4',
                                                "reason": 'Lambda execution policy for custom resources created by higher level CDK constructs',
                                                "appliesTo": [
                                                        'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
                                                    ],
                                            },
                                        ])
        
        # CDK NAG suppression
        NagSuppressions.add_resource_suppressions_by_path(            
            self,
            path="/idp-bda/BucketNotificationsHandler050a0587b7544547bf325f094a3db834/Role/DefaultPolicy/Resource",
            suppressions = [
                            { "id": 'AwsSolutions-IAM5', "reason": 'CDK BucketNotificationsHandler L1 Construct' },
                        ],
            apply_to_children=True
        )
        