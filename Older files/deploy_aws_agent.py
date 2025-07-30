#!/usr/bin/env python3
import boto3
import json
import os
import time
import zipfile
import argparse
import uuid
import shutil
from botocore.exceptions import ClientError

# Parse command line arguments
parser = argparse.ArgumentParser(description='Deploy AWS Agent')
parser.add_argument('--region', default='us-east-1', help='AWS region to deploy to')
parser.add_argument('--stack-name', default='AWSAgent', help='CloudFormation stack name')
parser.add_argument('--llm-model', default='anthropic.claude-3-sonnet-20240229-v1:0', 
                    help='Bedrock model ID to use')
parser.add_argument('--use-mcp', action='store_true', help='Enable MCP integration')
parser.add_argument('--mcp-endpoint', default='', help='MCP endpoint URL')
parser.add_argument('--vpc-id', default='', help='VPC ID for deployment (optional)')
parser.add_argument('--subnet-ids', default='', help='Comma-separated list of subnet IDs (optional)')
args = parser.parse_args()

# Initialize AWS clients
session = boto3.Session(region_name=args.region)
cloudformation = session.client('cloudformation')
s3 = session.client('s3')
lambda_client = session.client('lambda')
iam = session.client('iam')
dynamodb = session.client('dynamodb')
apigateway = session.client('apigatewayv2')

# Constants
STACK_NAME = args.stack_name
CODE_BUCKET = f"{STACK_NAME.lower()}-{str(uuid.uuid4())[:8]}"
LAMBDA_ROLE_NAME = f"{STACK_NAME}-LambdaRole"
API_NAME = f"{STACK_NAME}-API"
WEBSOCKET_API_NAME = f"{STACK_NAME}-WebSocketAPI"
DYNAMODB_COMMAND_TABLE = f"{STACK_NAME}CommandPatterns"
DYNAMODB_SESSION_TABLE = f"{STACK_NAME}SessionState"
DYNAMODB_HISTORY_TABLE = f"{STACK_NAME}ConversationHistory"

# Lambda function names
ORCHESTRATOR_FUNCTION = f"{STACK_NAME}-Orchestrator"
S3_HANDLER_FUNCTION = f"{STACK_NAME}-S3Handler"
LAMBDA_HANDLER_FUNCTION = f"{STACK_NAME}-LambdaHandler"
EC2_HANDLER_FUNCTION = f"{STACK_NAME}-EC2Handler"
IAM_HANDLER_FUNCTION = f"{STACK_NAME}-IAMHandler"
CLOUDWATCH_HANDLER_FUNCTION = f"{STACK_NAME}-CloudWatchHandler"

# Environment variables for Lambda functions
LAMBDA_ENV_VARS = {
    'COMMAND_PATTERNS_TABLE': DYNAMODB_COMMAND_TABLE,
    'SESSION_STATE_TABLE': DYNAMODB_SESSION_TABLE,
    'CONVERSATION_HISTORY_TABLE': DYNAMODB_HISTORY_TABLE,
    'S3_HANDLER_FUNCTION': S3_HANDLER_FUNCTION,
    'LAMBDA_HANDLER_FUNCTION': LAMBDA_HANDLER_FUNCTION,
    'EC2_HANDLER_FUNCTION': EC2_HANDLER_FUNCTION,
    'IAM_HANDLER_FUNCTION': IAM_HANDLER_FUNCTION,
    'CLOUDWATCH_HANDLER_FUNCTION': CLOUDWATCH_HANDLER_FUNCTION,
    'LLM_MODEL': args.llm_model,
    'USE_MCP': str(args.use_mcp).lower(),
    'MCP_ENDPOINT': args.mcp_endpoint
}

def create_zip_file(source_file, output_filename):
    """Create a zip file containing the source file"""
    with zipfile.ZipFile(output_filename, 'w') as zipf:
        zipf.write(source_file, os.path.basename(source_file))
    return output_filename

