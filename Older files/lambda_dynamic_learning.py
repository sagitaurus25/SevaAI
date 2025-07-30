import json
import boto3
import uuid
import hashlib
from datetime import datetime, timedelta
import os

# AWS clients
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """Main Lambda handler with dynamic learning prompts"""
    
    try:
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        message = body.get('message', '')
        session_id = body.get('session_id', str(uuid.uuid4()))
        
        print(f"🤖 Processing: {message} (session: {session_id})")
        
        # Debug mode - test connectivity
        if message.lower() == 'debug':
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'response': test_connectivity(),
                    'session_id': session_id,
                    'source': 'debug'
                })
            }
        
        # Seed common patterns on first run
        if message.lower() == 'seed':
            seed_common_patterns()
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'response': '🌱 Common patterns seeded',
                    'session_id': session_id,
                    'source': 'seed'
                })
            }
        
        # Get or create session
        session = get_session(session_id)
        
        # Process message based on session state
        if session.get('state') == 'WAITING':
            result = handle_followup_response(message, session)
        else:
            result = handle_new_query(message, session)
        
        # Update session
        update_session(session_id, session, result)
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'response': result,
                'session_id': session_id,
                'session_state': session.get('state', 'IDLE'),
                'source': 'dynamic_learning'
            })
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'response': f'Error: {str(e)}',
                'session_id': session_id,
                'source': 'error'
            })
        }

def get_session(session_id):
    """Get session from DynamoDB or create new one"""
    try:
        table = dynamodb.Table('conversation-context')
        response = table.get_item(Key={'session_id': session_id})
        
        if 'Item' in response:
            session = response['Item']
            last_update = datetime.fromisoformat(session.get('last_activity', '2000-01-01T00:00:00'))
            if (datetime.now() - last_update).seconds < 600:  # 10 minutes
                print(f"📱 Retrieved session: {session}")
                return session
        
        # Create new session
        session = {
            'session_id': session_id,
            'state': 'IDLE',
            'context': {},
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat()
        }
        print(f"📱 Created new session: {session_id}")
        return session
        
    except Exception as e:
        print(f"❌ Session retrieval error: {e}")
        return {'session_id': session_id, 'state': 'IDLE', 'context': {}}

def update_session(session_id, session, result):
    """Update session in DynamoDB"""
    try:
        session['last_activity'] = datetime.now().isoformat()
        
        # Determine new state based on result
        if isinstance(result, str) and any(word in result.lower() for word in ['which', 'what', 'specify']):
            session['state'] = 'WAITING'
        else:
            session['state'] = 'IDLE'
            session['context'] = {}  # Clear context after successful execution
        
        # Store session in DynamoDB
        table = dynamodb.Table('conversation-context')
        table.put_item(Item=session)
        print(f"💾 Session updated: {session_id} (state: {session['state']})")
        
    except Exception as e:
        print(f"❌ Session update error: {e}")

def handle_new_query(message, session):
    """Handle new query with dynamic learning prompts"""
    
    # 1. Check DynamoDB learned patterns
    learned_pattern = get_learned_pattern(message)
    if learned_pattern:
        print("📚 Using learned pattern")
        return execute_command(learned_pattern, session, message)
    
    # 2. Get successful patterns for dynamic prompt
    successful_patterns = get_successful_patterns()
    
    # 3. Build dynamic prompt with learned patterns
    dynamic_prompt = build_dynamic_prompt(message, successful_patterns)
    
    # 4. Ask AI Model with dynamic prompt
    print(f"🧠 Asking AI Model with dynamic prompt")
    ai_result = ask_ai_model(message, dynamic_prompt)
    
    if ai_result.get('needs_followup'):
        # Store context for follow-up
        partial_command = ai_result.get('partial_command', {})
        if 'confidence' in partial_command:
            del partial_command['confidence']
        
        session['context'] = {
            'waiting_for': determine_waiting_for(ai_result.get('question', '')),
            'partial_command': partial_command
        }
        session['last_query'] = message  # Store the original query
        print(f"💾 Stored context: {session['context']}")
        return ai_result.get('question', 'I need more information')
    else:
        # Store successful pattern with initial success count
        store_pattern(message, ai_result, success=True)
        return execute_command(ai_result, session, message)

