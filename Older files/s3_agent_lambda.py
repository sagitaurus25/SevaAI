import json
import boto3
import uuid
from datetime import datetime
import os

# Initialize AWS clients
bedrock = boto3.client('bedrock-runtime')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Constants
KNOWLEDGE_BASE_TABLE = 'S3CommandKnowledgeBase'

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
        
        # Check knowledge base first before calling the model
        kb_result = check_knowledge_base(user_message, session_id)
        
        # If we got a complete match from the knowledge base, use it
        if kb_result and not kb_result.get('needs_followup', False):
            result = execute_command(kb_result)
            return create_response(result)
        
        # If we need followup, return the question
        if kb_result and kb_result.get('needs_followup', False):
            return create_response(kb_result.get('followup_question', 'Could you provide more details?'))
        
        # If not in knowledge base, use Nova to parse the intent
        parsed_intent = parse_with_nova(user_message)
        
        # If Nova identified a need for followup, return the question
        if parsed_intent.get('needs_followup', False):
            # Add this to our knowledge base for future reference
            store_in_knowledge_base(user_message, parsed_intent)
            return create_response(parsed_intent.get('question', 'Could you provide more details?'))
        
        # Execute the command
        result = execute_command(parsed_intent)
        
        # Store successful command in knowledge base
        if "Error" not in result:
            store_in_knowledge_base(user_message, parsed_intent)
        
        return create_response(result)
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return create_response(f"Sorry, I encountered an error: {str(e)}")

def check_knowledge_base(user_message, session_id):
    """Check if the user message matches patterns in our knowledge base"""
    try:
        table = dynamodb.Table(KNOWLEDGE_BASE_TABLE)
        
        # Scan the table for patterns that might match
        # In a production system, you'd want to use a more efficient approach
        # like embedding-based similarity search
        response = table.scan()
        
        best_match = None
        best_match_score = 0
        
        # Simple pattern matching - in production you'd use embeddings or better NLP
        user_message_lower = user_message.lower()
        
        for item in response.get('Items', []):
            # Check exact intent match
            if item['intent_pattern'] in user_message_lower:
                return item
            
            # Check example phrases
            for phrase in item.get('example_phrases', []):
                if phrase in user_message_lower:
                    return item
            
            # Simple word overlap scoring
            pattern_words = set(item['intent_pattern'].lower().split())
            message_words = set(user_message_lower.split())
            common_words = pattern_words.intersection(message_words)
            
            if len(common_words) > 0:
                score = len(common_words) / len(pattern_words)
                if score > best_match_score and score > 0.5:  # Threshold
                    best_match_score = score
                    best_match = item
        
        return best_match
        
    except Exception as e:
        print(f"Knowledge base error: {str(e)}")
        return None

def store_in_knowledge_base(user_message, parsed_intent):
    """Store new patterns in the knowledge base"""
    try:
        # Only store if we have a valid service and action
        if parsed_intent.get('service') == 'unknown' or parsed_intent.get('action') == 'unknown':
            return
        
        # Simplify the user message to create a pattern
        # In production, you'd use more sophisticated NLP techniques
        words = user_message.lower().split()
        # Filter out common words, keep key command words
        key_words = [w for w in words if len(w) > 3 and w not in ['please', 'could', 'would', 'from', 'with']]
        
        if not key_words:
            return
            
        # Create a simple pattern from the first few key words
        pattern = ' '.join(key_words[:3])
        
        table = dynamodb.Table(KNOWLEDGE_BASE_TABLE)
        
        # Check if pattern already exists
        response = table.get_item(Key={'intent_pattern': pattern})
        if 'Item' in response:
            # Pattern exists, no need to add
            return
            
        # Create new knowledge base entry
        item = {
            'intent_pattern': pattern,
            'service': parsed_intent.get('service'),
            'action': parsed_intent.get('action'),
            'required_params': list(parsed_intent.get('parameters', {}).keys()),
            'example_phrases': [user_message.lower()],
            'needs_followup': parsed_intent.get('needs_followup', False),
            'followup_question': parsed_intent.get('question', None),
            'syntax_template': f"{pattern} " + " ".join([f"{{{p}}}" for p in parsed_intent.get('parameters', {})])
        }
        
        # Store in DynamoDB
        table.put_item(Item=item)
        print(f"Added new pattern to knowledge base: {pattern}")
        
    except Exception as e:
        print(f"Error storing in knowledge base: {str(e)}")

