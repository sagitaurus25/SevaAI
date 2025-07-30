import boto3
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Constants
HISTORY_TABLE_NAME = 'S3AgentConversationHistory'

def create_history_table_if_not_exists():
    """Create the conversation history table if it doesn't exist"""
    try:
        table = dynamodb.create_table(
            TableName=HISTORY_TABLE_NAME,
            KeySchema=[
                {'AttributeName': 'session_id', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}   # Sort key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'session_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5},
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'ttl'
            }
        )
        print(f"Creating table {HISTORY_TABLE_NAME}...")
        table.meta.client.get_waiter('table_exists').wait(TableName=HISTORY_TABLE_NAME)
        print(f"Table {HISTORY_TABLE_NAME} created successfully!")
        return table
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print(f"Table {HISTORY_TABLE_NAME} already exists.")
        return dynamodb.Table(HISTORY_TABLE_NAME)

def store_conversation(session_id, user_message, bot_response):
    """Store a conversation exchange in DynamoDB"""
    try:
        table = dynamodb.Table(HISTORY_TABLE_NAME)
        
        # Current timestamp
        now = datetime.now()
        timestamp = now.isoformat()
        
        # TTL - expire after 30 days
        ttl = int((now + timedelta(days=30)).timestamp())
        
        # Store user message
        table.put_item(
            Item={
                'session_id': session_id,
                'timestamp': f"{timestamp}_user",
                'role': 'user',
                'message': user_message,
                'ttl': ttl
            }
        )
        
        # Store bot response
        table.put_item(
            Item={
                'session_id': session_id,
                'timestamp': f"{timestamp}_bot",
                'role': 'bot',
                'message': bot_response,
                'ttl': ttl
            }
        )
        
        return True
        
    except Exception as e:
        print(f"Error storing conversation: {str(e)}")
        return False

def get_conversation_history(session_id, limit=10):
    """Get conversation history for a session"""
    try:
        table = dynamodb.Table(HISTORY_TABLE_NAME)
        
        response = table.query(
            KeyConditionExpression='session_id = :sid',
            ExpressionAttributeValues={
                ':sid': session_id
            },
            ScanIndexForward=True,  # ascending order
            Limit=limit * 2  # limit * 2 because we have user and bot messages
        )
        
        history = []
        for item in response.get('Items', []):
            history.append({
                'role': item['role'],
                'message': item['message'],
                'timestamp': item['timestamp'].split('_')[0]
            })
        
        return history
        
    except Exception as e:
        print(f"Error getting conversation history: {str(e)}")
        return []

if __name__ == "__main__":
    # Create the table if it doesn't exist
    create_history_table_if_not_exists()
    
    # Test storing a conversation
    session_id = str(uuid.uuid4())
    store_conversation(session_id, "list my buckets", "You have 3 buckets: bucket1, bucket2, bucket3")
    
    # Get the conversation history
    history = get_conversation_history(session_id)
    print(f"Conversation history for session {session_id}:")
    for item in history:
        print(f"{item['timestamp']} - {item['role']}: {item['message']}")