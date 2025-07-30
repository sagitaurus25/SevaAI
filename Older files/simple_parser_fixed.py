import json
import boto3
import uuid
import re
from datetime import datetime

# AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
ec2 = boto3.client('ec2')

def lambda_handler(event, context):
    """Lambda handler that uses simple regex parsing for AWS commands"""
    
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
        
        # Use simple regex parsing for the user's request
        parsed_intent = parse_command(user_message)
        
        # Check if we need more information
        if parsed_intent.get('needs_followup'):
            return create_response(parsed_intent.get('question', 'I need more information to process your request.'))
        
        # Execute the command based on the parsing
        result = execute_command(parsed_intent)
        
        return create_response(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(f"Sorry, an error occurred: {str(e)}")

def parse_command(user_message):
    """Parse user input using regex patterns"""
    message = user_message.lower().strip()
    
    # List buckets
    if re.search(r'(list|show|get).*buckets?', message):
        return {
            'service': 's3',
            'action': 'list_buckets'
        }
    
    # List objects in bucket
    bucket_match = re.search(r'(list|show|get).*(files?|objects?).*in\s+(\S+)', message)
    if bucket_match:
        bucket_name = bucket_match.group(3).strip()
        return {
            'service': 's3',
            'action': 'list_objects',
            'parameters': {'bucket': bucket_name}
        }
    
    # Create bucket - fixed pattern to match just "create bucket NAME"
    create_match = re.search(r'create\s+bucket\s+(\S+)', message)
    if create_match or message.startswith('create bucket'):
        # If just "create bucket" without name, ask for name
        if message == 'create bucket':
            return {
                'service': 's3',
                'action': 'create_bucket',
                'needs_followup': True,
                'question': 'What name would you like to give to the new bucket?'
            }
        
        # If we have a match, extract the bucket name
        if create_match:
            bucket_name = create_match.group(1).strip()
            return {
                'service': 's3',
                'action': 'create_bucket',
                'parameters': {'bucket': bucket_name}
            }
    
    # Copy object
    copy_match = re.search(r'copy\s+(\S+)\s+from\s+(\S+)\s+to\s+(\S+)', message)
    if copy_match:
        object_key = copy_match.group(1).strip()
        source_bucket = copy_match.group(2).strip()
        dest_bucket = copy_match.group(3).strip()
        return {
            'service': 's3',
            'action': 'copy_object',
            'parameters': {
                'object_key': object_key,
                'source_bucket': source_bucket,
                'dest_bucket': dest_bucket
            }
        }
    
    # Delete object
    delete_match = re.search(r'delete\s+(\S+)\s+from\s+(\S+)', message)
    if delete_match:
        object_key = delete_match.group(1).strip()
        bucket_name = delete_match.group(2).strip()
        return {
            'service': 's3',
            'action': 'delete_object',
            'parameters': {
                'object_key': object_key,
                'bucket': bucket_name
            }
        }
    
    # List EC2 instances
    if re.search(r'(list|show|get).*instances?', message):
        return {
            'service': 'ec2',
            'action': 'list_instances'
        }
    
    # Start EC2 instance
    start_match = re.search(r'start\s+instance\s+(\S+)', message)
    if start_match:
        instance_id = start_match.group(1).strip()
        return {
            'service': 'ec2',
            'action': 'start_instance',
            'parameters': {'instance_id': instance_id}
        }
    
    # Stop EC2 instance
    stop_match = re.search(r'stop\s+instance\s+(\S+)', message)
    if stop_match:
        instance_id = stop_match.group(1).strip()
        return {
            'service': 'ec2',
            'action': 'stop_instance',
            'parameters': {'instance_id': instance_id}
        }
    
    # If no pattern matches, ask for clarification
    return {
        'service': 'unknown',
        'action': 'unknown',
        'needs_followup': True,
        'question': "I'm not sure what you want to do. Try commands like 'list buckets', 'list files in my-bucket', or 'list instances'."
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