#!/usr/bin/env python3

import boto3
import zipfile
import io
import json

def add_organize_images_command():
    """Add organize images command to the S3 agent"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Adding organize images command to Lambda function: {FUNCTION_NAME}")
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
        # Get the current Lambda function code
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
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
        
        # Add organize_images function
        organize_images_function = '''
def organize_images_by_date(bucket):
    """Organize images in a bucket by date (year/month folders)"""
    try:
        # Check if bucket exists
        try:
            s3.head_bucket(Bucket=bucket)
        except:
            return f"❌ Bucket '{bucket}' does not exist."
        
        # Get all objects in the bucket
        response = s3.list_objects_v2(Bucket=bucket)
        if 'Contents' not in response:
            return f"Bucket '{bucket}' is empty."
        
        # Track statistics
        stats = {
            'total_files': 0,
            'image_files': 0,
            'organized_files': 0,
            'skipped_files': 0,
            'errors': 0
        }
        
        # Process each object
        for obj in response['Contents']:
            key = obj['Key']
            stats['total_files'] += 1
            
            # Skip if already in a year/month folder structure
            if re.match(r'^[0-9]{4}/[0-9]{2}/', key):
                stats['skipped_files'] += 1
                continue
            
            # Check if it's an image file
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic']
            if not any(key.lower().endswith(ext) for ext in image_extensions):
                continue
                
            stats['image_files'] += 1
            
            try:
                # Get object metadata
                metadata = s3.head_object(Bucket=bucket, Key=key)
                
                # Use last modified date
                date = metadata['LastModified']
                
                # Create new key with year/month structure
                year_month = date.strftime('%Y/%m')
                filename = key.split('/')[-1]
                new_key = f"{year_month}/{filename}"
                
                # Skip if file already exists at destination
                try:
                    s3.head_object(Bucket=bucket, Key=new_key)
                    stats['skipped_files'] += 1
                    continue
                except:
                    pass
                
                # Copy object to new location
                s3.copy_object(
                    CopySource={'Bucket': bucket, 'Key': key},
                    Bucket=bucket,
                    Key=new_key
                )
                
                # Delete original object
                s3.delete_object(Bucket=bucket, Key=key)
                
                stats['organized_files'] += 1
            except Exception as e:
                print(f"Error processing {key}: {str(e)}")
                stats['errors'] += 1
        
        # Generate summary message
        summary = f"✅ Image organization complete for bucket '{bucket}':\\n"
        summary += f"• Total files scanned: {stats['total_files']}\\n"
        summary += f"• Image files found: {stats['image_files']}\\n"
        summary += f"• Files organized: {stats['organized_files']}\\n"
        summary += f"• Files skipped: {stats['skipped_files']}\\n"
        
        if stats['errors'] > 0:
            summary += f"• Errors: {stats['errors']}\\n"
        
        return summary
        
    except Exception as e:
        return f"❌ Error organizing images: {str(e)}"
'''
        
        # Add import for re module
        if 'import re' not in current_code:
            current_code = current_code.replace('import uuid', 'import uuid\nimport re')
        
        # Add the function to the code
        function_insertion_point = current_code.rfind('def test_connectivity')
        updated_code = current_code[:function_insertion_point] + organize_images_function + '\n\n' + current_code[function_insertion_point:]
        
        # Add command handler in lambda_handler
        command_handler = '''
        # Organize images command
        if user_message_lower.startswith('organize images in '):
            bucket_name = user_message[18:].strip()
            if bucket_name:
                result = organize_images_by_date(bucket_name)
                return create_response(result)
            else:
                return create_response("Please specify a bucket name. Example: organize images in my-bucket")
        
        # Organize images command (alternative syntax)
        if 'organize images' in user_message_lower and 'in' in user_message_lower:
            parts = user_message_lower.split('in')
            if len(parts) > 1:
                bucket = parts[1].strip()
                result = organize_images_by_date(bucket)
                return create_response(result)
'''
        
        # Find a good place to insert the command handler
        handler_insertion_point = updated_code.find('# Handle bucket name response after list files')
        updated_code = updated_code[:handler_insertion_point] + command_handler + updated_code[handler_insertion_point:]
        
        # Add syntax helper
        syntax_helper = '''
        if user_message_lower == 'organize' or user_message_lower == 'organize images':
            return create_response("Syntax: `organize images in BUCKET_NAME`\\nExample: organize images in my-photos-bucket")
'''
        
        # Find a good place to insert the syntax helper
        helper_insertion_point = updated_code.find('# List buckets')
        updated_code = updated_code[:helper_insertion_point] + syntax_helper + updated_code[helper_insertion_point:]
        
        # Update help message
        help_message = updated_code.split('def get_help_message()')[1]
        help_message_start = help_message.find('return """')
        help_message_end = help_message.find('"""', help_message_start + 8)
        
        new_help_message = help_message[:help_message_start] + 'return """🤖 **Available Commands:**\n\n**📦 S3 Operations:**\n• `list buckets` - Show all S3 buckets\n• `list files` - Show objects in a bucket (you\'ll be asked which bucket)\n• `list files in BUCKET` - Show objects in specific bucket\n• `create bucket NAME` - Create a new bucket\n• `delete bucket NAME` - Delete an empty bucket\n• `delete file FILE from BUCKET` - Delete a file from a bucket\n• `copy file FILE from BUCKET1 to BUCKET2` - Copy a file between buckets\n• `organize images in BUCKET` - Organize images into year/month folders\n\n**🔧 System Commands:**\n• `help` - Show this help message\n• `test` - Test connectivity to AWS services\n\n**💡 Examples:**\n• "list my buckets"\n• "list files in my-data-bucket"\n• "create bucket new-bucket-name"\n• "organize images in my-photos-bucket"\n\nYou can also type partial commands like "delete" or "organize" to get syntax help.\n"""' + help_message[help_message_end + 3:]
        
        updated_code = updated_code.split('def get_help_message()')[0] + 'def get_help_message()' + new_help_message
        
        # Write the updated code
        with open('lambda_extract/lambda_function.py', 'w') as f:
            f.write(updated_code)
        
        # Add the updated file to the zip
        zip_file.write('lambda_extract/lambda_function.py', 'lambda_function.py')
    
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
        
        # Update the function configuration to increase timeout
        lambda_client.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Timeout=300  # 5 minutes
        )
        
        print("✅ Lambda function timeout increased to 5 minutes")
        
        # Clean up
        import os
        import shutil
        os.remove('lambda_current.zip')
        shutil.rmtree('lambda_extract')
        
        print("\n✅ Deployment complete!")
        print("The S3 agent now supports the 'organize images in BUCKET' command.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    add_organize_images_command()