def handle_followup_response(message, session):
    """Handle follow-up response using session context"""
    
    context = session.get('context', {})
    waiting_for = context.get('waiting_for')
    partial_command = context.get('partial_command', {})
    
    print(f"🔗 Handling followup: waiting for {waiting_for}")
    
    # Complete the command
    if waiting_for == 'bucket_name':
        partial_command['bucket'] = message.strip()
    elif waiting_for == 'resource':
        partial_command['bucket'] = message.strip()
        partial_command['resource'] = 'objects'
    elif waiting_for == 'dest_bucket':
        partial_command['dest_bucket'] = message.strip()
    elif waiting_for == 'source_bucket':
        partial_command['source_bucket'] = message.strip()
    
    # Store the completed pattern
    original_query = session.get('last_query', '')
    if original_query:
        store_pattern(original_query, partial_command, success=True)
    
    return execute_command(partial_command, session, message)

def build_dynamic_prompt(message, patterns):
    """Build dynamic prompt with learned patterns"""
    # Get top patterns by success rate
    top_patterns = sorted(patterns, key=lambda x: x.get('success_rate', 0), reverse=True)[:5]
    
    examples = ""
    for pattern in top_patterns:
        query = pattern.get('query', '')
        parsed = json.dumps(pattern.get('parsed_result', {}))
        examples += f'"{query}" → {parsed}\n'
    
    prompt = f"""Parse this AWS request into JSON format:
"{message}"

LEARNED SUCCESSFUL PATTERNS:
{examples}

Return JSON with these fields:
{{
  "action": "list|upload|move|delete",
  "resource": "buckets|objects|instances",
  "bucket": "bucket-name",
  "needs_followup": false
}}

If missing info, set needs_followup: true and include question."""

    return prompt

def get_successful_patterns():
    """Get successful patterns from DynamoDB"""
    try:
        table = dynamodb.Table('parsing-patterns')
        response = table.scan(
            FilterExpression="success_rate > :min_rate",
            ExpressionAttributeValues={":min_rate": 0.7}
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"❌ Failed to get patterns: {e}")
        return []

def get_learned_pattern(message):
    """Get learned pattern from DynamoDB"""
    try:
        table = dynamodb.Table('parsing-patterns')
        query_hash = hashlib.md5(message.lower().encode()).hexdigest()
        response = table.get_item(Key={'pattern_id': query_hash})
        
        if 'Item' in response:
            pattern = response['Item']
            if pattern.get('success_rate', 0) > 0.7:  # Only use patterns with good success rate
                return pattern.get('parsed_result', {})
    except Exception as e:
        print(f"❌ Pattern retrieval error: {e}")
    return None

def store_pattern(query, parsed_result, success=True):
    """Store pattern in DynamoDB with success/failure tracking"""
    try:
        table = dynamodb.Table('parsing-patterns')
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()
        
        # Check if pattern exists
        response = table.get_item(Key={'pattern_id': query_hash})
        
        if 'Item' in response:
            # Update existing pattern
            pattern = response['Item']
            success_count = pattern.get('success_count', 0)
            failure_count = pattern.get('failure_count', 0)
            
            if success:
                success_count += 1
            else:
                failure_count += 1
                
            success_rate = success_count / (success_count + failure_count) if (success_count + failure_count) > 0 else 0
            
            table.update_item(
                Key={'pattern_id': query_hash},
                UpdateExpression="set success_count=:s, failure_count=:f, success_rate=:r, last_used=:d",
                ExpressionAttributeValues={
                    ':s': success_count,
                    ':f': failure_count,
                    ':r': success_rate,
                    ':d': datetime.now().isoformat()
                }
            )
        else:
            # Create new pattern
            table.put_item(Item={
                'pattern_id': query_hash,
                'query': query,
                'parsed_result': parsed_result,
                'success_count': 1 if success else 0,
                'failure_count': 0 if success else 1,
                'success_rate': 1.0 if success else 0.0,
                'last_used': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            })
    except Exception as e:
        print(f"❌ Pattern storage error: {e}")

