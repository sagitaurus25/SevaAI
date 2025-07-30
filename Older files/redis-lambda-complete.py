import json
import boto3
import redis
import uuid
import hashlib
from datetime import datetime, timedelta
import os

# AWS clients
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Redis connection (will be set after cluster is ready)
redis_client = None

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
            store_learned_pattern(item["query"], item["pattern"])
        except:
            pass  # Ignore errors during seeding

def lambda_handler(event, context):
    """Main Lambda handler with Redis session management"""
    
    try:
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        message = body.get('message', '')
        session_id = body.get('session_id', str(uuid.uuid4()))
        ai_model = body.get('ai_model', 'auto')  # Get AI model preference
        
        print(f"🤖 Processing: {message} (session: {session_id})")
        
        # Debug mode - test connectivity
        if message.lower() == 'debug':
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'response': test_vpc_connectivity(),
                    'session_id': session_id,
                    'source': 'debug'
                })
            }
        
        # Initialize Redis connection
        init_redis()
        
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
            result = handle_new_query(message, session, ai_model)
        
        # Update session
        update_session(session_id, session, result)
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'response': result,
                'session_id': session_id,
                'session_state': session.get('state', 'IDLE'),
                'source': 'redis_session'
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

def init_redis():
    """Initialize Redis connection"""
    global redis_client
    
    if redis_client is None:
        redis_endpoint = os.environ.get('REDIS_ENDPOINT', 'localhost')
        redis_port = int(os.environ.get('REDIS_PORT', '6379'))
        
        try:
            redis_client = redis.Redis(
                host=redis_endpoint,
                port=redis_port,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            redis_client.ping()
            print(f"✅ Redis connected: {redis_endpoint}:{redis_port}")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            redis_client = None

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
        
        if isinstance(result, str) and any(word in result.lower() for word in ['which', 'what', 'specify']):
            session['state'] = 'WAITING'
        else:
            session['state'] = 'IDLE'
            session['context'] = {}
        
        table = dynamodb.Table('conversation-context')
        table.put_item(Item=session)
        print(f"💾 Session updated: {session_id} (state: {session['state']})")
        
    except Exception as e:
        print(f"❌ Session update error: {e}")

def handle_new_query(message, session, ai_model='auto'):
    """Handle new query - check cache, then DynamoDB, then AI model"""
    
    cached_pattern = get_cached_pattern(message)
    if cached_pattern:
        print("⚡ Using cached pattern")
        return execute_command(cached_pattern, session, message)
    
    learned_pattern = get_learned_pattern(message)
    if learned_pattern:
        print("📚 Using learned pattern")
        cache_pattern(message, learned_pattern)
        return execute_command(learned_pattern, session, message)
    
    print(f"🧠 Asking AI Model ({ai_model})")
    ai_result = ask_ai_model(message, ai_model)
    
    if ai_result.get('needs_followup'):
        partial_command = ai_result.get('partial_command', {})
        if 'confidence' in partial_command:
            del partial_command['confidence']
        
        session['context'] = {
            'waiting_for': determine_waiting_for(ai_result.get('question', '')),
            'partial_command': partial_command
        }
        session['last_query'] = message
        print(f"💾 Stored context: {session['context']}")
        return ai_result.get('question', 'I need more information')
    else:
        store_learned_pattern(message, ai_result)
        cache_pattern(message, ai_result)
        return execute_command(ai_result, session, message)

def handle_followup_response(message, session):
    """Handle follow-up response using session context"""
    
    context = session.get('context', {})
    waiting_for = context.get('waiting_for')
    partial_command = context.get('partial_command', {})
    
    print(f"🔗 Handling followup: waiting for {waiting_for}")
    
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
        store_learned_pattern(original_query, partial_command)
        cache_pattern(original_query, partial_command)
    
    return execute_command(partial_command, session, message)

def get_cached_pattern(message):
    """Get pattern from Redis cache"""
    if not redis_client:
        return None
    
    try:
        cache_key = f"pattern:{hashlib.md5(message.lower().encode()).hexdigest()}"
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        print(f"❌ Redis get error: {e}")
    return None

def cache_pattern(message, pattern):
    """Cache pattern in Redis"""
    if not redis_client:
        return
    
    try:
        cache_key = f"pattern:{hashlib.md5(message.lower().encode()).hexdigest()}"
        redis_client.setex(cache_key, 3600, json.dumps(pattern))  # 1 hour TTL
    except Exception as e:
        print(f"❌ Redis set error: {e}")

def get_learned_pattern(message):
    """Get learned pattern from DynamoDB"""
    try:
        table = dynamodb.Table('learned-patterns')
        query_hash = hashlib.md5(message.lower().encode()).hexdigest()
        response = table.get_item(Key={'query_hash': query_hash})
        
        if 'Item' in response:
            return response['Item']['pattern']
    except Exception as e:
        print(f"❌ DynamoDB get error: {e}")
    return None

def store_learned_pattern(message, pattern):
    """Store learned pattern in DynamoDB"""
    try:
        table = dynamodb.Table('learned-patterns')
        query_hash = hashlib.md5(message.lower().encode()).hexdigest()
        
        table.put_item(Item={
            'query_hash': query_hash,
            'original_query': message,
            'pattern': pattern,
            'created_at': datetime.now().isoformat(),
            'usage_count': 1
        })
    except Exception as e:
        print(f"❌ DynamoDB store error: {e}")

def ask_ai_model(message, ai_model='auto'):
    """Ask AI model to parse the request"""
    try:
        prompt = f"""Parse this AWS request into JSON:
"{message}"

Return JSON:
{{
  "action": "list|upload|move|delete",
  "resource": "buckets|objects|instances",
  "bucket": "bucket-name",
  "needs_followup": false
}}

If missing info, set needs_followup: true and include question."""

        response = bedrock.invoke_model(
            modelId='amazon.nova-micro-v1:0',
            body=json.dumps({
                'messages': [{'role': 'user', 'content': prompt}],
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
    """Execute the parsed command"""
    try:
        action = command.get('action')
        resource = command.get('resource')
        bucket = command.get('bucket')
        
        if action == 'list' and resource == 'buckets':
            response = s3.list_buckets()
            buckets = [b['Name'] for b in response['Buckets']]
            return f"📦 S3 Buckets ({len(buckets)}):\n" + '\n'.join(buckets)
        
        elif action == 'list' and resource == 'objects' and bucket:
            response = s3.list_objects_v2(Bucket=bucket, MaxKeys=50)
            objects = [obj['Key'] for obj in response.get('Contents', [])]
            return f"📁 Objects in {bucket} ({len(objects)}):\n" + '\n'.join(objects)
        
        else:
            return f"Command executed: {command}"
            
    except Exception as e:
        return f"❌ Execution error: {str(e)}"

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

def test_vpc_connectivity():
    """Test VPC connectivity"""
    try:
        # Test DynamoDB
        table = dynamodb.Table('conversation-context')
        table.table_status
        
        # Test S3
        s3.list_buckets()
        
        # Test Redis
        if redis_client:
            redis_client.ping()
            redis_status = "✅ Connected"
        else:
            redis_status = "❌ Not connected"
        
        return f"🔍 VPC Connectivity Test:\n✅ DynamoDB: Connected\n✅ S3: Connected\n{redis_status}: Redis"
        
    except Exception as e:
        return f"❌ VPC Test failed: {str(e)}"