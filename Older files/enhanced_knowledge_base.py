import boto3
import json
from decimal import Decimal
import uuid

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Define table names
COMMAND_PATTERNS_TABLE = 'AWSAgentCommandPatterns'
SESSION_STATE_TABLE = 'AWSAgentSessionState'
CONVERSATION_HISTORY_TABLE = 'AWSAgentConversationHistory'

def create_tables():
    """Create all required DynamoDB tables if they don't exist"""
    
    # Create command patterns table
    command_table = dynamodb.create_table(
        TableName=COMMAND_PATTERNS_TABLE,
        KeySchema=[
            {'AttributeName': 'intent_pattern', 'KeyType': 'HASH'},
            {'AttributeName': 'service', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'intent_pattern', 'AttributeType': 'S'},
            {'AttributeName': 'service', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    # Create session state table
    session_table = dynamodb.create_table(
        TableName=SESSION_STATE_TABLE,
        KeySchema=[
            {'AttributeName': 'session_id', 'KeyType': 'HASH'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'session_id', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    # Create conversation history table
    history_table = dynamodb.create_table(
        TableName=CONVERSATION_HISTORY_TABLE,
        KeySchema=[
            {'AttributeName': 'session_id', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'session_id', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'N'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    print(f"Created tables: {COMMAND_PATTERNS_TABLE}, {SESSION_STATE_TABLE}, {CONVERSATION_HISTORY_TABLE}")
    return command_table, session_table, history_table

def seed_command_patterns():
    """Seed the command patterns table with initial patterns for multiple services"""
    table = dynamodb.Table(COMMAND_PATTERNS_TABLE)
    
    # S3 commands
    s3_commands = [
        {
            'intent_pattern': 'list buckets',
            'service': 's3',
            'action': 'list_buckets',
            'required_params': [],
            'example_phrases': ['list my buckets', 'show all buckets', 'what s3 buckets do I have'],
            'needs_followup': False,
            'followup_question': '',
            'syntax_template': 'aws s3 ls'
        },
        {
            'intent_pattern': 'list files',
            'service': 's3',
            'action': 'list_objects',
            'required_params': ['bucket_name'],
            'example_phrases': ['list my files', 'show objects in bucket', 'what files are in my bucket'],
            'needs_followup': True,
            'followup_question': 'Which bucket would you like to list files from?',
            'syntax_template': 'aws s3 ls s3://{bucket_name}'
        },
        {
            'intent_pattern': 'create bucket',
            'service': 's3',
            'action': 'create_bucket',
            'required_params': ['bucket_name'],
            'example_phrases': ['create a new bucket', 'make s3 bucket', 'set up a bucket'],
            'needs_followup': True,
            'followup_question': 'What would you like to name the new bucket?',
            'syntax_template': 'aws s3 mb s3://{bucket_name}'
        }
    ]
    
    # Lambda commands
    lambda_commands = [
        {
            'intent_pattern': 'list functions',
            'service': 'lambda',
            'action': 'list_functions',
            'required_params': [],
            'example_phrases': ['list my lambda functions', 'show all lambdas', 'what functions do I have'],
            'needs_followup': False,
            'followup_question': '',
            'syntax_template': 'aws lambda list-functions'
        },
        {
            'intent_pattern': 'get function',
            'service': 'lambda',
            'action': 'get_function',
            'required_params': ['function_name'],
            'example_phrases': ['show lambda details', 'get function info', 'describe my lambda'],
            'needs_followup': True,
            'followup_question': 'Which Lambda function would you like to get details for?',
            'syntax_template': 'aws lambda get-function --function-name {function_name}'
        },
        {
            'intent_pattern': 'list invocations',
            'service': 'lambda',
            'action': 'list_invocations',
            'required_params': ['function_name'],
            'example_phrases': ['show lambda invocations', 'list function calls', 'get lambda metrics'],
            'needs_followup': True,
            'followup_question': 'Which Lambda function would you like to see invocations for?',
            'syntax_template': 'aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Invocations --dimensions Name=FunctionName,Value={function_name}'
        }
    ]
    
    # EC2 commands
    ec2_commands = [
        {
            'intent_pattern': 'list instances',
            'service': 'ec2',
            'action': 'list_instances',
            'required_params': [],
            'example_phrases': ['list my ec2 instances', 'show all servers', 'what instances are running'],
            'needs_followup': False,
            'followup_question': '',
            'syntax_template': 'aws ec2 describe-instances'
        },
        {
            'intent_pattern': 'start instance',
            'service': 'ec2',
            'action': 'start_instance',
            'required_params': ['instance_id'],
            'example_phrases': ['start my server', 'power on instance', 'boot up ec2'],
            'needs_followup': True,
            'followup_question': 'Which EC2 instance would you like to start? Please provide the instance ID.',
            'syntax_template': 'aws ec2 start-instances --instance-ids {instance_id}'
        }
    ]
    
    # IAM commands
    iam_commands = [
        {
            'intent_pattern': 'list users',
            'service': 'iam',
            'action': 'list_users',
            'required_params': [],
            'example_phrases': ['list iam users', 'show all users', 'who has access'],
            'needs_followup': False,
            'followup_question': '',
            'syntax_template': 'aws iam list-users'
        },
        {
            'intent_pattern': 'list roles',
            'service': 'iam',
            'action': 'list_roles',
            'required_params': [],
            'example_phrases': ['list iam roles', 'show all roles', 'what roles exist'],
            'needs_followup': False,
            'followup_question': '',
            'syntax_template': 'aws iam list-roles'
        }
    ]
    
    # Combine all commands
    all_commands = s3_commands + lambda_commands + ec2_commands + iam_commands
    
    # Insert into DynamoDB
    with table.batch_writer() as batch:
        for command in all_commands:
            batch.put_item(Item=command)
    
    print(f"Seeded {len(all_commands)} command patterns into {COMMAND_PATTERNS_TABLE}")

def manage_session_state(session_id, state=None):
    """Create, update or retrieve session state"""
    table = dynamodb.Table(SESSION_STATE_TABLE)
    
    if state is None:
        # Retrieve existing state
        response = table.get_item(Key={'session_id': session_id})
        return response.get('Item', {'session_id': session_id, 'context': {}})
    else:
        # Update state
        table.put_item(Item={
            'session_id': session_id,
            'context': state.get('context', {}),
            'last_updated': Decimal(str(boto3.client('dynamodb').meta.client.meta.config.utc_now().timestamp()))
        })
        return state

def add_to_conversation_history(session_id, role, message, metadata=None):
    """Add a message to the conversation history"""
    table = dynamodb.Table(CONVERSATION_HISTORY_TABLE)
    
    timestamp = Decimal(str(boto3.client('dynamodb').meta.client.meta.config.utc_now().timestamp()))
    
    table.put_item(Item={
        'session_id': session_id,
        'timestamp': timestamp,
        'role': role,  # 'user' or 'assistant'
        'message': message,
        'metadata': metadata or {}
    })
    
    return timestamp

def get_conversation_history(session_id, limit=10):
    """Retrieve conversation history for a session"""
    table = dynamodb.Table(CONVERSATION_HISTORY_TABLE)
    
    response = table.query(
        KeyConditionExpression='session_id = :sid',
        ExpressionAttributeValues={':sid': session_id},
        ScanIndexForward=True,  # ascending order by timestamp
        Limit=limit
    )
    
    return response.get('Items', [])

def create_new_session():
    """Create a new session and return the session ID"""
    session_id = str(uuid.uuid4())
    manage_session_state(session_id, {'context': {}})
    return session_id

def find_matching_command(query, service=None):
    """Find a matching command pattern for the given query"""
    table = dynamodb.Table(COMMAND_PATTERNS_TABLE)
    
    # If service is specified, filter by service
    if service:
        response = table.scan(
            FilterExpression='service = :svc',
            ExpressionAttributeValues={':svc': service}
        )
    else:
        response = table.scan()
    
    items = response.get('Items', [])
    
    # Simple matching logic - can be enhanced with fuzzy matching
    query_lower = query.lower()
    best_match = None
    
    for item in items:
        # Check exact match with intent pattern
        if item['intent_pattern'] in query_lower:
            return item
        
        # Check example phrases
        for phrase in item.get('example_phrases', []):
            if phrase.lower() in query_lower:
                best_match = item
                break
    
    return best_match

if __name__ == "__main__":
    # Create tables and seed data
    try:
        create_tables()
        print("Waiting for tables to be created...")
        # In a real implementation, you would wait for tables to be active
        seed_command_patterns()
        print("Knowledge base setup complete!")
    except Exception as e:
        print(f"Error setting up knowledge base: {str(e)}")