import boto3
import zipfile
import io
import os
import time

def update_lambda_function():
    """Update the Lambda function with the parsing fix"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Updating Lambda function with parsing fix: {FUNCTION_NAME}")
    
    # Get the current Lambda function code
    lambda_client = boto3.client('lambda')
    
    try:
        # Get the current function code
        response = lambda_client.get_function(
            FunctionName=FUNCTION_NAME
        )
        
        # Download the current code
        code_location = response['Code']['Location']
        
        import requests
        r = requests.get(code_location)
        
        # Save the current code
        with open('lambda_current.zip', 'wb') as f:
            f.write(r.content)
        
        # Extract the current code
        with zipfile.ZipFile('lambda_current.zip', 'r') as zip_ref:
            zip_ref.extractall('lambda_extract')
        
        # Read the current lambda_function.py
        with open('lambda_extract/lambda_function.py', 'r') as f:
            current_code = f.read()
        
        # Read the fix_nova_parsing.py
        with open('fix_nova_parsing.py', 'r') as f:
            fix_code = f.read()
        
        # Extract the parse_with_nova function from fix_code
        import re
        parse_function = re.search(r'def parse_with_nova\(.*?\):.*?(?=\n\n# Test the function|\Z)', fix_code, re.DOTALL)
        
        if parse_function:
            parse_function_code = parse_function.group(0)
            
            # Replace the parse_with_nova function in the current code
            updated_code = re.sub(r'def parse_with_nova\(.*?\):.*?(?=\n\ndef execute_command|\Z)', parse_function_code, current_code, flags=re.DOTALL)
            
            # Write the updated code
            with open('lambda_extract/lambda_function.py', 'w') as f:
                f.write(updated_code)
            
            # Create a new zip file
            with zipfile.ZipFile('lambda_updated.zip', 'w') as zipf:
                for root, dirs, files in os.walk('lambda_extract'):
                    for file in files:
                        zipf.write(os.path.join(root, file), 
                                  os.path.relpath(os.path.join(root, file), 
                                                 os.path.join('lambda_extract', '..')))
            
            # Read the updated zip file
            with open('lambda_updated.zip', 'rb') as f:
                zip_content = f.read()
            
            # Update the Lambda function
            response = lambda_client.update_function_code(
                FunctionName=FUNCTION_NAME,
                ZipFile=zip_content,
                Publish=True
            )
            
            print(f"✅ Lambda function updated successfully")
            print(f"Version: {response.get('Version')}")
            
            # Clean up
            os.remove('lambda_current.zip')
            os.remove('lambda_updated.zip')
            import shutil
            shutil.rmtree('lambda_extract')
            
            return True
        else:
            print("❌ Could not extract parse_with_nova function from fix code")
            return False
            
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    update_lambda_function()