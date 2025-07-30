import json
import boto3
import uuid
from datetime import datetime

# AWS clients
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
ec2 = boto3.client('ec2')

def lambda_handler(event, context):
    """Lambda handler that uses Claude to parse user input and execute AWS commands"""
    
    try:
        # Parse request
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        user_message = body.get('message', '')
        session_id = body.get('session_id', str(uuid.uuid4()))
        
        print(f"Processing request: {user_message} (session: {session_id})")
        
        # Handle debug command
        if user_message.lower() == 'debug':
            return create_response(test_connectivity())
        
        # Handle help command
        if user_message.lower() == 'help':
            return create_response(get_help_message())
        
        # Use Claude to parse the user's request
        parsed_intent = parse_with_claude(user_message)
        
        # Check if Claude needs more information
        if parsed_intent.get('needs_followup'):
            return create_response(parsed_intent.get('question', 'I need more information to process your request.'))
        
        # Execute the command based on Claude's parsing
        result = execute_command(parsed_intent)
        
        return create_response(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(f"Sorry, an error occurred: {str(e)}")

def parse_with_claude(user_message):
    """Use Claude to parse user input into structured commands"""
    try:
        prompt = f"""Parse this AWS request into a structured command:
"{user_message}"

Return JSON with these fields:
{{
  "service": "s3|ec2|lambda|iam|cloudwatch",
  "action": "list|create|delete|copy|move|start|stop",
  "parameters": {{}},
  "needs_followup": false
}}

For S3 commands:
- "list buckets" → {{"service": "s3", "action": "list_buckets"}}
- "list files in BUCKET" → {{"service": "s3", "action": "list_objects", "parameters": {{"bucket": "BUCKET"}}}}
- "create bucket NAME" → {{"service": "s3", "action": "create_bucket", "parameters": {{"bucket": "NAME"}}}}
- "copy FILE from BUCKET1 to BUCKET2" → {{"service": "s3", "action": "copy_object", "parameters": {{"source_bucket": "BUCKET1", "dest_bucket": "BUCKET2", "object_key": "FILE"}}}}

For EC2 commands:
- "list instances" → {{"service": "ec2", "action": "list_instances"}}
- "start instance ID" → {{"service": "ec2", "action": "start_instance", "parameters": {{"instance_id": "ID"}}}}
- "stop instance ID" → {{"service": "ec2", "action": "stop_instance", "parameters": {{"instance_id": "ID"}}}}

If information is missing, set needs_followup to true and include a question field.
Example: {{"service": "s3", "action": "list_objects", "needs_followup": true, "question": "Which bucket would you like to list objects from?"}}

Parse this request: "{user_message}"
"""

        # Claude invocation
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 1000,
                'temperature': 0,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ]
            })
        )
        
        result = json.loads(response['body'].read())
        content = result['content'][0]['text']
        
        # Extract JSON from response
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            parsed = json.loads(content[start:end])
            print(f"Claude parsed: {parsed}")
            return parsed
        
        return {
            'service': 'unknown',
            'action': 'unknown',
            'needs_followup': True,
            'question': 'I couldn\'t understand your request. Could you please rephrase it?'
        }
        
    except Exception as e:
        print(f"Claude parsing error: {str(e)}")
        return {
            'service': 'unknown',
            'action': 'unknown',
            'needs_followup': True,
            'question': f'Error parsing your request: {str(e)}'
        }

def execute_command(parsed_intent):
    """Execute AWS commands based on the parsed intent"""
    service = parsed_intent.get('service', '').lower()
    action = parsed_intent.get('action', '').lower()
    parameters = parsed_intent.get('parameters', {})
    
    print(f"Executing: {service}.{action} with parameters: {parameters}")
    
    try:
        # S3 commands
        if service == 's3':
            return execute_s3_command(action, parameters)
        
        # EC2 commands
        elif service == 'ec2':
            return execute_ec2_command(action, parameters)
        
        # Other services can be added here
        
        return f"Service '{service}' or action '{action}' not supported yet."
        
    except Exception as e:
        print(f"Command execution error: {str(e)}")
        return f"Error executing command: {str(e)}"