def create_s3_bucket():
    """Create an S3 bucket for Lambda code"""
    try:
        if args.region == 'us-east-1':
            s3.create_bucket(Bucket=CODE_BUCKET)
        else:
            s3.create_bucket(
                Bucket=CODE_BUCKET,
                CreateBucketConfiguration={'LocationConstraint': args.region}
            )
        print(f"Created S3 bucket: {CODE_BUCKET}")
        return CODE_BUCKET
    except Exception as e:
        print(f"Error creating S3 bucket: {str(e)}")
        raise

def upload_to_s3(file_path, s3_key):
    """Upload a file to the S3 bucket"""
    try:
        s3.upload_file(file_path, CODE_BUCKET, s3_key)
        print(f"Uploaded {file_path} to s3://{CODE_BUCKET}/{s3_key}")
        return f"s3://{CODE_BUCKET}/{s3_key}"
    except Exception as e:
        print(f"Error uploading to S3: {str(e)}")
        raise

def create_lambda_role():
    """Create IAM role for Lambda functions"""
    try:
        # Check if role already exists
        try:
            response = iam.get_role(RoleName=LAMBDA_ROLE_NAME)
            print(f"IAM role {LAMBDA_ROLE_NAME} already exists")
            return response['Role']['Arn']
        except iam.exceptions.NoSuchEntityException:
            pass
        
        # Create role with basic Lambda execution policy
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        response = iam.create_role(
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description=f"Role for {STACK_NAME} Lambda functions"
        )
        
        # Attach policies
        iam.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )
        
        # Create custom policy for AWS services access
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:BatchGetItem",
                        "dynamodb:BatchWriteItem"
                    ],
                    "Resource": [
                        f"arn:aws:dynamodb:{args.region}:*:table/{DYNAMODB_COMMAND_TABLE}",
                        f"arn:aws:dynamodb:{args.region}:*:table/{DYNAMODB_SESSION_TABLE}",
                        f"arn:aws:dynamodb:{args.region}:*:table/{DYNAMODB_HISTORY_TABLE}"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Resource": [
                        f"arn:aws:lambda:{args.region}:*:function:{ORCHESTRATOR_FUNCTION}",
                        f"arn:aws:lambda:{args.region}:*:function:{S3_HANDLER_FUNCTION}",
                        f"arn:aws:lambda:{args.region}:*:function:{LAMBDA_HANDLER_FUNCTION}",
                        f"arn:aws:lambda:{args.region}:*:function:{EC2_HANDLER_FUNCTION}",
                        f"arn:aws:lambda:{args.region}:*:function:{IAM_HANDLER_FUNCTION}",
                        f"arn:aws:lambda:{args.region}:*:function:{CLOUDWATCH_HANDLER_FUNCTION}"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:*"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:*"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:*"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:*"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "cloudwatch:*"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "execute-api:ManageConnections"
                    ],
                    "Resource": "arn:aws:execute-api:*:*:*/@connections/*"
                }
            ]
        }
        
        iam.put_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyName=f"{STACK_NAME}-AgentPolicy",
            PolicyDocument=json.dumps(policy_document)
        )
        
        print(f"Created IAM role: {LAMBDA_ROLE_NAME}")
        
        # Wait for role to propagate
        print("Waiting for IAM role to propagate...")
        time.sleep(10)
        
        return response['Role']['Arn']
    except Exception as e:
        print(f"Error creating IAM role: {str(e)}")
        raise

