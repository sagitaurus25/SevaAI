import boto3
import zipfile
import io
import os
import time

def deploy_lambda():
    """Deploy the fixed Lambda function"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Deploying fixed Lambda function: {FUNCTION_NAME}")
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the Lambda function code
        lambda_file = 'lambda_fixed_complete.py'
        if os.path.exists(lambda_file):
            # Add the file as lambda_function.py (the handler name)
            zip_file.write(lambda_file, 'lambda_function.py')
            print(f"✅ Added {lambda_file} as lambda_function.py to deployment package")
        else:
            print(f"❌ Error: {lambda_file} not found")
            return False
    
    # Get the zip file content
    zip_buffer.seek(0)
    zip_content = zip_buffer.read()
    
    # Update the Lambda function
    try:
        lambda_client = boto3.client('lambda')
        
        # Update the function code
        response = lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_content,
            Publish=True
        )
        
        print(f"✅ Lambda function code updated successfully")
        print(f"Version: {response.get('Version')}")
        
        # Wait for the function to be active
        print("Waiting for function to be active...")
        time.sleep(5)
        
        # Test the function
        test_response = lambda_client.invoke(
            FunctionName=FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload='{"body": "{\\\"message\\\":\\\"help\\\",\\\"session_id\\\":\\\"test-session\\\"}"}'
        )
        
        payload = test_response['Payload'].read().decode('utf-8')
        print(f"Test response: {payload[:100]}...")
        
        print("\n✅ Deployment complete!")
        print("You can now use the S3 agent interface to interact with your S3 buckets.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    deploy_lambda()