def parse_with_nova(user_message):
    """Parse user message using Nova Micro model"""
    try:
        # Create prompt for Nova Micro
        prompt = f"""You are an AI assistant that parses user requests about AWS S3 operations.
Extract the intent and parameters from the user's message.
Return a JSON object with the following structure:
{{
  "service": "s3",
  "action": "action_name",
  "parameters": {{"param1": "value1", "param2": "value2"}},
  "needs_followup": true/false,
  "question": "Follow-up question if more information is needed"
}}

Examples:
User: "List my S3 buckets"
{{"service": "s3", "action": "list_buckets", "parameters": {{}}, "needs_followup": false}}

User: "List files"
{{"service": "s3", "action": "list_objects", "needs_followup": true, "question": "Which bucket would you like to list objects from?"}}

Parse this request: "{user_message}"
"""

        # Correctly formatted Nova Micro invocation
        response = bedrock.invoke_model(
            modelId='amazon.nova-micro-v1:0',
            body=json.dumps({
                'messages': [{'role': 'user', 'content': prompt}]
            })
        )
        
        result = json.loads(response['body'].read())
        content = result['output']['message']['content'][0]['text']
        
        # Extract JSON from response
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            parsed = json.loads(content[start:end])
            print(f"Nova parsed: {parsed}")
            return parsed
        
        return {
            'service': 'unknown',
            'action': 'unknown',
            'needs_followup': True,
            'question': 'I couldn\'t understand your request. Could you please rephrase it?'
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
    """Execute AWS commands based on the parsed intent"""
    service = parsed_intent.get('service', '').lower()
    action = parsed_intent.get('action', '').lower()
    parameters = parsed_intent.get('parameters', {})
    
    print(f"Executing: {service}.{action} with parameters: {parameters}")
    
    try:
        # S3 commands
        if service == 's3':
            return execute_s3_command(action, parameters)
        
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
        
        # Upload file
        elif action == 'upload_file':
            bucket = parameters.get('bucket')
            object_key = parameters.get('object_key')
            local_file = parameters.get('local_file')
            
            if not bucket or not object_key or not local_file:
                return "Please specify bucket, object key, and local file path."
            
            s3.upload_file(local_file, bucket, object_key)
            return f"✅ Uploaded '{local_file}' to '{bucket}' as '{object_key}'."
        
        # Download file
        elif action == 'download_file':
            bucket = parameters.get('bucket')
            object_key = parameters.get('object_key')
            local_file = parameters.get('local_file')
            
            if not bucket or not object_key or not local_file:
                return "Please specify bucket, object key, and local file path."
            
            s3.download_file(bucket, object_key, local_file)
            return f"✅ Downloaded '{object_key}' from '{bucket}' to '{local_file}'."
        
        return f"S3 action '{action}' not supported yet."
        
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
        # Test DynamoDB
        dynamodb.Table(KNOWLEDGE_BASE_TABLE).scan(Limit=1)
        results.append("✅ DynamoDB: Connected")
    except Exception as e:
        results.append(f"❌ DynamoDB: {str(e)}")
    
    try:
        # Test Bedrock with correct invocation
        bedrock.invoke_model(
            modelId='amazon.nova-micro-v1:0',
            body=json.dumps({
                'messages': [{'role': 'user', 'content': 'Hello'}]
            })
        )
        results.append("✅ Bedrock: Connected")
    except Exception as e:
        results.append(f"❌ Bedrock: {str(e)}")
    
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
• `upload FILE to BUCKET` - Upload local file to S3
• `download FILE from BUCKET` - Download S3 file locally

**💡 Examples:**
• "list my buckets"
• "list files in my-data-bucket"
• "copy report.pdf from staging to production"
• "upload data.csv to analytics-bucket"

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