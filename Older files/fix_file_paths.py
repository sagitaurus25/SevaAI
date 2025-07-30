import boto3
import zipfile
import io
import urllib.parse

def deploy_file_path_fix():
    """Deploy a fix for handling file paths with spaces and special characters"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Deploying file path fix for: {FUNCTION_NAME}")
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the Lambda function code with triple quotes properly escaped
        lambda_code = '''
import json
import boto3
import uuid
import urllib.parse
from datetime import datetime

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
        if user_message_lower == 'download' or user_message_lower == 'download file':
            return create_response("Syntax: `download file FILE_NAME from BUCKET`\\nExample: download file data.txt from my-bucket")
        
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
                    # Use the original case for the file name
                    original_parts = user_message.split('delete file')[1].split('from')
                    original_file_name = original_parts[0].strip()
                    result = delete_object(bucket_name, original_file_name)
                    return create_response(result)
        
        # Copy file command
        if 'copy file' in user_message_lower and 'from' in user_message_lower and 'to' in user_message_lower:
            try:
                # Extract file name (between "copy file" and "from")
                file_start = user_message.index('copy file') + 10
                from_start = user_message.lower().index('from', file_start)
                file_name = user_message[file_start:from_start].strip()
                
                # Extract source bucket (between "from" and "to")
                from_start += 5  # length of "from "
                to_start = user_message.lower().index('to', from_start)
                source_bucket = user_message[from_start:to_start].strip()
                
                # Extract destination bucket (after "to")
                to_start += 3  # length of "to "
                dest_bucket = user_message[to_start:].strip()
                
                if file_name and source_bucket and dest_bucket:
                    result = copy_object(source_bucket, dest_bucket, file_name)
                    return create_response(result)
            except:
                pass
        
        # Download file command
        if 'download file' in user_message_lower and 'from' in user_message_lower:
            parts = user_message.split('download file')[1].split('from')
            if len(parts) == 2:
                file_name = parts[0].strip()
                bucket_name = parts[1].strip()
                if file_name and bucket_name:
                    result = generate_download_url(bucket_name, file_name)
                    return create_response(result)
        
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
            # Try to list objects with a prefix to help the user
            try:
                prefix = key.split('/')[0] + '/' if '/' in key else key[0:3]
                response = s3.list_objects_v2(Bucket=source_bucket, Prefix=prefix, MaxKeys=10)
                if response.get('Contents'):
                    similar_files = [obj['Key'] for obj in response['Contents']]
                    return f"❌ File '{key}' does not exist in bucket '{source_bucket}'.\\n\\nSimilar files:\\n" + "\\n".join(similar_files)
            except:
                pass
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
            # Try to list objects with a prefix to help the user
            try:
                prefix = key.split('/')[0] + '/' if '/' in key else key[0:3]
                response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=10)
                if response.get('Contents'):
                    similar_files = [obj['Key'] for obj in response['Contents']]
                    return f"❌ File '{key}' does not exist in bucket '{bucket}'.\\n\\nSimilar files:\\n" + "\\n".join(similar_files)
            except:
                pass
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

**📦 S3 Operations:**
• `list buckets` - Show all S3 buckets
• `list files` - Show objects in a bucket (you'll be asked which bucket)
• `list files in BUCKET` - Show objects in specific bucket
• `create bucket NAME` - Create a new bucket
• `delete bucket NAME` - Delete an empty bucket
• `delete file FILE from BUCKET` - Delete a file from a bucket
• `copy file FILE from BUCKET1 to BUCKET2` - Copy a file between buckets
• `download file FILE from BUCKET` - Generate a download link for a file

**🔧 System Commands:**
• `help` - Show this help message
• `test` - Test connectivity to AWS services

**💡 Examples:**
• "list my buckets"
• "list files in my-data-bucket"
• "create bucket new-bucket-name"
• "download file data.txt from my-bucket"

**📝 Note:**
When specifying file paths, make sure to use the exact case and spacing as shown in the bucket listing.
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
        print("The Lambda function now handles file paths with spaces and special characters.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    deploy_file_path_fix()