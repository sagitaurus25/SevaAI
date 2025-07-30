import boto3
import zipfile
import io

def deploy_minimal_fix():
    """Deploy a minimal fix for the list files command"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Deploying minimal fix for Lambda function: {FUNCTION_NAME}")
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the Lambda function code
        lambda_code = """
import json
import boto3
import uuid
from datetime import datetime

# Initialize AWS clients
bedrock = boto3.client('bedrock-runtime')
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
        if user_message.lower() in ['list buckets', 'show buckets', 'list my buckets']:
            result = list_buckets()
            return create_response(result)
        
        # Special handling for list files
        if user_message.lower() == 'list files':
            return create_response("Which bucket would you like to list files from?")
        
        # Handle bucket name response after list files
        if len(user_message.split()) == 1:  # Single word response, likely a bucket name
            result = list_objects(user_message)
            return create_response(result)
        
        # Handle list files in bucket
        if 'list files in' in user_message.lower():
            parts = user_message.lower().split('list files in')
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

def test_connectivity():
    """Test connectivity to AWS services"""
    results = []
    
    try:
        # Test S3
        s3.list_buckets()
        results.append("✅ S3: Connected")
    except Exception as e:
        results.append(f"❌ S3: {str(e)}")
    
    try:
        # Test Bedrock
        bedrock.invoke_model(
            modelId='amazon.nova-micro-v1:0',
            body=json.dumps({
                'messages': [{'role': 'user', 'content': 'Hello'}]
            })
        )
        results.append("✅ Bedrock: Connected")
    except Exception as e:
        results.append(f"❌ Bedrock: {str(e)}")
    
    return "\\n".join(results)

def get_help_message():
    """Return help message with available commands"""
    return \"\"\"🤖 **Available Commands:**

**📦 S3 Operations:**
• `list buckets` - Show all S3 buckets
• `list files` - Show objects in a bucket (you'll be asked which bucket)
• `list files in BUCKET` - Show objects in specific bucket

**🔧 System Commands:**
• `help` - Show this help message
• `test` - Test connectivity to AWS services

**💡 Examples:**
• "list my buckets"
• "list files in my-data-bucket"

Just ask naturally - I'll understand! 🚀\"\"\"

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
"""
        
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
        print("You can now use the S3 agent interface to interact with your S3 buckets.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    deploy_minimal_fix()