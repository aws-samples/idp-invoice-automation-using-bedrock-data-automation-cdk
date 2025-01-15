## Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
## SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
## Licensed under the Amazon Software License  https://aws.amazon.com/asl/
import boto3
from botocore.config import Config
from io import BytesIO
import pypdfium2


#increase the standard time out limits in boto3, because Bedrock may take a while to respond to large requests.
my_config = Config(
    connect_timeout=60*5,
    read_timeout=60*5,
)

s3_client=boto3.client("s3")
s3_resource = boto3.resource('s3')
ssm = boto3.client('ssm')
bda_client = boto3.client('bedrock-data-automation')
bda_runtime_client = boto3.client('bedrock-data-automation-runtime')

def save_image_to_s3(image, bucket, key):
    with BytesIO() as image_buffer:
        image.save(image_buffer, 'PNG')
        image_buffer.seek(0)
        s3_client.upload_fileobj(image_buffer, bucket, key)
    return bucket, key

def convert_pdf_to_png(input_bucket, input_key, output_bucket, output_key):
    pdf_obj = s3_resource.Object(input_bucket, input_key).get()['Body'].read()
    pdf = pypdfium2.PdfDocument(pdf_obj)
    n_pages = len(pdf)  # get the number of pages in the document
    print("Number of pages:", n_pages)
    page = pdf[0] # we will take first page only
    bitmap = page.render(scale=2, rotation=0)
    pil_image = bitmap.to_pil()
    save_image_to_s3(pil_image, output_bucket, output_key)
    return output_bucket, output_key

def invoke_data_automation(input_s3_uri, output_s3_uri, blueprint_arn):
    response = bda_runtime_client.invoke_data_automation_async(
                                inputConfiguration={
                                    's3Uri': input_s3_uri
                                },
                                outputConfiguration={
                                    's3Uri': output_s3_uri
                                },
                                notificationConfiguration={
                                    'eventBridgeConfiguration': {
                                        'eventBridgeEnabled': True
                                    }
                                },
                                blueprints=[{'blueprintArn': blueprint_arn},]
                            )
    return response

def get_parameter_from_ssm(param_name):
    response = ssm.get_parameter(
            Name=param_name,
            WithDecryption=True
        )
    param_value = response['Parameter']['Value']
    return param_value