#!/usr/bin/env python3
import boto3
import json
import time
import os
import zipfile
import io
import argparse
from botocore.exceptions import ClientError

# Parse command line arguments
parser = argparse.ArgumentParser(description='Set up S3 Workflow Agent')
parser.add_argument('--region', default='us-east-1', help='AWS region to deploy to')
parser.add_argument('--profile', help='AWS CLI profile to use')
parser.add_argument('--stack-name', default='S3WorkflowAgent', help='CloudFormation stack name')
args = parser.parse_args()

# Initialize AWS clients with optional profile
session = boto3.Session(profile_name=args.profile, region_name=args.region)
cloudformation = session.client('cloudformation')
s3 = session.client('s3')
iam = session.client('iam')
lambda_client = session.client('lambda')
dynamodb = session.resource('dynamodb')
apigateway = session.client('apigateway')
stepfunctions = session.client('stepfunctions')

# Constants
LAMBDA_ROLE_NAME = 'S3WorkflowAgentRole'
STEP_FUNCTIONS_ROLE_NAME = 'StepFunctionsWorkflowRole'
LAMBDA_FUNCTION_NAME = 'S3WorkflowAgent'
API_NAME = 'S3WorkflowAgentAPI'
KNOWLEDGE_BASE_TABLE = 'S3CommandKnowledgeBase'
WORKFLOW_TABLE = 'S3WorkflowDefinitions'
EXECUTION_TABLE = 'S3WorkflowExecutions'
DEPLOYMENT_BUCKET = f's3-workflow-agent-deployment-{int(time.time())}'

def create_deployment_bucket():
    """Create S3 bucket for deployment artifacts"""
    try:
        s3.create_bucket(Bucket=DEPLOYMENT_BUCKET)
        print(f"Created deployment bucket: {DEPLOYMENT_BUCKET}")
    except ClientError as e:
        print(f"Error creating deployment bucket: {e}")
        exit(1)

def create_iam_roles():
    """Create IAM roles for Lambda and Step Functions"""
    # Create Lambda execution role
    lambda_trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        lambda_role = iam.create_role(
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(lambda_trust_policy),
            Description="Role for S3 Workflow Agent Lambda function"
        )
        
        # Attach policies
        iam.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess"
        )
        iam.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
        )
        iam.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
        )
        iam.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
        )
        iam.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/AWSStepFunctionsFullAccess"
        )
        
        print(f"Created Lambda execution role: {LAMBDA_ROLE_NAME}")
        
        # Create Step Functions execution role
        step_functions_trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "states.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        step_functions_role = iam.create_role(
            RoleName=STEP_FUNCTIONS_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(step_functions_trust_policy),
            Description="Role for S3 Workflow Step Functions"
        )
        
        # Attach policies
        iam.attach_role_policy(
            RoleName=STEP_FUNCTIONS_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/AWSLambda_FullAccess"
        )
        iam.attach_role_policy(
            RoleName=STEP_FUNCTIONS_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
        )
        
        print(f"Created Step Functions execution role: {STEP_FUNCTIONS_ROLE_NAME}")
        
        # Wait for roles to propagate
        print("Waiting for IAM roles to propagate...")
        time.sleep(10)
        
        return lambda_role['Role']['Arn'], step_functions_role['Role']['Arn']
    
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"IAM roles already exist, retrieving ARNs...")
            lambda_role_arn = f"arn:aws:iam::{session.client('sts').get_caller_identity()['Account']}:role/{LAMBDA_ROLE_NAME}"
            step_functions_role_arn = f"arn:aws:iam::{session.client('sts').get_caller_identity()['Account']}:role/{STEP_FUNCTIONS_ROLE_NAME}"
            return lambda_role_arn, step_functions_role_arn
        else:
            print(f"Error creating IAM roles: {e}")
            exit(1)

def create_dynamodb_tables():
    """Create DynamoDB tables for knowledge base and workflows"""
    # Import and run the table creation scripts
    try:
        # Create knowledge base table
        from seed_knowledge_base import create_table_if_not_exists as create_kb_table
        kb_table = create_kb_table()
        
        # Create workflow tables
        from workflow_schema import create_table_if_not_exists as create_workflow_table
        workflow_table = create_workflow_table()
        
        # Create execution table
        from workflow_orchestrator import create_execution_table_if_not_exists as create_execution_table
        execution_table = create_execution_table()
        
        print("Created DynamoDB tables successfully")
    except Exception as e:
        print(f"Error creating DynamoDB tables: {e}")
        exit(1)

