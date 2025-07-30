import boto3
import json
from decimal import Decimal
import uuid
from datetime import datetime

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Define table name
TABLE_NAME = 'S3WorkflowDefinitions'

def create_table_if_not_exists():
    """Create the DynamoDB table if it doesn't exist"""
    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {'AttributeName': 'workflow_id', 'KeyType': 'HASH'},  # Partition key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'workflow_id', 'AttributeType': 'S'},
                {'AttributeName': 'workflow_type', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'WorkflowTypeIndex',
                    'KeySchema': [
                        {'AttributeName': 'workflow_type', 'KeyType': 'HASH'},
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
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

def seed_workflow_definitions(table):
    """Seed the table with sample workflow definitions"""
    
    # Define sample workflow definitions
    workflows = [
        {
            "workflow_id": str(uuid.uuid4()),
            "workflow_type": "inventory_report",
            "name": "S3 Inventory Report",
            "description": "Configure S3 inventory, set output format and schedule frequency",
            "parameters": {
                "bucket": {"type": "string", "description": "Source bucket for inventory"},
                "destination_bucket": {"type": "string", "description": "Destination bucket for inventory reports"},
                "format": {"type": "string", "description": "Output format (CSV/ORC)", "default": "CSV"},
                "frequency": {"type": "string", "description": "Report frequency", "default": "Weekly"}
            },
            "steps": [
                {
                    "step_id": "check_buckets",
                    "type": "lambda",
                    "function": "check_bucket_exists",
                    "description": "Verify source and destination buckets exist"
                },
                {
                    "step_id": "configure_inventory",
                    "type": "lambda",
                    "function": "configure_s3_inventory",
                    "description": "Configure S3 inventory settings"
                },
                {
                    "step_id": "verify_configuration",
                    "type": "lambda",
                    "function": "verify_inventory_config",
                    "description": "Verify inventory configuration is active"
                }
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "example_phrases": [
                "set up inventory report for my bucket",
                "configure weekly inventory for bucket",
                "create s3 inventory in csv format"
            ]
        },
        {
            "workflow_id": str(uuid.uuid4()),
            "workflow_type": "log_analysis",
            "name": "Log Analysis Workflow",
            "description": "Query CloudWatch logs for errors, group by type and generate summary",
            "parameters": {
                "log_group": {"type": "string", "description": "CloudWatch log group name"},
                "time_range": {"type": "string", "description": "Time range for analysis", "default": "1d"},
                "error_threshold": {"type": "number", "description": "Error threshold for alerts", "default": 5}
            },
            "steps": [
                {
                    "step_id": "query_logs",
                    "type": "lambda",
                    "function": "query_cloudwatch_logs",
                    "description": "Query CloudWatch logs for error entries"
                },
                {
                    "step_id": "analyze_errors",
                    "type": "lambda",
                    "function": "analyze_error_patterns",
                    "description": "Group errors by type and frequency"
                },
                {
                    "step_id": "generate_report",
                    "type": "lambda",
                    "function": "generate_error_report",
                    "description": "Generate summary statistics and insights"
                }
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "example_phrases": [
                "analyze logs for errors",
                "generate error report from cloudwatch",
                "find error patterns in my logs"
            ]
        },
        {
            "workflow_id": str(uuid.uuid4()),
            "workflow_type": "lifecycle_management",
            "name": "S3 Lifecycle Management",
            "description": "Configure lifecycle rules for S3 objects with transitions and expirations",
            "parameters": {
                "bucket": {"type": "string", "description": "Bucket to configure lifecycle rules for"},
                "prefix": {"type": "string", "description": "Object prefix to apply rules to", "default": "logs/"},
                "transition_days": {"type": "number", "description": "Days before transition to Glacier", "default": 30},
                "expiration_days": {"type": "number", "description": "Days before object expiration", "default": 365}
            },
            "steps": [
                {
                    "step_id": "check_bucket",
                    "type": "lambda",
                    "function": "check_bucket_exists",
                    "description": "Verify bucket exists"
                },
                {
                    "step_id": "create_lifecycle_config",
                    "type": "lambda",
                    "function": "create_lifecycle_configuration",
                    "description": "Create lifecycle configuration with specified rules"
                },
                {
                    "step_id": "apply_lifecycle_config",
                    "type": "lambda",
                    "function": "apply_lifecycle_configuration",
                    "description": "Apply lifecycle configuration to bucket"
                },
                {
                    "step_id": "verify_lifecycle_config",
                    "type": "lambda",
                    "function": "verify_lifecycle_configuration",
                    "description": "Verify lifecycle configuration is active"
                }
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "example_phrases": [
                "set up lifecycle rules for my bucket",
                "configure glacier transition after 30 days",
                "create expiration policy for log files"
            ]
        }
    ]
    
    # Convert to DynamoDB format and insert items
    with table.batch_writer() as batch:
        for workflow in workflows:
            # Convert to DynamoDB format (handling decimal types)
            item = json.loads(json.dumps(workflow), parse_float=Decimal)
            batch.put_item(Item=item)
    
    print(f"Successfully seeded {len(workflows)} workflow definitions.")

def query_examples():
    """Show examples of querying the workflow definitions"""
    table = dynamodb.Table(TABLE_NAME)
    
    # Example 1: Get all inventory report workflows
    response = table.query(
        IndexName='WorkflowTypeIndex',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('workflow_type').eq('inventory_report')
    )
    if 'Items' in response:
        print("\nExample 1: Inventory Report Workflows")
        for item in response['Items']:
            print(f"- {item['name']}: {item['description']}")
    
    # Example 2: Get all workflow types
    response = table.scan(
        ProjectionExpression='workflow_type, #name',
        ExpressionAttributeNames={'#name': 'name'}
    )
    if 'Items' in response:
        print("\nExample 2: Available Workflow Types")
        workflow_types = {}
        for item in response['Items']:
            wf_type = item['workflow_type']
            if wf_type not in workflow_types:
                workflow_types[wf_type] = item['name']
        
        for wf_type, name in workflow_types.items():
            print(f"- {wf_type}: {name}")

if __name__ == "__main__":
    # Create table if it doesn't exist
    table = create_table_if_not_exists()
    
    # Seed the workflow definitions
    seed_workflow_definitions(table)
    
    # Show query examples
    query_examples()