def create_dynamodb_tables():
    """Create DynamoDB tables for the agent"""
    try:
        # Create command patterns table
        try:
            dynamodb.create_table(
                TableName=DYNAMODB_COMMAND_TABLE,
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
            print(f"Created DynamoDB table: {DYNAMODB_COMMAND_TABLE}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print(f"DynamoDB table {DYNAMODB_COMMAND_TABLE} already exists")
            else:
                raise
        
        # Create session state table
        try:
            dynamodb.create_table(
                TableName=DYNAMODB_SESSION_TABLE,
                KeySchema=[
                    {'AttributeName': 'session_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'session_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print(f"Created DynamoDB table: {DYNAMODB_SESSION_TABLE}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print(f"DynamoDB table {DYNAMODB_SESSION_TABLE} already exists")
            else:
                raise
        
        # Create conversation history table
        try:
            dynamodb.create_table(
                TableName=DYNAMODB_HISTORY_TABLE,
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
            print(f"Created DynamoDB table: {DYNAMODB_HISTORY_TABLE}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print(f"DynamoDB table {DYNAMODB_HISTORY_TABLE} already exists")
            else:
                raise
        
        # Wait for tables to be active
        print("Waiting for DynamoDB tables to become active...")
        for table_name in [DYNAMODB_COMMAND_TABLE, DYNAMODB_SESSION_TABLE, DYNAMODB_HISTORY_TABLE]:
            waiter = dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=table_name)
        
        return True
    except Exception as e:
        print(f"Error creating DynamoDB tables: {str(e)}")
        raise

def create_lambda_function(function_name, handler, code_s3_key, role_arn, timeout=30):
    """Create a Lambda function"""
    try:
        # Check if function already exists
        try:
            lambda_client.get_function(FunctionName=function_name)
            print(f"Lambda function {function_name} already exists, updating...")
            
            # Update function code
            lambda_client.update_function_code(
                FunctionName=function_name,
                S3Bucket=CODE_BUCKET,
                S3Key=code_s3_key
            )
            
            # Update function configuration
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                Runtime='python3.9',
                Handler=handler,
                Role=role_arn,
                Timeout=timeout,
                MemorySize=256,
                Environment={
                    'Variables': LAMBDA_ENV_VARS
                }
            )
        except lambda_client.exceptions.ResourceNotFoundException:
            # Create new function
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Handler=handler,
                Role=role_arn,
                Code={
                    'S3Bucket': CODE_BUCKET,
                    'S3Key': code_s3_key
                },
                Timeout=timeout,
                MemorySize=256,
                Environment={
                    'Variables': LAMBDA_ENV_VARS
                }
            )
            print(f"Created Lambda function: {function_name}")
            
            # Wait for function to be active
            print(f"Waiting for Lambda function {function_name} to become active...")
            time.sleep(5)
        
        return function_name
    except Exception as e:
        print(f"Error creating Lambda function {function_name}: {str(e)}")
        raise

def create_api_gateway():
    """Create API Gateway for the agent"""
    try:
        # Create REST API
        try:
            apis = apigateway.get_apis()
            api_id = None
            
            for api in apis.get('Items', []):
                if api['Name'] == API_NAME:
                    api_id = api['ApiId']
                    print(f"API Gateway {API_NAME} already exists with ID: {api_id}")
                    break
            
            if not api_id:
                response = apigateway.create_api(
                    Name=API_NAME,
                    ProtocolType='HTTP',
                    CorsConfiguration={
                        'AllowOrigins': ['*'],
                        'AllowMethods': ['POST', 'GET', 'OPTIONS'],
                        'AllowHeaders': ['Content-Type', 'Authorization'],
                        'MaxAge': 300
                    }
                )
                api_id = response['ApiId']
                print(f"Created API Gateway: {API_NAME} with ID: {api_id}")
            
            # Create routes
            routes = apigateway.get_routes(ApiId=api_id)
            route_keys = [route['RouteKey'] for route in routes.get('Items', [])]
            
            if 'POST /message' not in route_keys:
                # Create integration with Lambda
                integration = apigateway.create_integration(
                    ApiId=api_id,
                    IntegrationType='AWS_PROXY',
                    IntegrationMethod='POST',
                    PayloadFormatVersion='2.0',
                    IntegrationUri=f"arn:aws:lambda:{args.region}:{boto3.client('sts').get_caller_identity()['Account']}:function:{ORCHESTRATOR_FUNCTION}"
                )
                
                # Create route
                apigateway.create_route(
                    ApiId=api_id,
                    RouteKey='POST /message',
                    Target=f"integrations/{integration['IntegrationId']}"
                )
                print("Created route: POST /message")
            
            # Deploy API
            stage_name = 'prod'
            apigateway.create_stage(
                ApiId=api_id,
                StageName=stage_name,
                AutoDeploy=True
            )
            
            # Add Lambda permission
            try:
                lambda_client.add_permission(
                    FunctionName=ORCHESTRATOR_FUNCTION,
                    StatementId=f"{ORCHESTRATOR_FUNCTION}-ApiGateway",
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=f"arn:aws:execute-api:{args.region}:{boto3.client('sts').get_caller_identity()['Account']}:{api_id}/*/*/message"
                )
            except lambda_client.exceptions.ResourceConflictException:
                # Permission already exists
                pass
            
            api_url = f"https://{api_id}.execute-api.{args.region}.amazonaws.com/{stage_name}/message"
            print(f"API Gateway URL: {api_url}")
            
            # Create WebSocket API
            websocket_api_id = None
            apis = apigateway.get_apis()
            
            for api in apis.get('Items', []):
                if api['Name'] == WEBSOCKET_API_NAME:
                    websocket_api_id = api['ApiId']
                    print(f"WebSocket API {WEBSOCKET_API_NAME} already exists with ID: {websocket_api_id}")
                    break
            
            if not websocket_api_id:
                response = apigateway.create_api(
                    Name=WEBSOCKET_API_NAME,
                    ProtocolType='WEBSOCKET',
                    RouteSelectionExpression='$request.body.action'
                )
                websocket_api_id = response['ApiId']
                print(f"Created WebSocket API: {WEBSOCKET_API_NAME} with ID: {websocket_api_id}")
            
            # Create WebSocket routes
            routes = apigateway.get_routes(ApiId=websocket_api_id)
            route_keys = [route['RouteKey'] for route in routes.get('Items', [])]
            
            # Create integrations for WebSocket routes
            for route_key in ['$connect', '$disconnect', 'sendMessage']:
                if route_key not in route_keys:
                    # Create integration with Lambda
                    integration = apigateway.create_integration(
                        ApiId=websocket_api_id,
                        IntegrationType='AWS_PROXY',
                        IntegrationMethod='POST',
                        IntegrationUri=f"arn:aws:lambda:{args.region}:{boto3.client('sts').get_caller_identity()['Account']}:function:{ORCHESTRATOR_FUNCTION}"
                    )
                    
                    # Create route
                    apigateway.create_route(
                        ApiId=websocket_api_id,
                        RouteKey=route_key,
                        Target=f"integrations/{integration['IntegrationId']}"
                    )
                    print(f"Created WebSocket route: {route_key}")
            
            # Deploy WebSocket API
            apigateway.create_stage(
                ApiId=websocket_api_id,
                StageName=stage_name,
                AutoDeploy=True
            )
            
            # Add Lambda permissions for WebSocket
            try:
                lambda_client.add_permission(
                    FunctionName=ORCHESTRATOR_FUNCTION,
                    StatementId=f"{ORCHESTRATOR_FUNCTION}-WebSocketApiGateway",
                    Action='lambda:InvokeFunction',
                    Principal='apigateway.amazonaws.com',
                    SourceArn=f"arn:aws:execute-api:{args.region}:{boto3.client('sts').get_caller_identity()['Account']}:{websocket_api_id}/*/*"
                )
            except lambda_client.exceptions.ResourceConflictException:
                # Permission already exists
                pass
            
            websocket_url = f"wss://{websocket_api_id}.execute-api.{args.region}.amazonaws.com/{stage_name}"
            print(f"WebSocket API URL: {websocket_url}")
            
            return {
                'rest_api_url': api_url,
                'websocket_api_url': websocket_url
            }
        except Exception as e:
            print(f"Error creating API Gateway: {str(e)}")
            raise
    except Exception as e:
        print(f"Error creating API Gateway: {str(e)}")
        raise

def update_web_interface(api_urls):
    """Update the web interface with API URLs"""
    try:
        interface_file = 'agent_interface.html'
        
        with open(interface_file, 'r') as f:
            content = f.read()
        
        # Update API endpoint
        updated_content = content.replace(
            "const API_ENDPOINT = 'https://your-api-gateway-endpoint.execute-api.region.amazonaws.com/prod';",
            f"const API_ENDPOINT = '{api_urls['rest_api_url']}';"
        )
        
        # Write updated file
        with open('agent_interface_deployed.html', 'w') as f:
            f.write(updated_content)
        
        print("Updated web interface with API URLs: agent_interface_deployed.html")
        return 'agent_interface_deployed.html'
    except Exception as e:
        print(f"Error updating web interface: {str(e)}")
        raise

def seed_knowledge_base():
    """Seed the knowledge base with initial command patterns"""
    try:
        # Create a temporary script to seed the knowledge base
        seed_script = """
import boto3
import json
from decimal import Decimal

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('{}')

# S3 commands
s3_commands = [
    {{
        'intent_pattern': 'list buckets',
        'service': 's3',
        'action': 'list_buckets',
        'required_params': [],
        'example_phrases': ['list my buckets', 'show all buckets', 'what s3 buckets do I have'],
        'needs_followup': False,
        'followup_question': '',
        'syntax_template': 'aws s3 ls'
    }},
    {{
        'intent_pattern': 'list files',
        'service': 's3',
        'action': 'list_objects',
        'required_params': ['bucket_name'],
        'example_phrases': ['list my files', 'show objects in bucket', 'what files are in my bucket'],
        'needs_followup': True,
        'followup_question': 'Which bucket would you like to list files from?',
        'syntax_template': 'aws s3 ls s3://{{bucket_name}}'
    }},
    {{
        'intent_pattern': 'create bucket',
        'service': 's3',
        'action': 'create_bucket',
        'required_params': ['bucket_name'],
        'example_phrases': ['create a new bucket', 'make s3 bucket', 'set up a bucket'],
        'needs_followup': True,
        'followup_question': 'What would you like to name the new bucket?',
        'syntax_template': 'aws s3 mb s3://{{bucket_name}}'
    }}
]

# Lambda commands
lambda_commands = [
    {{
        'intent_pattern': 'list functions',
        'service': 'lambda',
        'action': 'list_functions',
        'required_params': [],
        'example_phrases': ['list my lambda functions', 'show all lambdas', 'what functions do I have'],
        'needs_followup': False,
        'followup_question': '',
        'syntax_template': 'aws lambda list-functions'
    }},
    {{
        'intent_pattern': 'get function',
        'service': 'lambda',
        'action': 'get_function',
        'required_params': ['function_name'],
        'example_phrases': ['show lambda details', 'get function info', 'describe my lambda'],
        'needs_followup': True,
        'followup_question': 'Which Lambda function would you like to get details for?',
        'syntax_template': 'aws lambda get-function --function-name {{function_name}}'
    }},
    {{
        'intent_pattern': 'list invocations',
        'service': 'lambda',
        'action': 'list_invocations',
        'required_params': ['function_name'],
        'example_phrases': ['show lambda invocations', 'list function calls', 'get lambda metrics'],
        'needs_followup': True,
        'followup_question': 'Which Lambda function would you like to see invocations for?',
        'syntax_template': 'aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Invocations --dimensions Name=FunctionName,Value={{function_name}}'
    }}
]

# EC2 commands
ec2_commands = [
    {{
        'intent_pattern': 'list instances',
        'service': 'ec2',
        'action': 'list_instances',
        'required_params': [],
        'example_phrases': ['list my ec2 instances', 'show all servers', 'what instances are running'],
        'needs_followup': False,
        'followup_question': '',
        'syntax_template': 'aws ec2 describe-instances'
    }},
    {{
        'intent_pattern': 'start instance',
        'service': 'ec2',
        'action': 'start_instance',
        'required_params': ['instance_id'],
        'example_phrases': ['start my server', 'power on instance', 'boot up ec2'],
        'needs_followup': True,
        'followup_question': 'Which EC2 instance would you like to start? Please provide the instance ID.',
        'syntax_template': 'aws ec2 start-instances --instance-ids {{instance_id}}'
    }}
]

# IAM commands
iam_commands = [
    {{
        'intent_pattern': 'list users',
        'service': 'iam',
        'action': 'list_users',
        'required_params': [],
        'example_phrases': ['list iam users', 'show all users', 'who has access'],
        'needs_followup': False,
        'followup_question': '',
        'syntax_template': 'aws iam list-users'
    }},
    {{
        'intent_pattern': 'list roles',
        'service': 'iam',
        'action': 'list_roles',
        'required_params': [],
        'example_phrases': ['list iam roles', 'show all roles', 'what roles exist'],
        'needs_followup': False,
        'followup_question': '',
        'syntax_template': 'aws iam list-roles'
    }}
]

# Combine all commands
all_commands = s3_commands + lambda_commands + ec2_commands + iam_commands

# Insert into DynamoDB
with table.batch_writer() as batch:
    for command in all_commands:
        batch.put_item(Item=command)

print(f"Seeded {{len(all_commands)}} command patterns into the knowledge base")
""".format(DYNAMODB_COMMAND_TABLE)
        
        with open('seed_temp.py', 'w') as f:
            f.write(seed_script)
        
        # Execute the script
        os.system('python seed_temp.py')
        
        # Clean up
        os.remove('seed_temp.py')
        
        print("Knowledge base seeded successfully")
        return True
    except Exception as e:
        print(f"Error seeding knowledge base: {str(e)}")
        raise

def main():
    """Main deployment function"""
    print(f"Deploying AWS Agent to region {args.region}...")
    
    # Create S3 bucket for Lambda code
    bucket_name = create_s3_bucket()
    
    # Create IAM role for Lambda functions
    role_arn = create_lambda_role()
    
    # Create DynamoDB tables
    create_dynamodb_tables()
    
    # Create temporary directory for Lambda zip files
    os.makedirs('lambda_packages', exist_ok=True)
    
    # Package and upload Lambda functions
    orchestrator_zip = 'lambda_packages/orchestrator.zip'
    s3_handler_zip = 'lambda_packages/s3_handler.zip'
    
    create_zip_file('agent_orchestrator.py', orchestrator_zip)
    create_zip_file('s3_service_handler.py', s3_handler_zip)
    
    orchestrator_s3_key = 'lambda/orchestrator.zip'
    s3_handler_s3_key = 'lambda/s3_handler.zip'
    
    upload_to_s3(orchestrator_zip, orchestrator_s3_key)
    upload_to_s3(s3_handler_zip, s3_handler_s3_key)
    
    # Create Lambda functions
    create_lambda_function(
        ORCHESTRATOR_FUNCTION,
        'agent_orchestrator.lambda_handler',
        orchestrator_s3_key,
        role_arn,
        timeout=60
    )
    
    create_lambda_function(
        S3_HANDLER_FUNCTION,
        's3_service_handler.lambda_handler',
        s3_handler_s3_key,
        role_arn,
        timeout=30
    )
    
    # Create API Gateway
    api_urls = create_api_gateway()
    
    # Seed knowledge base
    seed_knowledge_base()
    
    # Update web interface
    updated_interface = update_web_interface(api_urls)
    
    # Clean up
    shutil.rmtree('lambda_packages')
    
    print("\n=== AWS Agent Deployment Complete ===")
    print(f"REST API URL: {api_urls['rest_api_url']}")
    print(f"WebSocket URL: {api_urls['websocket_api_url']}")
    print(f"Web Interface: {updated_interface}")
    print("\nTo use the agent, open the web interface in a browser.")
    print("You can also deploy the web interface to an S3 bucket for static website hosting.")

if __name__ == "__main__":
    main()