def seed_tables():
    """Seed the DynamoDB tables with initial data"""
    try:
        # Seed knowledge base
        from seed_knowledge_base import seed_knowledge_base
        seed_knowledge_base(dynamodb.Table(KNOWLEDGE_BASE_TABLE))
        
        # Seed workflow definitions
        from workflow_schema import seed_workflow_definitions
        seed_workflow_definitions(dynamodb.Table(WORKFLOW_TABLE))
        
        print("Seeded DynamoDB tables successfully")
    except Exception as e:
        print(f"Error seeding DynamoDB tables: {e}")
        exit(1)

def create_lambda_function(lambda_role_arn):
    """Create Lambda function for the S3 agent"""
    # Create a deployment package
    try:
        # Create a zip file containing all the necessary files
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add main Lambda function
            zipf.write('s3_agent_workflow.py', 'lambda_function.py')
            
            # Add workflow modules
            zipf.write('workflow_orchestrator.py', 'workflow_orchestrator.py')
            zipf.write('workflow_lambdas.py', 'workflow_lambdas.py')
            
            # Add any other required files
            if os.path.exists('requirements.txt'):
                zipf.write('requirements.txt', 'requirements.txt')
        
        # Upload the deployment package to S3
        s3.put_object(
            Bucket=DEPLOYMENT_BUCKET,
            Key=f'{LAMBDA_FUNCTION_NAME}.zip',
            Body=zip_buffer.getvalue()
        )
        
        # Create the Lambda function
        response = lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime='python3.9',
            Role=lambda_role_arn,
            Handler='lambda_function.lambda_handler',
            Code={
                'S3Bucket': DEPLOYMENT_BUCKET,
                'S3Key': f'{LAMBDA_FUNCTION_NAME}.zip'
            },
            Timeout=30,
            MemorySize=256,
            Environment={
                'Variables': {
                    'KNOWLEDGE_BASE_TABLE': KNOWLEDGE_BASE_TABLE,
                    'WORKFLOW_TABLE': WORKFLOW_TABLE,
                    'EXECUTION_TABLE': EXECUTION_TABLE
                }
            }
        )
        
        print(f"Created Lambda function: {LAMBDA_FUNCTION_NAME}")
        return response['FunctionArn']
    
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            print(f"Lambda function {LAMBDA_FUNCTION_NAME} already exists, updating...")
            
            # Update the existing function
            response = lambda_client.update_function_code(
                FunctionName=LAMBDA_FUNCTION_NAME,
                S3Bucket=DEPLOYMENT_BUCKET,
                S3Key=f'{LAMBDA_FUNCTION_NAME}.zip'
            )
            
            print(f"Updated Lambda function: {LAMBDA_FUNCTION_NAME}")
            return response['FunctionArn']
        else:
            print(f"Error creating Lambda function: {e}")
            exit(1)

def create_workflow_lambda_functions(lambda_role_arn):
    """Create Lambda functions for workflow steps"""
    # Create a deployment package for workflow Lambda functions
    try:
        # Create a zip file containing the workflow Lambda functions
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write('workflow_lambdas.py', 'lambda_function.py')
        
        # Upload the deployment package to S3
        s3.put_object(
            Bucket=DEPLOYMENT_BUCKET,
            Key='workflow_lambdas.zip',
            Body=zip_buffer.getvalue()
        )
        
        # Define the Lambda functions to create
        workflow_functions = [
            # Inventory Report functions
            {'name': 'check_bucket_exists', 'handler': 'lambda_function.check_bucket_exists'},
            {'name': 'configure_s3_inventory', 'handler': 'lambda_function.configure_s3_inventory'},
            {'name': 'verify_inventory_config', 'handler': 'lambda_function.verify_inventory_config'},
            
            # Log Analysis functions
            {'name': 'query_cloudwatch_logs', 'handler': 'lambda_function.query_cloudwatch_logs'},
            {'name': 'analyze_error_patterns', 'handler': 'lambda_function.analyze_error_patterns'},
            {'name': 'generate_error_report', 'handler': 'lambda_function.generate_error_report'},
            
            # Lifecycle Management functions
            {'name': 'create_lifecycle_configuration', 'handler': 'lambda_function.create_lifecycle_configuration'},
            {'name': 'apply_lifecycle_configuration', 'handler': 'lambda_function.apply_lifecycle_configuration'},
            {'name': 'verify_lifecycle_configuration', 'handler': 'lambda_function.verify_lifecycle_configuration'}
        ]
        
        # Create or update each function
        function_arns = {}
        for func in workflow_functions:
            try:
                response = lambda_client.create_function(
                    FunctionName=func['name'],
                    Runtime='python3.9',
                    Role=lambda_role_arn,
                    Handler=func['handler'],
                    Code={
                        'S3Bucket': DEPLOYMENT_BUCKET,
                        'S3Key': 'workflow_lambdas.zip'
                    },
                    Timeout=30,
                    MemorySize=256,
                    Environment={
                        'Variables': {
                            'EXECUTION_TABLE': EXECUTION_TABLE
                        }
                    }
                )
                print(f"Created Lambda function: {func['name']}")
                function_arns[func['name']] = response['FunctionArn']
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceConflictException':
                    print(f"Lambda function {func['name']} already exists, updating...")
                    
                    # Update the existing function
                    response = lambda_client.update_function_code(
                        FunctionName=func['name'],
                        S3Bucket=DEPLOYMENT_BUCKET,
                        S3Key='workflow_lambdas.zip'
                    )
                    
                    print(f"Updated Lambda function: {func['name']}")
                    function_arns[func['name']] = response['FunctionArn']
                else:
                    print(f"Error creating Lambda function {func['name']}: {e}")
        
        return function_arns
    
    except Exception as e:
        print(f"Error creating workflow Lambda functions: {e}")
        exit(1)

