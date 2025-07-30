import boto3
import zipfile
import os
import io
import sys

def create_lambda_function():
    """Create the Lambda function with knowledge base integration"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Creating Lambda function: {FUNCTION_NAME}")
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the Lambda function code
        lambda_file = 'lambda_nova_parser_correct.py'
        if os.path.exists(lambda_file):
            zip_file.write(lambda_file)
            print(f"✅ Added {lambda_file} to deployment package")
        else:
            print(f"❌ Error: {lambda_file} not found")
            return False
    
    # Get the zip file content
    zip_buffer.seek(0)
    zip_content = zip_buffer.read()
    
    # Create the Lambda function
    try:
        lambda_client = boto3.client('lambda')
        
        # Get the Lambda execution role
        print("\nPlease enter the ARN of the Lambda execution role:")
        print("(This role should have permissions for S3, DynamoDB, and Bedrock)")
        role_arn = input("Role ARN: ")
        
        response = lambda_client.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime='python3.9',
            Role=role_arn,
            Handler='lambda_nova_parser_correct.lambda_handler',
            Code={
                'ZipFile': zip_content
            },
            Timeout=30,
            MemorySize=256,
            Environment={
                'Variables': {
                    'KNOWLEDGE_BASE_TABLE': 'S3CommandKnowledgeBase'
                }
            }
        )
        
        print(f"\n✅ Lambda function '{FUNCTION_NAME}' created successfully!")
        print(f"Function ARN: {response.get('FunctionArn')}")
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    create_lambda_function()