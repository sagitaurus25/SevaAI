import boto3
import json
from datetime import datetime, timedelta

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Constants
HISTORY_TABLE_NAME = 'S3AgentConversationHistory'

def create_history_table():
    """Create the conversation history table"""
    try:
        # Check if table already exists
        existing_tables = dynamodb.meta.client.list_tables()['TableNames']
        if HISTORY_TABLE_NAME in existing_tables:
            print(f"Table {HISTORY_TABLE_NAME} already exists.")
            return dynamodb.Table(HISTORY_TABLE_NAME)
        
        # Create the table
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
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        print(f"Creating table {HISTORY_TABLE_NAME}...")
        table.meta.client.get_waiter('table_exists').wait(TableName=HISTORY_TABLE_NAME)
        print(f"Table {HISTORY_TABLE_NAME} created successfully!")
        
        # Enable TTL
        dynamodb.meta.client.update_time_to_live(
            TableName=HISTORY_TABLE_NAME,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'ttl'
            }
        )
        print(f"TTL enabled for table {HISTORY_TABLE_NAME}")
        
        return table
        
    except Exception as e:
        print(f"Error creating history table: {str(e)}")
        return None

def add_sample_data(table):
    """Add sample conversation data to the table"""
    try:
        session_id = "sample-session-1"
        now = datetime.now()
        ttl = int((now + timedelta(days=30)).timestamp())
        
        # Sample conversation
        conversation = [
            {"role": "user", "message": "Hello, can you help me with S3?"},
            {"role": "bot", "message": "Hello! I'm your AWS Aigent. I can help you manage your S3 buckets and objects. What would you like to do?"},
            {"role": "user", "message": "list my buckets"},
            {"role": "bot", "message": "📦 S3 Buckets (3):\nbucket1\nbucket2\nbucket3"},
            {"role": "user", "message": "list files in bucket1"},
            {"role": "bot", "message": "📁 Objects in 'bucket1' (2):\nfile1.txt\nfile2.jpg"}
        ]
        
        # Add items to the table
        for i, item in enumerate(conversation):
            timestamp = (now - timedelta(minutes=len(conversation) - i)).isoformat()
            
            table.put_item(
                Item={
                    'session_id': session_id,
                    'timestamp': f"{timestamp}_{item['role']}",
                    'role': item['role'],
                    'message': item['message'],
                    'ttl': ttl
                }
            )
        
        print(f"Added sample conversation data for session {session_id}")
        return True
        
    except Exception as e:
        print(f"Error adding sample data: {str(e)}")
        return False

def test_query(table):
    """Test querying the table"""
    try:
        session_id = "sample-session-1"
        
        response = table.query(
            KeyConditionExpression='session_id = :sid',
            ExpressionAttributeValues={
                ':sid': session_id
            },
            ScanIndexForward=True  # ascending order
        )
        
        print(f"\nConversation history for session {session_id}:")
        for item in response.get('Items', []):
            timestamp = item['timestamp'].split('_')[0]
            role = item['role']
            message = item['message']
            print(f"{timestamp} - {role}: {message}")
        
        return True
        
    except Exception as e:
        print(f"Error testing query: {str(e)}")
        return False

if __name__ == "__main__":
    print("Setting up conversation history table...")
    table = create_history_table()
    
    if table:
        add_sample_data(table)
        test_query(table)