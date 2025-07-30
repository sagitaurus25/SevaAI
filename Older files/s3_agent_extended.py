import boto3
import zipfile
import io

def deploy_extended_s3_agent():
    """Deploy an extended S3 agent with additional functions"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Deploying extended S3 agent: {FUNCTION_NAME}")
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the Lambda function code with triple quotes properly escaped
        lambda_code = '''
import json
import boto3
import uuid
from datetime import datetime
import re

# Initialize AWS clients
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """Main Lambda handler function"""
    try:
        # Extract user message from event
        body = json.loads(event.get('body', '{}'))
        user_message = body.get('message', '')
        session_id = body.get('session_id', str(uuid.uuid4()))
        
        if not user_message:
            return create_response("Please provide a message.")
        
        # Special commands
        if user_message.lower() == 'help':
            return create_response(get_help_message())
        elif user_message.lower() == 'test':
            return create_response(test_connectivity())
        
        # Direct handling for common commands
        user_message_lower = user_message.lower()
        
        # Syntax helpers for partial commands
        if user_message_lower == 'list':
            return create_response("Available list commands:\\n• `list buckets` - Show all S3 buckets\\n• `list files` - Show objects in a bucket\\n• `list files in BUCKET` - Show objects in specific bucket")
        
        if user_message_lower == 'create':
            return create_response("Available create commands:\\n• `create bucket BUCKET_NAME` - Create a new bucket\\n• `create folder FOLDER_NAME in BUCKET` - Create a new folder in a bucket")
        
        if user_message_lower == 'delete':
            return create_response("Available delete commands:\\n• `delete bucket BUCKET_NAME` - Delete an empty bucket\\n• `delete file FILE_NAME from BUCKET_NAME` - Delete a file from a bucket\\n• `delete folder FOLDER_NAME from BUCKET` - Delete a folder and its contents")
        
        if user_message_lower == 'delete file' or user_message_lower == 'delete files':
            return create_response("Syntax: `delete file FILE_NAME from BUCKET_NAME`\\nExample: delete file data.txt from my-bucket")
        
        if user_message_lower == 'copy' or user_message_lower == 'copy file':
            return create_response("Syntax: `copy file FILE_NAME from SOURCE_BUCKET to DESTINATION_BUCKET`\\nExample: copy file data.txt from source-bucket to target-bucket")
        
        if user_message_lower == 'download' or user_message_lower == 'download file':
            return create_response("Syntax: `download file FILE_NAME from BUCKET`\\nExample: download file data.txt from my-bucket")
        
        if user_message_lower == 'upload' or user_message_lower == 'upload file':
            return create_response("Syntax: `upload file FILE_NAME to BUCKET`\\nExample: upload file data.txt to my-bucket\\n\\nNote: For actual file uploads, you'll need to use the AWS Console or AWS CLI.")
        
        if user_message_lower == 'search' or user_message_lower == 'find':
            return create_response("Syntax: `search for PATTERN in BUCKET`\\nExample: search for .jpg in my-bucket")
        
        # List buckets
        if user_message_lower in ['list buckets', 'show buckets', 'list my buckets']:
            result = list_buckets()
            return create_response(result)
        
        # List files command
        if user_message_lower == 'list files':
            return create_response("Which bucket would you like to list files from?")
        
        # Create bucket command
        if user_message_lower.startswith('create bucket '):
            bucket_name = user_message[14:].strip()
            if bucket_name:
                result = create_bucket(bucket_name)
                return create_response(result)
            else:
                return create_response("Please specify a bucket name. Example: create bucket my-new-bucket")
        
        # Create folder command
        if 'create folder' in user_message_lower and 'in' in user_message_lower:
            parts = user_message_lower.split('create folder')[1].split('in')
            if len(parts) == 2:
                folder_name = parts[0].strip()
                bucket_name = parts[1].strip()
                if folder_name and bucket_name:
                    result = create_folder(bucket_name, folder_name)
                    return create_response(result)
            return create_response("Syntax: `create folder FOLDER_NAME in BUCKET`\\nExample: create folder my-folder in my-bucket")
        
        # Delete bucket command
        if user_message_lower.startswith('delete bucket '):
            bucket_name = user_message[14:].strip()
            if bucket_name:
                result = delete_bucket(bucket_name)
                return create_response(result)
            else:
                return create_response("Please specify a bucket name. Example: delete bucket my-bucket")
        
        # Delete file command
        if 'delete file' in user_message_lower and 'from' in user_message_lower:
            parts = user_message_lower.split('delete file')[1].split('from')
            if len(parts) == 2:
                file_name = parts[0].strip()
                bucket_name = parts[1].strip()
                if file_name and bucket_name:
                    result = delete_object(bucket_name, file_name)
                    return create_response(result)
            return create_response("Syntax: `delete file FILE_NAME from BUCKET_NAME`\\nExample: delete file data.txt from my-bucket")
        
        # Delete folder command
        if 'delete folder' in user_message_lower and 'from' in user_message_lower:
            parts = user_message_lower.split('delete folder')[1].split('from')
            if len(parts) == 2:
                folder_name = parts[0].strip()
                bucket_name = parts[1].strip()
                if folder_name and bucket_name:
                    result = delete_folder(bucket_name, folder_name)
                    return create_response(result)
            return create_response("Syntax: `delete folder FOLDER_NAME from BUCKET`\\nExample: delete folder my-folder from my-bucket")
        
        # Copy file command
        if 'copy file' in user_message_lower and 'from' in user_message_lower and 'to' in user_message_lower:
            try:
                # Extract file name (between "copy file" and "from")
                file_start = user_message_lower.index('copy file') + 10
                from_start = user_message_lower.index('from', file_start)
                file_name = user_message[file_start:from_start].strip()
                
                # Extract source bucket (between "from" and "to")
                from_start += 5  # length of "from "
                to_start = user_message_lower.index('to', from_start)
                source_bucket = user_message[from_start:to_start].strip()
                
                # Extract destination bucket (after "to")
                to_start += 3  # length of "to "
                dest_bucket = user_message[to_start:].strip()
                
                if file_name and source_bucket and dest_bucket:
                    result = copy_object(source_bucket, dest_bucket, file_name)
                    return create_response(result)
            except:
                pass
            return create_response("Syntax: `copy file FILE_NAME from SOURCE_BUCKET to DESTINATION_BUCKET`\\nExample: copy file data.txt from source-bucket to target-bucket")
        
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
        
        # Search for files
        if ('search for' in user_message_lower or 'find' in user_message_lower) and 'in' in user_message_lower:
            match = re.search(r'(search for|find)\s+(.+?)\s+in\s+(.+)', user_message_lower)
            if match:
                pattern = match.group(2).strip()
                bucket = match.group(3).strip()
                if pattern and bucket:
                    result = search_objects(bucket, pattern)
                    return create_response(result)
            return create_response("Syntax: `search for PATTERN in BUCKET`\\nExample: search for .jpg in my-bucket")
        
        # Get bucket info
        if user_message_lower.startswith('info bucket ') or user_message_lower.startswith('bucket info '):
            bucket_name = user_message_lower.replace('info bucket ', '').replace('bucket info ', '').strip()
            if bucket_name:
                result = get_bucket_info(bucket_name)
                return create_response(result)
            return create_response("Syntax: `info bucket BUCKET_NAME`\\nExample: info bucket my-bucket")
        
        # Handle bucket name response after list files
        if len(user_message.split()) == 1:  # Single word response, likely a bucket name
            result = list_objects(user_message)
            return create_response(result)
        
        # Handle list files in bucket
        if 'list files in' in user_message_lower:
            parts = user_message_lower.split('list files in')
            if len(parts) > 1:
                bucket = parts[1].strip()
                result = list_objects(bucket)
                return create_response(result)
        
        # For other commands, use a simple approach
        return create_response("I can help with S3 operations. Try 'list buckets', 'list files', or 'help'.")
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return create_response(f"Sorry, I encountered an error: {str(e)}")

def list_buckets():
    """List S3 buckets"""
    try:
        response = s3.list_buckets()
        buckets = [b['Name'] for b in response.get('Buckets', [])]
        if not buckets:
            return "You don't have any S3 buckets."
        return f"📦 S3 Buckets ({len(buckets)}):\\n" + "\\n".join(buckets)
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def list_objects(bucket):
    """List objects in an S3 bucket"""
    try:
        response = s3.list_objects_v2(Bucket=bucket, MaxKeys=50)
        objects = [obj['Key'] for obj in response.get('Contents', [])]
        
        if not objects:
            return f"Bucket '{bucket}' is empty."
        
        return f"📁 Objects in '{bucket}' ({len(objects)}):\\n" + "\\n".join(objects)
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def create_bucket(bucket):
    """Create an S3 bucket"""
    try:
        s3.create_bucket(Bucket=bucket)
        return f"✅ Bucket '{bucket}' created successfully."
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def create_folder(bucket, folder):
    """Create a folder in an S3 bucket"""
    try:
        # Ensure folder name ends with a slash
        if not folder.endswith('/'):
            folder += '/'
        
        # Create an empty object with the folder name
        s3.put_object(Bucket=bucket, Key=folder)
        return f"✅ Folder '{folder}' created in bucket '{bucket}'."
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def delete_bucket(bucket):
    """Delete an S3 bucket"""
    try:
        # Check if bucket exists
        s3.head_bucket(Bucket=bucket)
        
        # Check if bucket is empty
        response = s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
        if response.get('Contents'):
            return f"❌ Cannot delete bucket '{bucket}' because it's not empty. Please delete all objects first."
        
        # Delete the bucket
        s3.delete_bucket(Bucket=bucket)
        return f"✅ Bucket '{bucket}' deleted successfully."
    except s3.exceptions.NoSuchBucket:
        return f"❌ Bucket '{bucket}' does not exist."
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def delete_object(bucket, key):
    """Delete an object from an S3 bucket"""
    try:
        s3.delete_object(Bucket=bucket, Key=key)
        return f"✅ File '{key}' deleted from bucket '{bucket}'."
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def delete_folder(bucket, folder):
    """Delete a folder and its contents from an S3 bucket"""
    try:
        # Ensure folder name ends with a slash
        if not folder.endswith('/'):
            folder += '/'
        
        # List all objects in the folder
        response = s3.list_objects_v2(Bucket=bucket, Prefix=folder)
        
        if not response.get('Contents'):
            return f"❌ Folder '{folder}' not found in bucket '{bucket}'."
        
        # Delete all objects in the folder
        objects = [{'Key': obj['Key']} for obj in response.get('Contents', [])]
        s3.delete_objects(Bucket=bucket, Delete={'Objects': objects})
        
        return f"✅ Folder '{folder}' and {len(objects)} objects deleted from bucket '{bucket}'."
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def copy_object(source_bucket, dest_bucket, key):
    """Copy an object from one S3 bucket to another"""
    try:
        # Check if source bucket exists
        try:
            s3.head_bucket(Bucket=source_bucket)
        except:
            return f"❌ Source bucket '{source_bucket}' does not exist."
        
        # Check if destination bucket exists
        try:
            s3.head_bucket(Bucket=dest_bucket)
        except:
            return f"❌ Destination bucket '{dest_bucket}' does not exist."
        
        # Check if object exists in source bucket
        try:
            s3.head_object(Bucket=source_bucket, Key=key)
        except:
            return f"❌ File '{key}' does not exist in bucket '{source_bucket}'."
        
        # Copy the object
        s3.copy_object(
            CopySource={'Bucket': source_bucket, 'Key': key},
            Bucket=dest_bucket,
            Key=key
        )
        
        return f"✅ File '{key}' copied from '{source_bucket}' to '{dest_bucket}'."
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

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
        
        return f"✅ Download URL for '{key}' (valid for 1 hour):\\n{url}"
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def search_objects(bucket, pattern):
    """Search for objects in a bucket matching a pattern"""
    try:
        # Check if bucket exists
        try:
            s3.head_bucket(Bucket=bucket)
        except:
            return f"❌ Bucket '{bucket}' does not exist."
        
        # List all objects in the bucket
        response = s3.list_objects_v2(Bucket=bucket)
        
        if not response.get('Contents'):
            return f"Bucket '{bucket}' is empty."
        
        # Filter objects by pattern
        matching_objects = []
        for obj in response.get('Contents', []):
            if pattern in obj['Key'].lower():
                matching_objects.append(obj['Key'])
        
        if not matching_objects:
            return f"No objects matching '{pattern}' found in bucket '{bucket}'."
        
        return f"📁 Objects matching '{pattern}' in '{bucket}' ({len(matching_objects)}):\\n" + "\\n".join(matching_objects)
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def get_bucket_info(bucket):
    """Get information about a bucket"""
    try:
        # Check if bucket exists
        try:
            s3.head_bucket(Bucket=bucket)
        except:
            return f"❌ Bucket '{bucket}' does not exist."
        
        # Get bucket location
        location = s3.get_bucket_location(Bucket=bucket)
        region = location.get('LocationConstraint') or 'us-east-1'
        
        # Count objects and total size
        response = s3.list_objects_v2(Bucket=bucket)
        object_count = 0
        total_size = 0
        
        if response.get('Contents'):
            object_count = len(response.get('Contents', []))
            total_size = sum(obj['Size'] for obj in response.get('Contents', []))
        
        # Format size
        size_str = format_size(total_size)
        
        return f"📊 Bucket Info: '{bucket}'\\n" + \
               f"Region: {region}\\n" + \
               f"Objects: {object_count}\\n" + \
               f"Total Size: {size_str}"
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def format_size(size_bytes):
    """Format size in bytes to human-readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def test_connectivity():
    """Test connectivity to AWS services"""
    results = []
    
    try:
        # Test S3
        s3.list_buckets()
        results.append("✅ S3: Connected")
    except Exception as e:
        results.append(f"❌ S3: {str(e)}")
    
    return "\\n".join(results)

