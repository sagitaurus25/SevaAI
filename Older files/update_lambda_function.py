import boto3
import zipfile
import os
import io
import sys

def update_lambda_function():
    """Update the Lambda function with knowledge base integration"""
    
    # Lambda function name - update this to match your function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Updating Lambda function: {FUNCTION_NAME}")
    
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
    
    # Update the Lambda function
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_content,
            Publish=True
        )
        
        print(f"✅ Lambda function updated successfully!")
        print(f"Version: {response.get('Version')}")
        print(f"Last Modified: {response.get('LastModified')}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return False

def check_lambda_environment():
    """Check if the Lambda function has the required environment variables"""
    
    # Lambda function name - update this to match your function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function_configuration(
            FunctionName=FUNCTION_NAME
        )
        
        env_vars = response.get('Environment', {}).get('Variables', {})
        
        print(f"\nLambda Environment Variables:")
        print("-" * 50)
        
        for key, value in env_vars.items():
            print(f"• {key}: {value}")
        
        # Check for required environment variables
        required_vars = ['KNOWLEDGE_BASE_TABLE']
        missing_vars = [var for var in required_vars if var not in env_vars]
        
        if missing_vars:
            print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
            
            # Add the missing environment variables
            print("\nAdding missing environment variables...")
            
            updated_vars = env_vars.copy()
            if 'KNOWLEDGE_BASE_TABLE' not in updated_vars:
                updated_vars['KNOWLEDGE_BASE_TABLE'] = 'S3CommandKnowledgeBase'
            
            lambda_client.update_function_configuration(
                FunctionName=FUNCTION_NAME,
                Environment={
                    'Variables': updated_vars
                }
            )
            
            print("✅ Environment variables updated")
        else:
            print("\n✅ All required environment variables are set")
        
    except Exception as e:
        print(f"❌ Error checking Lambda environment: {str(e)}")

if __name__ == "__main__":
    if update_lambda_function():
        check_lambda_environment()