def execute_s3_command(action, parameters):
    """Execute S3 commands"""
    try:
        # List buckets
        if action == 'list_buckets':
            response = s3.list_buckets()
            buckets = [b['Name'] for b in response.get('Buckets', [])]
            if not buckets:
                return "You don't have any S3 buckets."
            return f"📦 S3 Buckets ({len(buckets)}):\n" + "\n".join(buckets)
        
        # List objects in bucket
        elif action == 'list_objects':
            bucket = parameters.get('bucket')
            if not bucket:
                return "Please specify a bucket name."
            
            response = s3.list_objects_v2(Bucket=bucket, MaxKeys=50)
            objects = [obj['Key'] for obj in response.get('Contents', [])]
            
            if not objects:
                return f"Bucket '{bucket}' is empty."
            
            return f"📁 Objects in '{bucket}' ({len(objects)}):\n" + "\n".join(objects)
        
        # Create bucket
        elif action == 'create_bucket':
            bucket = parameters.get('bucket')
            if not bucket:
                return "Please specify a bucket name."
            
            s3.create_bucket(Bucket=bucket)
            return f"✅ Bucket '{bucket}' created successfully."
        
        # Copy object
        elif action == 'copy_object':
            source_bucket = parameters.get('source_bucket')
            dest_bucket = parameters.get('dest_bucket')
            object_key = parameters.get('object_key')
            
            if not source_bucket or not dest_bucket or not object_key:
                return "Please specify source bucket, destination bucket, and object key."
            
            s3.copy_object(
                CopySource={'Bucket': source_bucket, 'Key': object_key},
                Bucket=dest_bucket,
                Key=object_key
            )
            
            return f"✅ Copied '{object_key}' from '{source_bucket}' to '{dest_bucket}'."
        
        # Delete object
        elif action == 'delete_object':
            bucket = parameters.get('bucket')
            object_key = parameters.get('object_key')
            
            if not bucket or not object_key:
                return "Please specify bucket and object key."
            
            s3.delete_object(Bucket=bucket, Key=object_key)
            return f"✅ Deleted '{object_key}' from '{bucket}'."
        
        return f"S3 action '{action}' not supported yet."
        
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def execute_ec2_command(action, parameters):
    """Execute EC2 commands"""
    try:
        # List instances
        if action == 'list_instances':
            response = ec2.describe_instances()
            instances = []
            
            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    instance_id = instance.get('InstanceId', 'Unknown')
                    state = instance.get('State', {}).get('Name', 'unknown')
                    instance_type = instance.get('InstanceType', 'Unknown')
                    
                    # Get name tag if available
                    name = 'Unnamed'
                    for tag in instance.get('Tags', []):
                        if tag.get('Key') == 'Name':
                            name = tag.get('Value')
                            break
                    
                    instances.append(f"{instance_id} ({name}) - {state} - {instance_type}")
            
            if not instances:
                return "You don't have any EC2 instances."
            
            return f"🖥️ EC2 Instances ({len(instances)}):\n" + "\n".join(instances)
        
        # Start instance
        elif action == 'start_instance':
            instance_id = parameters.get('instance_id')
            if not instance_id:
                return "Please specify an instance ID."
            
            ec2.start_instances(InstanceIds=[instance_id])
            return f"✅ Started instance '{instance_id}'."
        
        # Stop instance
        elif action == 'stop_instance':
            instance_id = parameters.get('instance_id')
            if not instance_id:
                return "Please specify an instance ID."
            
            ec2.stop_instances(InstanceIds=[instance_id])
            return f"✅ Stopped instance '{instance_id}'."
        
        return f"EC2 action '{action}' not supported yet."
        
    except Exception as e:
        return f"❌ EC2 Error: {str(e)}"

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
        # Test EC2
        ec2.describe_instances(MaxResults=5)
        results.append("✅ EC2: Connected")
    except Exception as e:
        results.append(f"❌ EC2: {str(e)}")
    
    try:
        # Test Bedrock with Claude
        bedrock.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 10,
                'temperature': 0,
                'messages': [
                    {'role': 'user', 'content': 'Hello'}
                ]
            })
        )
        results.append("✅ Bedrock Claude: Connected")
    except Exception as e:
        results.append(f"❌ Bedrock Claude: {str(e)}")
    
    return "\n".join(results)

def get_help_message():
    """Return help message with available commands"""
    return """🤖 **Available Commands:**

**📦 S3 Operations:**
• `list buckets` - Show all S3 buckets
• `list files in BUCKET` - Show objects in bucket
• `create bucket NAME` - Create new bucket
• `copy FILE from BUCKET1 to BUCKET2` - Copy between buckets
• `delete FILE from BUCKET` - Delete object

**🖥️ EC2 Operations:**
• `list instances` - Show all EC2 instances
• `start instance ID` - Start an EC2 instance
• `stop instance ID` - Stop an EC2 instance

**💡 Examples:**
• "list my buckets"
• "list files in my-data-bucket"
• "copy report.pdf from staging to production"
• "list all my EC2 instances"

Just ask naturally - I'll understand! 🚀"""

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
            'session_state': 'IDLE',
            'timestamp': datetime.now().isoformat()
        })
    }