def get_help_message():
    """Return help message with available commands"""
    return """🤖 **Available Commands:**

**📦 S3 Bucket Operations:**
• `list buckets` - Show all S3 buckets
• `create bucket NAME` - Create a new bucket
• `delete bucket NAME` - Delete an empty bucket
• `info bucket NAME` - Show information about a bucket

**📁 File Operations:**
• `list files` - Show objects in a bucket (you'll be asked which bucket)
• `list files in BUCKET` - Show objects in specific bucket
• `delete file FILE from BUCKET` - Delete a file from a bucket
• `copy file FILE from BUCKET1 to BUCKET2` - Copy a file between buckets
• `download file FILE from BUCKET` - Generate a download URL

**📂 Folder Operations:**
• `create folder FOLDER in BUCKET` - Create a new folder
• `delete folder FOLDER from BUCKET` - Delete a folder and its contents

**🔍 Search:**
• `search for PATTERN in BUCKET` - Find files matching a pattern

**🔧 System Commands:**
• `help` - Show this help message
• `test` - Test connectivity to AWS services

**💡 Examples:**
• "list my buckets"
• "list files in my-data-bucket"
• "create bucket new-bucket-name"
• "copy file data.txt from source-bucket to target-bucket"

You can also type partial commands like "delete file" to get syntax help.
"""

def create_response(message):
    """Create API Gateway response"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps({
            'response': message,
            'session_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat()
        })
    }
'''
        
        # Write the Lambda function to a file
        zip_file.writestr('lambda_function.py', lambda_code)
    
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
        print("You can now use the extended S3 agent with additional functions.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    deploy_extended_s3_agent()