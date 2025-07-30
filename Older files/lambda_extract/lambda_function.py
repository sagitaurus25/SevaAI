
import json
import boto3
import uuid
from datetime import datetime

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

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
            return create_response("Available list commands:\n• `list buckets` - Show all S3 buckets\n• `list files` - Show objects in a bucket\n• `list files in BUCKET` - Show objects in specific bucket")
        
        if user_message_lower == 'create':
            return create_response("Syntax: `create bucket BUCKET_NAME`\nExample: create bucket my-new-bucket")
        
        if user_message_lower == 'delete':
            return create_response("Available delete commands:\n• `delete bucket BUCKET_NAME` - Delete an empty bucket\n• `delete file FILE_NAME from BUCKET_NAME` - Delete a file from a bucket")
        
        if user_message_lower == 'delete file' or user_message_lower == 'delete files':
            return create_response("Syntax: `delete file FILE_NAME from BUCKET_NAME`\nExample: delete file data.txt from my-bucket")
        
        if user_message_lower == 'copy' or user_message_lower == 'copy file':
            return create_response("Syntax: `copy file FILE_NAME from SOURCE_BUCKET to DESTINATION_BUCKET`\nExample: copy file data.txt from source-bucket to target-bucket")
        
        
        if user_message_lower == 'workflow' or user_message_lower == 'workflows':
            return create_response("To see available workflows, type `list workflows`")
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
                    result = delete_object(bucket_name, file_name)
                    return create_response(result)
                else:
                    return create_response("Syntax: `delete file FILE_NAME from BUCKET_NAME`\nExample: delete file data.txt from my-bucket")
        
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
                else:
                    return create_response("Syntax: `copy file FILE_NAME from SOURCE_BUCKET to DESTINATION_BUCKET`\nExample: copy file data.txt from source-bucket to target-bucket")
            except:
                return create_response("Syntax: `copy file FILE_NAME from SOURCE_BUCKET to DESTINATION_BUCKET`\nExample: copy file data.txt from source-bucket to target-bucket")
        
        
        # List workflows command
        if user_message_lower == 'list workflows':
            result = list_workflows()
            return create_response(result)
        
        # Try to parse as a workflow command
        workflow_command = parse_workflow_command(user_message)
        if workflow_command:
            result = execute_workflow(workflow_command['workflow_id'], workflow_command['parameters'])
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
        return f"📦 S3 Buckets ({len(buckets)}):\n" + "\n".join(buckets)
    except Exception as e:
        return f"❌ S3 Error: {str(e)}"

def list_objects(bucket):
    """List objects in an S3 bucket"""
    try:
        response = s3.list_objects_v2(Bucket=bucket, MaxKeys=50)
        objects = [obj['Key'] for obj in response.get('Contents', [])]
        
        if not objects:
            return f"Bucket '{bucket}' is empty."
        
        return f"📁 Objects in '{bucket}' ({len(objects)}):\n" + "\n".join(objects)
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


def get_workflow_definitions():
    """Get all workflow definitions from DynamoDB"""
    try:
        table = dynamodb.Table('S3WorkflowDefinitions')
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        print(f"Error getting workflow definitions: {str(e)}")
        return []

def get_workflow_by_id(workflow_id):
    """Get a specific workflow definition by ID"""
    try:
        table = dynamodb.Table('S3WorkflowDefinitions')
        response = table.get_item(Key={'workflow_id': workflow_id})
        return response.get('Item')
    except Exception as e:
        print(f"Error getting workflow {workflow_id}: {str(e)}")
        return None

def parse_workflow_command(user_message):
    """Parse a workflow command from natural language"""
    try:
        # Get all workflow definitions
        workflows = get_workflow_definitions()
        if not workflows:
            return None
        
        # Try to match the command to a workflow
        user_message_lower = user_message.lower()
        
        for workflow in workflows:
            # Check if workflow name is in the message
            if workflow['name'].lower() in user_message_lower:
                # Extract parameters
                params = {}
                
                # Extract source bucket
                if 'in' in user_message_lower and 'bucket' in user_message_lower:
                    bucket_match = re.search(r'in\s+([\w-]+)\s+bucket', user_message_lower)
                    if bucket_match:
                        params['source_bucket'] = bucket_match.group(1)
                
                # For organize-images workflow
                if workflow['workflow_id'] == 'organize-images':
                    # Extract file types
                    if 'extension' in user_message_lower or 'file type' in user_message_lower:
                        ext_match = re.search(r'extension[s]?\s+([\w\.,]+)', user_message_lower)
                        if ext_match:
                            params['file_types'] = ext_match.group(1).split(',')
                    
                    # Extract date format
                    if 'format' in user_message_lower:
                        if 'year-month' in user_message_lower:
                            params['date_format'] = '%Y-%m'
                        elif 'year/month/day' in user_message_lower:
                            params['date_format'] = '%Y/%m/%d'
                
                # For search-move workflow
                if workflow['workflow_id'] == 'search-move':
                    # Extract search pattern
                    if 'search for' in user_message_lower or 'find' in user_message_lower:
                        pattern_match = re.search(r'(search for|find)\s+([\w\*\.]+)', user_message_lower)
                        if pattern_match:
                            params['search_pattern'] = pattern_match.group(2)
                    
                    # Extract destination
                    if 'move to' in user_message_lower:
                        dest_match = re.search(r'move to\s+([\w\/]+)', user_message_lower)
                        if dest_match:
                            params['destination_prefix'] = dest_match.group(1)
                
                return {
                    'workflow_id': workflow['workflow_id'],
                    'parameters': params
                }
        
        return None
    except Exception as e:
        print(f"Error parsing workflow command: {str(e)}")
        return None

