import boto3
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def check_dynamodb_table(table_name):
    """Check the DynamoDB table and its contents"""
    
    print(f"Checking DynamoDB table: {table_name}")
    print("-" * 80)
    
    try:
        # Create DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        
        # Check if table exists
        try:
            table = dynamodb.Table(table_name)
            table.load()
            print(f"✅ Table '{table_name}' exists")
            
            # Print table details
            print(f"Status: {table.table_status}")
            print(f"Item Count: {table.item_count}")
            print(f"Size (bytes): {table.table_size_bytes}")
            
            # Print key schema
            print("\nKey Schema:")
            for key in table.key_schema:
                print(f"  {key['AttributeName']} ({key['KeyType']})")
            
            # Scan the table
            print("\nScanning table items...")
            response = table.scan()
            items = response.get('Items', [])
            
            print(f"Found {len(items)} items")
            
            if len(items) == 0:
                print("\n⚠️ WARNING: Table is empty")
                print("The knowledge base needs to be seeded with S3 command patterns")
                print("Run the seed_s3_knowledge_base.py script to populate the table")
                return True
            
            # Print a few items
            print("\nSample Items:")
            for i, item in enumerate(items[:5]):
                print(f"\nItem {i+1}:")
                print(json.dumps(item, indent=2, cls=DecimalEncoder))
            
            # Check for required patterns
            required_patterns = ["list buckets", "list files", "create bucket"]
            found_patterns = [item['intent_pattern'] for item in items if 'intent_pattern' in item]
            
            print("\nChecking for required patterns:")
            for pattern in required_patterns:
                if pattern in found_patterns:
                    print(f"  ✅ '{pattern}' found")
                else:
                    print(f"  ❌ '{pattern}' not found")
            
            missing_patterns = [pattern for pattern in required_patterns if pattern not in found_patterns]
            if missing_patterns:
                print("\n⚠️ WARNING: Some required patterns are missing")
                print("Run the seed_s3_knowledge_base.py script to populate the table")
            
            return True
            
        except dynamodb.meta.client.exceptions.ResourceNotFoundException:
            print(f"❌ Table '{table_name}' does not exist")
            print("You need to create the table and seed it with S3 command patterns")
            print("Run the seed_s3_knowledge_base.py script to create and populate the table")
            return False
            
    except Exception as e:
        print(f"Error checking DynamoDB table: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Check DynamoDB table')
    parser.add_argument('--table', '-t', default='S3CommandKnowledgeBase', help='DynamoDB table name')
    
    args = parser.parse_args()
    
    check_dynamodb_table(args.table)