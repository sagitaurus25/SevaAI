import boto3
import zipfile
import io
import os
import time

def deploy_fixed_function():
    """Deploy a fixed version of the Lambda function"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Deploying fixed Lambda function: {FUNCTION_NAME}")
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the Lambda function code
        lambda_code = """
import json
import boto3
import uuid
import re
from datetime import datetime

# Initialize AWS clients
bedrock = boto3.client('bedrock-runtime')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    \"\"\"Main Lambda handler function\"\"\"
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
        
        if 'list files in' in user_message.lower():
            parts = user_message.lower().split('list files in')
            if len(parts) > 1:
                bucket = parts[1].strip()
                result = list_objects(bucket)
                return create_response(result)
        
        # Parse with Nova for other commands
        parsed_intent = parse_with_nova(user_message)
        
        # If Nova identified a need for followup, return the question
        if parsed_intent.get('needs_followup', False):
            return create_response(parsed_intent.get('question', 'Could you provide more details?'))
        
        # Execute the command
        result = execute_command(parsed_intent)
        return create_response(result)
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return create_response(f"Sorry, I encountered an error: {str(e)}")

def parse_with_nova(user_message):
    \"\"\"Parse user message using Nova Micro model with improved error handling\"\"\"
    try:
        # Create prompt for Nova Micro
        prompt = \"\"\"You are an AI assistant that parses user requests about AWS S3 operations.
Extract the intent and parameters from the user's message.
Return a JSON object with the following structure:
{
  "service": "s3",
  "action": "action_name",
  "parameters": {"param1": "value1", "param2": "value2"},
  "needs_followup": true/false,
  "question": "Follow-up question if more information is needed"
}

Examples:
User: "List my S3 buckets"
{"service": "s3", "action": "list_buckets", "parameters": {}, "needs_followup": false}

User: "List files"
{"service": "s3", "action": "list_objects", "needs_followup": true, "question": "Which bucket would you like to list objects from?"}

User: "List files in bucket1"
{"service": "s3", "action": "list_objects", "parameters": {"bucket": "bucket1"}, "needs_followup": false}

User: "bucket1"
{"service": "s3", "action": "list_objects", "parameters": {"bucket": "bucket1"}, "needs_followup": false}

Parse this request: "{0}"
\"\"\"

        # Correctly formatted Nova Micro invocation
        response = bedrock.invoke_model(
            modelId='amazon.nova-micro-v1:0',
            body=json.dumps({
                'messages': [{'role': 'user', 'content': prompt.format(user_message)}]
            })
        )
        
        result = json.loads(response['body'].read())
        content = result['output']['message']['content'][0]['text']
        
        print(f"Raw Nova response: {content}")
        
        # Improved JSON extraction with regex
        json_match = re.search(r'\\{.*\\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            # Clean up any potential issues
            json_str = json_str.replace('\\n', ' ').replace('\\r', '')
            try:
                parsed = json.loads(json_str)
                print(f"Successfully parsed: {parsed}")
                return parsed
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {str(e)}")
                # Try to fix common JSON issues
                json_str = re.sub(r'([{,])\\s*([a-zA-Z0-9_]+):', r'\\1"\\2":', json_str)
                json_str = re.sub(r':\\s*([a-zA-Z0-9_]+)([,}])', r':\"\\1\"\\2', json_str)
                try:
                    parsed = json.loads(json_str)
                    print(f"Fixed and parsed: {parsed}")
                    return parsed
                except:
                    pass
        
        # Direct parsing for bucket name
        if user_message.strip().lower() == user_message.strip():  # If message is just a word
            return {
                'service': 's3',
                'action': 'list_objects',
                'parameters': {'bucket': user_message.strip()},
                'needs_followup': False
            }
        
        return {
            'service': 'unknown',
            'action': 'unknown',
            'needs_followup': True,
            'question': 'I couldn\\'t understand your request. Could you please rephrase it?'
        }
        
    except Exception as e:
        print(f"Nova parsing error: {str(e)}")
        return {
            'service': 'unknown',
            'action': 'unknown',
            'needs_followup': True,
            'question': f'Error parsing your request: {str(e)}'
        }

def execute_command(parsed_intent):
    \"\"\"Execute AWS commands based on the parsed intent\"\"\"
    service = parsed_intent.get('service', '').lower()
    action = parsed_intent.get('action', '').lower()
    parameters = parsed_intent.get('parameters', {})
    
    print(f"Executing: {service}.{action} with parameters: {parameters}")
    
    try:
        # S3 commands
        if service == 's3':
            if action == 'list_buckets':
                return list_buckets()
            elif action == 'list_objects':
                bucket = parameters.get('bucket')
                if not bucket:
                    return "Please specify a bucket name."
                return list_objects(bucket)
            elif action == 'create_bucket':
                bucket = parameters.get('bucket')
                if not bucket:
                    return "Please specify a bucket name."
                return create_bucket(bucket)
        
        return f"Service '{service}' or action '{action}' not supported yet."
        
    except Exception as e:
        print(f"Command execution error: {str(e)}")
        return f"Error executing command: {str(e)}"

def list_buckets():
    \"\"\"List S3 buckets\"\"\"
    try:
        response = s3.list_buckets()
        buckets = [b['Name'] for b in response.get('Buckets', [])]
        if not buckets:
            return "You don't have any S3 buckets."
        return f"📦 S3 Buckets ({len(buckets)}):\\n" + "\\n".join(buckets)
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def list_objects(bucket):
    \"\"\"List objects in an S3 bucket\"\"\"
    try:
        response = s3.list_objects_v2(Bucket=bucket, MaxKeys=50)
        objects = [obj['Key'] for obj in response.get('Contents', [])]
        
        if not objects:
            return f"Bucket '{bucket}' is empty."
        
        return f"📁 Objects in '{bucket}' ({len(objects)}):\\n" + "\\n".join(objects)
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def create_bucket(bucket):
    \"\"\"Create an S3 bucket\"\"\"
    try:
        s3.create_bucket(Bucket=bucket)
        return f"✅ Bucket '{bucket}' created successfully."
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def test_connectivity():
    \"\"\"Test connectivity to AWS services\"\"\"
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
    \"\"\"Return help message with available commands\"\"\"
    return \"\"\"🤖 **Available Commands:**

**📦 S3 Operations:**
• `list buckets` - Show all S3 buckets
• `list files in BUCKET` - Show objects in bucket
• `create bucket NAME` - Create new bucket

**🔧 System Commands:**
• `help` - Show this help message
• `test` - Test connectivity to AWS services

**💡 Examples:**
• "list my buckets"
• "list files in my-data-bucket"
• "create bucket new-bucket-name"

Just ask naturally - I'll understand! 🚀\"\"\"

def create_response(message):
    \"\"\"Create API Gateway response\"\"\"
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
        
        # Wait for the function to be active
        print("Waiting for function to be active...")
        time.sleep(5)
        
        print("\n✅ Deployment complete!")
        print("You can now use the S3 agent interface to interact with your S3 buckets.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    deploy_fixed_function()