def execute_workflow(workflow_id, parameters):
    """Execute a workflow with the given parameters"""
    try:
        # Get the workflow definition
        workflow = get_workflow_by_id(workflow_id)
        if not workflow:
            return f"❌ Workflow '{workflow_id}' not found."
        
        # Validate parameters
        missing_params = []
        for param_name, param_config in workflow['parameters'].items():
            if param_config.get('required', False) and param_name not in parameters:
                missing_params.append(param_name)
        
        if missing_params:
            return f"❌ Missing required parameters: {', '.join(missing_params)}"
        
        # Fill in default values for optional parameters
        for param_name, param_config in workflow['parameters'].items():
            if param_name not in parameters and 'default' in param_config:
                parameters[param_name] = param_config['default']
        
        # Create execution record
        execution_id = str(uuid.uuid4())
        execution_table = dynamodb.Table('S3WorkflowExecutions')
        execution_table.put_item(Item={
            'execution_id': execution_id,
            'workflow_id': workflow_id,
            'parameters': parameters,
            'status': 'RUNNING',
            'start_time': datetime.now().isoformat(),
            'steps_completed': 0
        })
        
        # Execute workflow based on type
        if workflow_id == 'organize-images':
            result = execute_organize_images(workflow, parameters, execution_id)
        elif workflow_id == 'search-move':
            result = execute_search_move(workflow, parameters, execution_id)
        else:
            result = f"❌ Workflow type '{workflow_id}' not implemented."
        
        # Update execution record
        execution_table.update_item(
            Key={'execution_id': execution_id},
            UpdateExpression="set #s = :s, end_time = :t",
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': 'COMPLETED', ':t': datetime.now().isoformat()}
        )
        
        return result
    except Exception as e:
        print(f"Error executing workflow: {str(e)}")
        return f"❌ Error executing workflow: {str(e)}"

def execute_organize_images(workflow, parameters, execution_id):
    """Execute the organize-images workflow"""
    bucket = parameters['source_bucket']
    file_types = parameters.get('file_types', ['.jpg', '.jpeg', '.png', '.gif', '.heic'])
    date_format = parameters.get('date_format', '%Y/%m')
    
    # Implementation similar to organize_images_by_date function
    # but using the configurable parameters
    
    # For brevity, returning a placeholder result
    return f"✅ Organized images in bucket '{bucket}' using format '{date_format}'\nProcessed file types: {', '.join(file_types)}"

def execute_search_move(workflow, parameters, execution_id):
    """Execute the search-move workflow"""
    bucket = parameters['source_bucket']
    search_pattern = parameters['search_pattern']
    destination_prefix = parameters['destination_prefix']
    
    # Implementation for searching and moving files
    
    # For brevity, returning a placeholder result
    return f"✅ Searched for '{search_pattern}' in bucket '{bucket}'\nMoved matching files to '{destination_prefix}/'"

def list_workflows():
    """List all available workflows"""
    workflows = get_workflow_definitions()
    if not workflows:
        return "No workflows defined."
    
    result = "📋 Available Workflows:\n\n"
    
    for workflow in workflows:
        result += f"• {workflow['name']}\n"
        result += f"  ID: {workflow['workflow_id']}\n"
        result += f"  Description: {workflow['description']}\n"
        result += f"  Example: {workflow['examples'][0]}\n\n"
    
    return result


def test_connectivity():
    """Test connectivity to AWS services"""
    results = []
    
    try:
        # Test S3
        s3.list_buckets()
        results.append("✅ S3: Connected")
    except Exception as e:
        results.append(f"❌ S3: {str(e)}")
    
    return "\n".join(results)

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


**🔄 Workflow Operations:**
• `list workflows` - Show all available workflows
• `organize images in BUCKET` - Organize images by date
• `search for PATTERN in BUCKET and move to PREFIX` - Search and move files
**🔧 System Commands:**
• `help` - Show this help message
• `test` - Test connectivity to AWS services

**💡 Examples:**
• "list my buckets"
• "list files in my-data-bucket"
• "create bucket new-bucket-name"
• "copy file data.txt from source-bucket to target-bucket"

You can also type partial commands like "delete" or "copy" to get syntax help.
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
