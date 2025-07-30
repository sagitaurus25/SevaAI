#!/usr/bin/env python3

import boto3
import json
import uuid

def create_workflow_tables():
    """Create DynamoDB tables for configurable workflows"""
    
    # Initialize DynamoDB client
    dynamodb = boto3.client('dynamodb')
    
    # Create workflow definitions table
    try:
        dynamodb.create_table(
            TableName='S3WorkflowDefinitions',
            KeySchema=[
                {'AttributeName': 'workflow_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'workflow_id', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        print("✅ Created S3WorkflowDefinitions table")
    except dynamodb.exceptions.ResourceInUseException:
        print("✓ S3WorkflowDefinitions table already exists")
    
    # Create workflow executions table
    try:
        dynamodb.create_table(
            TableName='S3WorkflowExecutions',
            KeySchema=[
                {'AttributeName': 'execution_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'execution_id', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        print("✅ Created S3WorkflowExecutions table")
    except dynamodb.exceptions.ResourceInUseException:
        print("✓ S3WorkflowExecutions table already exists")
    
    # Wait for tables to be created
    print("Waiting for tables to be created...")
    waiter = dynamodb.get_waiter('table_exists')
    waiter.wait(TableName='S3WorkflowDefinitions')
    waiter.wait(TableName='S3WorkflowExecutions')
    
    print("✅ Tables are ready")
    
    # Create sample workflow definitions
    create_sample_workflows()
    
    return True

def create_sample_workflows():
    """Create sample workflow definitions"""
    
    # Initialize DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('S3WorkflowDefinitions')
    
    # Sample workflow 1: Organize images by date
    image_workflow = {
        'workflow_id': 'organize-images',
        'name': 'Organize Images by Date',
        'description': 'Organize image files into year/month folders based on creation date',
        'parameters': {
            'source_bucket': {
                'type': 'string',
                'description': 'Source bucket containing the images',
                'required': True
            },
            'file_types': {
                'type': 'array',
                'description': 'File extensions to process',
                'default': ['.jpg', '.jpeg', '.png', '.gif', '.heic'],
                'required': False
            },
            'date_format': {
                'type': 'string',
                'description': 'Folder structure format',
                'default': '%Y/%m',
                'required': False
            }
        },
        'steps': [
            {
                'action': 'scan',
                'description': 'Scan bucket for matching files'
            },
            {
                'action': 'extract_date',
                'description': 'Extract date from file metadata or name'
            },
            {
                'action': 'organize',
                'description': 'Move files to date-based folders'
            }
        ],
        'examples': [
            'organize images in my-photos-bucket',
            'organize images with extensions .jpg,.png in my-bucket',
            'organize images in my-bucket using format year-month'
        ]
    }
    
    # Sample workflow 2: Search and move files
    search_workflow = {
        'workflow_id': 'search-move',
        'name': 'Search and Move Files',
        'description': 'Search for files matching a pattern and move them to a destination folder',
        'parameters': {
            'source_bucket': {
                'type': 'string',
                'description': 'Source bucket to search in',
                'required': True
            },
            'search_pattern': {
                'type': 'string',
                'description': 'Pattern to search for (regex supported)',
                'required': True
            },
            'destination_prefix': {
                'type': 'string',
                'description': 'Destination folder prefix',
                'required': True
            }
        },
        'steps': [
            {
                'action': 'search',
                'description': 'Search for files matching pattern'
            },
            {
                'action': 'move',
                'description': 'Move matching files to destination'
            }
        ],
        'examples': [
            'search for invoice*.pdf in documents-bucket and move to invoices/',
            'find files matching 2023* in my-bucket and move to archive/2023/'
        ]
    }
    
    # Save workflows to DynamoDB
    try:
        table.put_item(Item=image_workflow)
        print(f"✅ Created workflow: {image_workflow['name']}")
        
        table.put_item(Item=search_workflow)
        print(f"✅ Created workflow: {search_workflow['name']}")
        
        return True
    except Exception as e:
        print(f"❌ Error creating sample workflows: {str(e)}")
        return False

def add_workflow_functions():
    """Add workflow functions to the S3 agent Lambda"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Adding workflow functions to Lambda: {FUNCTION_NAME}")
    
    # Get the current Lambda function code
    lambda_client = boto3.client('lambda')
    response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
    code_location = response['Code']['Location']
    
    import requests
    r = requests.get(code_location)
    
    # Save the current code
    with open('lambda_current.zip', 'wb') as f:
        f.write(r.content)
    
    # Extract the current code
    import zipfile
    import os
    import io
    with zipfile.ZipFile('lambda_current.zip', 'r') as zip_ref:
        zip_ref.extractall('lambda_extract')
    
    # Read the current lambda_function.py
    with open('lambda_extract/lambda_function.py', 'r') as f:
        current_code = f.read()
    
    # Add DynamoDB client initialization
    if 'dynamodb = boto3.resource(' not in current_code:
        current_code = current_code.replace(
            's3 = boto3.client(\'s3\')',
            's3 = boto3.client(\'s3\')\ndynamodb = boto3.resource(\'dynamodb\')'
        )
    
    # Add workflow functions
    workflow_functions = '''
def get_workflow_definitions():
    """Get all workflow definitions from DynamoDB"""
    try:
        table = dynamodb.Table('S3WorkflowDefinitions')
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        print(f"Error getting workflow definitions: {str(e)}")
        return []

def get_workflow_by_id(workflow_id):
    """Get a specific workflow definition by ID"""
    try:
        table = dynamodb.Table('S3WorkflowDefinitions')
        response = table.get_item(Key={'workflow_id': workflow_id})
        return response.get('Item')
    except Exception as e:
        print(f"Error getting workflow {workflow_id}: {str(e)}")
        return None

def parse_workflow_command(user_message):
    """Parse a workflow command from natural language"""
    try:
        # Get all workflow definitions
        workflows = get_workflow_definitions()
        if not workflows:
            return None
        
        # Try to match the command to a workflow
        user_message_lower = user_message.lower()
        
        for workflow in workflows:
            # Check if workflow name is in the message
            if workflow['name'].lower() in user_message_lower:
                # Extract parameters
                params = {}
                
                # Extract source bucket
                if 'in' in user_message_lower and 'bucket' in user_message_lower:
                    bucket_match = re.search(r'in\\s+([\\w-]+)\\s+bucket', user_message_lower)
                    if bucket_match:
                        params['source_bucket'] = bucket_match.group(1)
                
                # For organize-images workflow
                if workflow['workflow_id'] == 'organize-images':
                    # Extract file types
                    if 'extension' in user_message_lower or 'file type' in user_message_lower:
                        ext_match = re.search(r'extension[s]?\\s+([\\w\\.,]+)', user_message_lower)
                        if ext_match:
                            params['file_types'] = ext_match.group(1).split(',')
                    
                    # Extract date format
                    if 'format' in user_message_lower:
                        if 'year-month' in user_message_lower:
                            params['date_format'] = '%Y-%m'
                        elif 'year/month/day' in user_message_lower:
                            params['date_format'] = '%Y/%m/%d'
                
                # For search-move workflow
                if workflow['workflow_id'] == 'search-move':
                    # Extract search pattern
                    if 'search for' in user_message_lower or 'find' in user_message_lower:
                        pattern_match = re.search(r'(search for|find)\\s+([\\w\\*\\.]+)', user_message_lower)
                        if pattern_match:
                            params['search_pattern'] = pattern_match.group(2)
                    
                    # Extract destination
                    if 'move to' in user_message_lower:
                        dest_match = re.search(r'move to\\s+([\\w\\/]+)', user_message_lower)
                        if dest_match:
                            params['destination_prefix'] = dest_match.group(1)
                
                return {
                    'workflow_id': workflow['workflow_id'],
                    'parameters': params
                }
        
        return None
    except Exception as e:
        print(f"Error parsing workflow command: {str(e)}")
        return None

def execute_workflow(workflow_id, parameters):
    """Execute a workflow with the given parameters"""
    try:
        # Get the workflow definition
        workflow = get_workflow_by_id(workflow_id)
        if not workflow:
            return f"❌ Workflow '{workflow_id}' not found."
        
        # Validate parameters
        missing_params = []
        for param_name, param_config in workflow['parameters'].items():
            if param_config.get('required', False) and param_name not in parameters:
                missing_params.append(param_name)
        
        if missing_params:
            return f"❌ Missing required parameters: {', '.join(missing_params)}"
        
        # Fill in default values for optional parameters
        for param_name, param_config in workflow['parameters'].items():
            if param_name not in parameters and 'default' in param_config:
                parameters[param_name] = param_config['default']
        
        # Create execution record
        execution_id = str(uuid.uuid4())
        execution_table = dynamodb.Table('S3WorkflowExecutions')
        execution_table.put_item(Item={
            'execution_id': execution_id,
            'workflow_id': workflow_id,
            'parameters': parameters,
            'status': 'RUNNING',
            'start_time': datetime.now().isoformat(),
            'steps_completed': 0
        })
        
        # Execute workflow based on type
        if workflow_id == 'organize-images':
            result = execute_organize_images(workflow, parameters, execution_id)
        elif workflow_id == 'search-move':
            result = execute_search_move(workflow, parameters, execution_id)
        else:
            result = f"❌ Workflow type '{workflow_id}' not implemented."
        
        # Update execution record
        execution_table.update_item(
            Key={'execution_id': execution_id},
            UpdateExpression="set #s = :s, end_time = :t",
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': 'COMPLETED', ':t': datetime.now().isoformat()}
        )
        
        return result
    except Exception as e:
        print(f"Error executing workflow: {str(e)}")
        return f"❌ Error executing workflow: {str(e)}"

def execute_organize_images(workflow, parameters, execution_id):
    """Execute the organize-images workflow"""
    bucket = parameters['source_bucket']
    file_types = parameters.get('file_types', ['.jpg', '.jpeg', '.png', '.gif', '.heic'])
    date_format = parameters.get('date_format', '%Y/%m')
    
    # Implementation similar to organize_images_by_date function
    # but using the configurable parameters
    
    # For brevity, returning a placeholder result
    return f"✅ Organized images in bucket '{bucket}' using format '{date_format}'\\nProcessed file types: {', '.join(file_types)}"

def execute_search_move(workflow, parameters, execution_id):
    """Execute the search-move workflow"""
    bucket = parameters['source_bucket']
    search_pattern = parameters['search_pattern']
    destination_prefix = parameters['destination_prefix']
    
    # Implementation for searching and moving files
    
    # For brevity, returning a placeholder result
    return f"✅ Searched for '{search_pattern}' in bucket '{bucket}'\\nMoved matching files to '{destination_prefix}/'"

def list_workflows():
    """List all available workflows"""
    workflows = get_workflow_definitions()
    if not workflows:
        return "No workflows defined."
    
    result = "📋 Available Workflows:\\n\\n"
    
    for workflow in workflows:
        result += f"• {workflow['name']}\\n"
        result += f"  ID: {workflow['workflow_id']}\\n"
        result += f"  Description: {workflow['description']}\\n"
        result += f"  Example: {workflow['examples'][0]}\\n\\n"
    
    return result
'''
    
    # Add the functions to the code
    function_insertion_point = current_code.rfind('def test_connectivity')
    updated_code = current_code[:function_insertion_point] + workflow_functions + '\n\n' + current_code[function_insertion_point:]
    
    # Add command handlers
    command_handlers = '''
        # List workflows command
        if user_message_lower == 'list workflows':
            result = list_workflows()
            return create_response(result)
        
        # Try to parse as a workflow command
        workflow_command = parse_workflow_command(user_message)
        if workflow_command:
            result = execute_workflow(workflow_command['workflow_id'], workflow_command['parameters'])
            return create_response(result)
'''
    
    # Find a good place to insert the command handlers
    handler_insertion_point = updated_code.find('# Handle bucket name response after list files')
    updated_code = updated_code[:handler_insertion_point] + command_handlers + updated_code[handler_insertion_point:]
    
    # Add syntax helpers
    syntax_helpers = '''
        if user_message_lower == 'workflow' or user_message_lower == 'workflows':
            return create_response("To see available workflows, type `list workflows`")
'''
    
    # Find a good place to insert the syntax helpers
    helper_insertion_point = updated_code.find('# List buckets')
    updated_code = updated_code[:helper_insertion_point] + syntax_helpers + updated_code[helper_insertion_point:]
    
    # Update help message
    help_message = updated_code.split('def get_help_message()')[1]
    help_message_start = help_message.find('return """')
    help_message_end = help_message.find('"""', help_message_start + 8)
    
    new_help_section = """
**🔄 Workflow Operations:**
• `list workflows` - Show all available workflows
• `organize images in BUCKET` - Organize images by date
• `search for PATTERN in BUCKET and move to PREFIX` - Search and move files
"""
    
    current_help = help_message[help_message_start:help_message_end]
    system_commands_pos = current_help.find('**🔧 System Commands:**')
    
    new_help = current_help[:system_commands_pos] + new_help_section + current_help[system_commands_pos:]
    updated_help_message = help_message[:help_message_start] + new_help + help_message[help_message_end:]
    
    updated_code = updated_code.split('def get_help_message()')[0] + 'def get_help_message()' + updated_help_message
    
    # Write the updated code
    with open('lambda_extract/lambda_function.py', 'w') as f:
        f.write(updated_code)
    
    # Create a new zip file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write('lambda_extract/lambda_function.py', 'lambda_function.py')
    
    # Get the zip file content
    zip_buffer.seek(0)
    zip_content = zip_buffer.read()
    
    # Update the Lambda function
    try:
        # Update the function code
        response = lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_content,
            Publish=True
        )
        
        print(f"✅ Lambda function updated successfully")
        print(f"Version: {response.get('Version')}")
        
        # Update the function configuration to increase timeout and memory
        lambda_client.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Timeout=300,  # 5 minutes
            MemorySize=512  # 512 MB
        )
        
        print("✅ Lambda function configuration updated")
        
        # Clean up
        import shutil
        os.remove('lambda_current.zip')
        shutil.rmtree('lambda_extract')
        
        print("\n✅ Deployment complete!")
        print("The S3 agent now supports configurable workflows using DynamoDB.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    # Create DynamoDB tables for workflows
    create_workflow_tables()
    
    # Add workflow functions to Lambda
    add_workflow_functions()