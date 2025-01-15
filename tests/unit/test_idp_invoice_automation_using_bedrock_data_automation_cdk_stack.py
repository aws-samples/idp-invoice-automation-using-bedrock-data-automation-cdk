import aws_cdk as core
import aws_cdk.assertions as assertions

from idp_invoice_automation_using_bedrock_data_automation_cdk.idp_stack import IdpInvoiceAutomationUsingBedrockDataAutomationCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in idp_invoice_automation_using_bedrock_data_automation_cdk/idp_invoice_automation_using_bedrock_data_automation_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = IdpInvoiceAutomationUsingBedrockDataAutomationCdkStack(app, "idp-invoice-automation-using-bedrock-data-automation-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