def create_api_gateway(lambda_function_arn):
    """Create API Gateway for the S3 agent"""
    try:
        # Create REST API
        api = apigateway.create_rest_api(
            name=API_NAME,
            description='API for S3 Workflow Agent',
            endpointConfiguration={
                'types': ['REGIONAL']
            }
        )
        
        api_id = api['id']
        
        # Get the root resource ID
        resources = apigateway.get_resources(restApiId=api_id)
        root_id = [resource for resource in resources['items'] if resource['path'] == '/'][0]['id']
        
        # Create a resource
        resource = apigateway.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='s3agent'
        )
        
        resource_id = resource['id']
        
        # Create POST method
        apigateway.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='POST',
            authorizationType='NONE',
            apiKeyRequired=False
        )
        
        # Create OPTIONS method for CORS
        apigateway.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE',
            apiKeyRequired=False
        )
        
        # Set up Lambda integration for POST
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='POST',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=f'arn:aws:apigateway:{args.region}:lambda:path/2015-03-31/functions/{lambda_function_arn}/invocations'
        )
        
        # Set up mock integration for OPTIONS
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            integrationHttpMethod='OPTIONS',
            requestTemplates={
                'application/json': '{"statusCode": 200}'
            }
        )
        
        # Set up method response for OPTIONS
        apigateway.put_method_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Origin': True
            },
            responseModels={
                'application/json': 'Empty'
            }
        )
        
        # Set up integration response for OPTIONS
        apigateway.put_integration_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            },
            responseTemplates={
                'application/json': ''
            }
        )
        
        # Deploy the API
        deployment = apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Production deployment'
        )
        
        # Add Lambda permission
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId=f'apigateway-invoke-{int(time.time())}',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:{args.region}:{session.client("sts").get_caller_identity()["Account"]}:{api_id}/*/*/s3agent'
        )
        
        # Get the API URL
        api_url = f'https://{api_id}.execute-api.{args.region}.amazonaws.com/prod/s3agent'
        print(f"Created API Gateway: {api_url}")
        
        return api_url
    
    except ClientError as e:
        print(f"Error creating API Gateway: {e}")
        exit(1)

def update_frontend(api_url):
    """Update the frontend HTML with the API URL"""
    try:
        with open('s3_agent_workflow_interface.html', 'r') as file:
            content = file.read()
        
        # Replace the API endpoint
        updated_content = content.replace(
            "const API_ENDPOINT = 'https://1jbk6z92h3.execute-api.us-east-1.amazonaws.com/prod/s3agent';",
            f"const API_ENDPOINT = '{api_url}';"
        )
        
        with open('s3_agent_workflow_interface.html', 'w') as file:
            file.write(updated_content)
        
        print(f"Updated frontend with API URL: {api_url}")
    except Exception as e:
        print(f"Error updating frontend: {e}")

def main():
    """Main deployment function"""
    print("Starting S3 Workflow Agent deployment...")
    
    # Create deployment bucket
    create_deployment_bucket()
    
    # Create IAM roles
    lambda_role_arn, step_functions_role_arn = create_iam_roles()
    
    # Create DynamoDB tables
    create_dynamodb_tables()
    
    # Seed tables with initial data
    seed_tables()
    
    # Create Lambda functions for workflow steps
    workflow_function_arns = create_workflow_lambda_functions(lambda_role_arn)
    
    # Create main Lambda function
    lambda_function_arn = create_lambda_function(lambda_role_arn)
    
    # Create API Gateway
    api_url = create_api_gateway(lambda_function_arn)
    
    # Update frontend with API URL
    update_frontend(api_url)
    
    print("\n=== Deployment Complete ===")
    print(f"API URL: {api_url}")
    print("To use the S3 Workflow Agent, open s3_agent_workflow_interface.html in your browser")
    print("You can also test the API directly using curl or Postman")

if __name__ == "__main__":
    main()