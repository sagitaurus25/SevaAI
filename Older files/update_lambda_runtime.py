import boto3
import json

def update_lambda_runtime():
    """Update the Lambda function's runtime to the latest version"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Updating Lambda runtime for: {FUNCTION_NAME}")
    
    try:
        # Create Lambda client
        lambda_client = boto3.client('lambda')
        
        # Get current function configuration
        response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
        current_runtime = response['Configuration']['Runtime']
        
        print(f"Current runtime: {current_runtime}")
        
        # Update to the latest Python runtime (3.12 as of 2024)
        new_runtime = 'python3.12'
        
        if current_runtime != new_runtime:
            print(f"Updating runtime from {current_runtime} to {new_runtime}...")
            
            lambda_client.update_function_configuration(
                FunctionName=FUNCTION_NAME,
                Runtime=new_runtime
            )
            
            print(f"✅ Runtime updated to {new_runtime}")
        else:
            print(f"Runtime is already at the latest version: {current_runtime}")
        
        # Also update the timeout to 30 seconds (default is 3 seconds)
        print("Updating timeout to 30 seconds...")
        lambda_client.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Timeout=30
        )
        print("✅ Timeout updated to 30 seconds")
        
        # Update memory to 256MB (default is 128MB)
        print("Updating memory to 256MB...")
        lambda_client.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            MemorySize=256
        )
        print("✅ Memory updated to 256MB")
        
        print("\n✅ Lambda function configuration updated successfully!")
        print("It may take a few minutes for the changes to propagate.")
        print("Try your S3 commands again in a minute or two.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda runtime: {str(e)}")
        return False

if __name__ == "__main__":
    update_lambda_runtime()