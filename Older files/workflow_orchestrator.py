import boto3
import json
import uuid
from datetime import datetime

# Initialize AWS clients
stepfunctions = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

# Constants
WORKFLOW_TABLE = 'S3WorkflowDefinitions'
EXECUTION_TABLE = 'S3WorkflowExecutions'
STATE_MACHINE_PREFIX = 'S3Workflow-'

def create_execution_table_if_not_exists():
    """Create the workflow executions table if it doesn't exist"""
    try:
        table = dynamodb.create_table(
            TableName=EXECUTION_TABLE,
            KeySchema=[
                {'AttributeName': 'execution_id', 'KeyType': 'HASH'},  # Partition key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'execution_id', 'AttributeType': 'S'},
                {'AttributeName': 'workflow_id', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'WorkflowIdIndex',
                    'KeySchema': [
                        {'AttributeName': 'workflow_id', 'KeyType': 'HASH'},
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    'IndexName': 'StatusIndex',
                    'KeySchema': [
                        {'AttributeName': 'status', 'KeyType': 'HASH'},
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
        print(f"Creating table {EXECUTION_TABLE}...")
        table.meta.client.get_waiter('table_exists').wait(TableName=EXECUTION_TABLE)
        print(f"Table {EXECUTION_TABLE} created successfully!")
        return table
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print(f"Table {EXECUTION_TABLE} already exists.")
        return dynamodb.Table(EXECUTION_TABLE)

def get_workflow_definition(workflow_id):
    """Get workflow definition from DynamoDB"""
    table = dynamodb.Table(WORKFLOW_TABLE)
    response = table.get_item(Key={'workflow_id': workflow_id})
    if 'Item' not in response:
        raise ValueError(f"Workflow with ID {workflow_id} not found")
    return response['Item']

def get_workflow_by_type(workflow_type):
    """Get workflow definition by type"""
    table = dynamodb.Table(WORKFLOW_TABLE)
    response = table.query(
        IndexName='WorkflowTypeIndex',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('workflow_type').eq(workflow_type)
    )
    if not response.get('Items'):
        raise ValueError(f"No workflow found with type {workflow_type}")
    return response['Items'][0]  # Return the first matching workflow

def create_state_machine_definition(workflow):
    """Create Step Functions state machine definition from workflow"""
    steps = workflow['steps']
    
    # Create a Step Functions state machine definition
    states = {}
    
    # Add states for each step
    for i, step in enumerate(steps):
        step_id = step['step_id']
        function_name = step['function']
        
        # Create task state
        states[step_id] = {
            "Type": "Task",
            "Resource": f"arn:aws:lambda:${{AWS::Region}}:${{AWS::AccountId}}:function:{function_name}",
            "ResultPath": f"$.{step_id}_result",
            "Next": steps[i+1]['step_id'] if i < len(steps) - 1 else "WorkflowSucceeded"
        }
    
    # Add success and failure states
    states["WorkflowSucceeded"] = {
        "Type": "Succeed"
    }
    
    # Create the state machine definition
    state_machine = {
        "Comment": f"State machine for {workflow['name']}",
        "StartAt": steps[0]['step_id'],
        "States": states
    }
    
    return json.dumps(state_machine)

def create_or_update_state_machine(workflow):
    """Create or update Step Functions state machine for workflow"""
    state_machine_name = f"{STATE_MACHINE_PREFIX}{workflow['workflow_type']}"
    state_machine_definition = create_state_machine_definition(workflow)
    
    # Check if state machine exists
    try:
        response = stepfunctions.describe_state_machine(
            stateMachineArn=f"arn:aws:states:${{AWS::Region}}:${{AWS::AccountId}}:stateMachine:{state_machine_name}"
        )
        # Update existing state machine
        stepfunctions.update_state_machine(
            stateMachineArn=response['stateMachineArn'],
            definition=state_machine_definition
        )
        return response['stateMachineArn']
    except stepfunctions.exceptions.StateMachineDoesNotExist:
        # Create new state machine
        response = stepfunctions.create_state_machine(
            name=state_machine_name,
            definition=state_machine_definition,
            roleArn=f"arn:aws:iam::${{AWS::AccountId}}:role/StepFunctionsWorkflowRole"
        )
        return response['stateMachineArn']

def start_workflow_execution(workflow_id, parameters):
    """Start a workflow execution"""
    # Get workflow definition
    workflow = get_workflow_definition(workflow_id)
    
    # Create or update state machine
    state_machine_arn = create_or_update_state_machine(workflow)
    
    # Generate execution ID
    execution_id = str(uuid.uuid4())
    
    # Start execution
    execution = stepfunctions.start_execution(
        stateMachineArn=state_machine_arn,
        name=f"{workflow['workflow_type']}-{execution_id}",
        input=json.dumps({
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "parameters": parameters,
            "start_time": datetime.now().isoformat()
        })
    )
    
    # Record execution in DynamoDB
    execution_table = dynamodb.Table(EXECUTION_TABLE)
    execution_table.put_item(
        Item={
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "workflow_type": workflow['workflow_type'],
            "workflow_name": workflow['name'],
            "parameters": parameters,
            "status": "RUNNING",
            "start_time": datetime.now().isoformat(),
            "state_machine_execution_arn": execution['executionArn']
        }
    )
    
    return {
        "execution_id": execution_id,
        "workflow_id": workflow_id,
        "workflow_name": workflow['name'],
        "status": "RUNNING"
    }

def get_workflow_execution_status(execution_id):
    """Get status of a workflow execution"""
    execution_table = dynamodb.Table(EXECUTION_TABLE)
    response = execution_table.get_item(Key={"execution_id": execution_id})
    
    if 'Item' not in response:
        raise ValueError(f"Execution with ID {execution_id} not found")
    
    execution = response['Item']
    
    # If execution is still running, check Step Functions for latest status
    if execution['status'] == 'RUNNING':
        try:
            sf_response = stepfunctions.describe_execution(
                executionArn=execution['state_machine_execution_arn']
            )
            
            # Update status in DynamoDB if needed
            new_status = sf_response['status']
            if new_status != 'RUNNING':
                execution_table.update_item(
                    Key={"execution_id": execution_id},
                    UpdateExpression="SET #status = :status, end_time = :end_time",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":status": new_status,
                        ":end_time": datetime.now().isoformat()
                    }
                )
                execution['status'] = new_status
                execution['end_time'] = datetime.now().isoformat()
                
                # If execution completed, get the output
                if new_status == 'SUCCEEDED':
                    execution['output'] = json.loads(sf_response['output'])
        except Exception as e:
            print(f"Error getting Step Functions execution status: {str(e)}")
    
    return execution

def list_workflow_executions(workflow_id=None, status=None, limit=10):
    """List workflow executions with optional filters"""
    execution_table = dynamodb.Table(EXECUTION_TABLE)
    
    if workflow_id:
        # Query by workflow ID
        response = execution_table.query(
            IndexName='WorkflowIdIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('workflow_id').eq(workflow_id),
            Limit=limit
        )
    elif status:
        # Query by status
        response = execution_table.query(
            IndexName='StatusIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('status').eq(status),
            Limit=limit
        )
    else:
        # Scan all executions
        response = execution_table.scan(Limit=limit)
    
    return response.get('Items', [])

def list_available_workflows():
    """List all available workflow definitions"""
    workflow_table = dynamodb.Table(WORKFLOW_TABLE)
    response = workflow_table.scan(
        ProjectionExpression="workflow_id, workflow_type, #name, description",
        ExpressionAttributeNames={"#name": "name"}
    )
    return response.get('Items', [])

# Example usage
if __name__ == "__main__":
    # Create execution table
    create_execution_table_if_not_exists()
    
    # List available workflows
    workflows = list_available_workflows()
    print("Available workflows:")
    for wf in workflows:
        print(f"- {wf['name']} ({wf['workflow_type']}): {wf['description']}")
    
    # Example: Start an inventory report workflow
    if workflows:
        sample_workflow = workflows[0]
        print(f"\nStarting sample workflow: {sample_workflow['name']}")
        execution = start_workflow_execution(
            sample_workflow['workflow_id'],
            {"bucket": "example-bucket", "destination_bucket": "example-reports"}
        )
        print(f"Execution started: {execution}")
        
        # Get execution status
        status = get_workflow_execution_status(execution['execution_id'])
        print(f"Execution status: {status['status']}")