def ask_ai_model(message, dynamic_prompt):
    """Ask AI model to parse the request using dynamic prompt"""
    try:
        response = bedrock.invoke_model(
            modelId='amazon.nova-micro-v1:0',
            body=json.dumps({
                'messages': [{'role': 'user', 'content': dynamic_prompt}],
                'max_tokens': 200,
                'temperature': 0.1
            })
        )
        
        result = json.loads(response['body'].read())
        content = result['output']['message']['content'][0]['text']
        
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        
        return {'action': 'unknown', 'needs_followup': True, 'question': 'Could you clarify your request?'}
        
    except Exception as e:
        print(f"❌ AI model error: {e}")
        return {'action': 'unknown', 'needs_followup': True, 'question': 'I need more information to help you.'}

def execute_command(command, session, original_message):
    """Execute the parsed command and track success/failure"""
    try:
        action = command.get('action')
        resource = command.get('resource')
        bucket = command.get('bucket')
        
        if action == 'list' and resource == 'buckets':
            response = s3.list_buckets()
            buckets = [b['Name'] for b in response['Buckets']]
            result = f"📦 S3 Buckets ({len(buckets)}):\n" + '\n'.join(buckets)
            
            # Track success
            update_pattern_success(original_message, command, True)
            return result
        
        elif action == 'list' and resource == 'objects' and bucket:
            response = s3.list_objects_v2(Bucket=bucket, MaxKeys=50)
            objects = [obj['Key'] for obj in response.get('Contents', [])]
            result = f"📁 Objects in {bucket} ({len(objects)}):\n" + '\n'.join(objects)
            
            # Track success
            update_pattern_success(original_message, command, True)
            return result
        
        else:
            # Track failure for unsupported command
            update_pattern_success(original_message, command, False)
            return f"Unsupported command: {command}"
            
    except Exception as e:
        # Track failure
        update_pattern_success(original_message, command, False)
        return f"❌ Execution error: {str(e)}"

def update_pattern_success(query, parsed_result, success):
    """Update pattern success/failure count"""
    if not query:
        return
        
    try:
        store_pattern(query, parsed_result, success)
    except Exception as e:
        print(f"❌ Failed to update pattern success: {e}")

def determine_waiting_for(question):
    """Determine what we're waiting for based on the question"""
    question_lower = question.lower()
    
    if 'bucket' in question_lower and 'which' in question_lower:
        return 'bucket_name'
    elif 'resource' in question_lower:
        return 'resource'
    elif 'destination' in question_lower:
        return 'dest_bucket'
    elif 'source' in question_lower:
        return 'source_bucket'
    
    return 'unknown'

def seed_common_patterns():
    """Seed DynamoDB with common patterns"""
    common_patterns = [
        {"query": "list files", "pattern": {"action": "list", "resource": "objects"}},
        {"query": "list objects", "pattern": {"action": "list", "resource": "objects"}},
        {"query": "show files", "pattern": {"action": "list", "resource": "objects"}},
        {"query": "list buckets", "pattern": {"action": "list", "resource": "buckets"}},
        {"query": "show buckets", "pattern": {"action": "list", "resource": "buckets"}}
    ]
    
    for item in common_patterns:
        try:
            store_pattern(item["query"], item["pattern"], success=True)
        except Exception as e:
            print(f"❌ Seed error: {e}")

def test_connectivity():
    """Test connectivity to AWS services"""
    try:
        # Test DynamoDB
        table = dynamodb.Table('parsing-patterns')
        table.scan(Limit=1)
        
        # Test S3
        s3.list_buckets()
        
        return "✅ All services connected"
    except Exception as e:
        return f"❌ Connectivity test failed: {str(e)}"