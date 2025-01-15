#!/usr/bin/env python3

## Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
## Licensed under the Amazon Software License  https://aws.amazon.com/asl/
import json
import cdk_nag
from aws_cdk import Aspects
import aws_cdk as cdk
from idp_invoice_automation_using_bedrock_data_automation_cdk.idp_stack import IDPStack


with open('project_config.json', 'r') as file:
    variables = json.load(file)

app = cdk.App()
idp_stack = IDPStack(app, variables["idp_stack_name"],)

Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(reports=True, verbose=True))
app.synth()
