import boto3
import json
from decimal import Decimal

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Define table name
TABLE_NAME = 'S3CommandKnowledgeBase'

def create_table_if_not_exists():
    """Create the DynamoDB table if it doesn't exist"""
    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {'AttributeName': 'intent_pattern', 'KeyType': 'HASH'},  # Partition key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'intent_pattern', 'AttributeType': 'S'},
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        print(f"Creating table {TABLE_NAME}...")
        table.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)
        print(f"Table {TABLE_NAME} created successfully!")
        return table
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print(f"Table {TABLE_NAME} already exists.")
        return dynamodb.Table(TABLE_NAME)

def seed_knowledge_base(table):
    """Seed the knowledge base with S3 command patterns and required parameters"""
    
    # Define S3 command patterns and their required parameters
    s3_commands = [
        {
            "intent_pattern": "list buckets",
            "service": "s3",
            "action": "list_buckets",
            "required_params": [],
            "example_phrases": [
                "show my buckets", 
                "list all s3 buckets", 
                "what buckets do I have"
            ],
            "needs_followup": False,
            "followup_question": None,
            "syntax_template": "List buckets"
        },
        {
            "intent_pattern": "list files",
            "service": "s3",
            "action": "list_objects",
            "required_params": ["bucket"],
            "example_phrases": [
                "show files in bucket", 
                "list objects", 
                "what's in my bucket"
            ],
            "needs_followup": True,
            "followup_question": "Which bucket would you like to list objects from?",
            "syntax_template": "List files from {bucket}"
        },
        {
            "intent_pattern": "create bucket",
            "service": "s3",
            "action": "create_bucket",
            "required_params": ["bucket"],
            "example_phrases": [
                "make a new bucket", 
                "create s3 bucket", 
                "add bucket"
            ],
            "needs_followup": True,
            "followup_question": "What name would you like to give to the new bucket?",
            "syntax_template": "Create bucket {bucket}"
        },
        {
            "intent_pattern": "delete file",
            "service": "s3",
            "action": "delete_object",
            "required_params": ["bucket", "object_key"],
            "example_phrases": [
                "remove file", 
                "delete object", 
                "remove file from bucket"
            ],
            "needs_followup": True,
            "followup_question": "Which file would you like to delete and from which bucket?",
            "syntax_template": "Delete {object_key} from {bucket}"
        },
        {
            "intent_pattern": "copy file",
            "service": "s3",
            "action": "copy_object",
            "required_params": ["source_bucket", "dest_bucket", "object_key"],
            "example_phrases": [
                "copy object between buckets", 
                "duplicate file", 
                "move file to another bucket"
            ],
            "needs_followup": True,
            "followup_question": "Which file would you like to copy, from which source bucket, to which destination bucket?",
            "syntax_template": "Copy {object_key} from {source_bucket} to {dest_bucket}"
        }
    ]
    
    # Convert to DynamoDB format and insert items
    with table.batch_writer() as batch:
        for command in s3_commands:
            # Convert to DynamoDB format (handling decimal types)
            item = json.loads(json.dumps(command), parse_float=Decimal)
            batch.put_item(Item=item)
    
    print(f"Successfully seeded {len(s3_commands)} command patterns to the knowledge base.")

def query_examples():
    """Show examples of querying the knowledge base"""
    table = dynamodb.Table(TABLE_NAME)
    
    # Example 1: Get command pattern for "list buckets"
    response = table.get_item(Key={'intent_pattern': 'list buckets'})
    if 'Item' in response:
        print("\nExample 1: Command pattern for 'list buckets'")
        print(json.dumps(response['Item'], indent=2, default=str))
    
    # Example 2: Get command pattern for "list files"
    response = table.get_item(Key={'intent_pattern': 'list files'})
    if 'Item' in response:
        print("\nExample 2: Command pattern for 'list files'")
        print(json.dumps(response['Item'], indent=2, default=str))

if __name__ == "__main__":
    # Create table if it doesn't exist
    table = create_table_if_not_exists()
    
    # Seed the knowledge base
    seed_knowledge_base(table)
    
    # Show query examples
    query_examples()