import boto3
import zipfile
import io

def deploy_fixed_download():
    """Deploy a fix for the download URL function"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Deploying download URL fix for: {FUNCTION_NAME}")
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the updated generate_download_url function
        lambda_code = '''
def generate_download_url(bucket, key):
    """Generate a presigned URL for downloading an object"""
    try:
        # Check if object exists
        try:
            s3.head_object(Bucket=bucket, Key=key)
        except:
            return f"❌ File '{key}' does not exist in bucket '{bucket}'."
        
        # Generate presigned URL (valid for 1 hour)
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=3600
        )
        
        # Format the URL as a clickable link for HTML
        clickable_url = f'<a href="{url}" target="_blank">Click here to download {key}</a>'
        
        return f"✅ Download link for '{key}' (valid for 1 hour):\\n{clickable_url}"
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"
'''
        
        # First, get the current Lambda function code
        lambda_client = boto3.client('lambda')
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
        
        # Check if the generate_download_url function exists
        if 'def generate_download_url(' in current_code:
            # Replace the existing function
            import re
            pattern = r'def generate_download_url\([^)]*\):.*?(?=def \w+\(|$)'
            updated_code = re.sub(pattern, lambda_code, current_code, flags=re.DOTALL)
        else:
            # Add the function before the last function (usually create_response)
            last_def_pos = current_code.rfind('def ')
            updated_code = current_code[:last_def_pos] + lambda_code + '\n\n' + current_code[last_def_pos:]
            
            # Also add the download command handler if it doesn't exist
            if 'download file' not in current_code:
                download_handler = '''
        # Download file command (generate presigned URL)
        if 'download file' in user_message_lower and 'from' in user_message_lower:
            parts = user_message_lower.split('download file')[1].split('from')
            if len(parts) == 2:
                file_name = parts[0].strip()
                bucket_name = parts[1].strip()
                if file_name and bucket_name:
                    result = generate_download_url(bucket_name, file_name)
                    return create_response(result)
            return create_response("Syntax: `download file FILE_NAME from BUCKET`\\nExample: download file data.txt from my-bucket")
'''
                # Find a good place to insert the handler (before the catch-all handler)
                handler_pos = current_code.find('# For other commands')
                if handler_pos > 0:
                    updated_code = updated_code[:handler_pos] + download_handler + updated_code[handler_pos:]
        
        # Write the updated code
        with open('lambda_extract/lambda_function.py', 'w') as f:
            f.write(updated_code)
        
        # Create a new zip file with the updated code
        for root, dirs, files in zip_file.namelist():
            for file in files:
                if file == 'lambda_function.py':
                    zip_file.write('lambda_extract/lambda_function.py', 'lambda_function.py')
                else:
                    zip_file.write(os.path.join(root, file), 
                                  os.path.relpath(os.path.join(root, file), 
                                                 os.path.join('lambda_extract', '..')))
    
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
        
        print(f"✅ Lambda function updated successfully")
        print(f"Version: {response.get('Version')}")
        
        print("\n✅ Deployment complete!")
        print("The download URL function now provides a clickable link.")
        
        # Clean up
        import os
        import shutil
        os.remove('lambda_current.zip')
        shutil.rmtree('lambda_extract')
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    deploy_fixed_download()