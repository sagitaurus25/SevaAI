#!/usr/bin/env python3
import boto3
import json
import os
import sys
import time
import zipfile
import io
import subprocess
import argparse

# Configuration
CONFIG = {
    'lambda_function_name': 'SevaAI-S3Agent',
    'dynamodb_table_name': 'S3CommandKnowledgeBase',
    'api_gateway_name': 'SevaAI-S3Agent-API',
    'lambda_file': 'lambda_nova_parser_correct.py',
    'html_file': 's3_agent_interface.html'
}

def print_header(message):
    """Print a header message"""
    print("\n" + "=" * 80)
    print(f" {message}")
    print("=" * 80)

def print_step(step, message):
    """Print a step message"""
    print(f"\n[{step}] {message}")
    print("-" * 80)

def check_aws_credentials():
    """Check if AWS credentials are configured"""
    try:
        session = boto3.Session()
        identity = session.client('sts').get_caller_identity()
        print(f"✅ AWS credentials found for: {identity['Arn']}")
        return True
    except Exception as e:
        print(f"❌ AWS credentials not found or invalid: {str(e)}")
        print("Please configure your AWS credentials using 'aws configure'")
        return False

def check_dynamodb_table():
    """Check if the DynamoDB table exists"""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(CONFIG['dynamodb_table_name'])
        table.scan(Limit=1)
        print(f"✅ DynamoDB table '{CONFIG['dynamodb_table_name']}' exists")
        return True
    except Exception as e:
        print(f"❌ DynamoDB table '{CONFIG['dynamodb_table_name']}' not found: {str(e)}")
        return False

def create_dynamodb_table():
    """Create the DynamoDB table"""
    try:
        print(f"Creating DynamoDB table '{CONFIG['dynamodb_table_name']}'...")
        
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.create_table(
            TableName=CONFIG['dynamodb_table_name'],
            KeySchema=[
                {'AttributeName': 'intent_pattern', 'KeyType': 'HASH'},  # Partition key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'intent_pattern', 'AttributeType': 'S'},
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        
        print(f"Waiting for table to be created...")
        table.meta.client.get_waiter('table_exists').wait(TableName=CONFIG['dynamodb_table_name'])
        print(f"✅ DynamoDB table '{CONFIG['dynamodb_table_name']}' created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating DynamoDB table: {str(e)}")
        return False

def seed_knowledge_base():
    """Seed the knowledge base with S3 command patterns"""
    try:
        print("Running seed_s3_knowledge_base.py...")
        result = subprocess.run(['python', 'seed_s3_knowledge_base.py'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Knowledge base seeded successfully")
            return True
        else:
            print(f"❌ Error seeding knowledge base: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error running seed script: {str(e)}")
        return False

def check_lambda_function():
    """Check if the Lambda function exists"""
    try:
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function(
            FunctionName=CONFIG['lambda_function_name']
        )
        print(f"✅ Lambda function '{CONFIG['lambda_function_name']}' exists")
        return True
    except Exception as e:
        print(f"❌ Lambda function '{CONFIG['lambda_function_name']}' not found")
        return False

def create_lambda_function():
    """Create the Lambda function"""
    try:
        print(f"Creating Lambda function '{CONFIG['lambda_function_name']}'...")
        
        # Create a zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
            # Add the Lambda function code
            if os.path.exists(CONFIG['lambda_file']):
                zip_file.write(CONFIG['lambda_file'])
                print(f"✅ Added {CONFIG['lambda_file']} to deployment package")
            else:
                print(f"❌ Error: {CONFIG['lambda_file']} not found")
                return False
        
        # Get the zip file content
        zip_buffer.seek(0)
        zip_content = zip_buffer.read()
        
        # Create the Lambda function
        lambda_client = boto3.client('lambda')
        
        # Get the Lambda execution role
        print("Please enter the ARN of the Lambda execution role:")
        print("(This role should have permissions for S3, DynamoDB, and Bedrock)")
        role_arn = input("Role ARN: ")
        
        response = lambda_client.create_function(
            FunctionName=CONFIG['lambda_function_name'],
            Runtime='python3.9',
            Role=role_arn,
            Handler=f"{os.path.splitext(CONFIG['lambda_file'])[0]}.lambda_handler",
            Code={
                'ZipFile': zip_content
            },
            Timeout=30,
            MemorySize=256,
            Environment={
                'Variables': {
                    'KNOWLEDGE_BASE_TABLE': CONFIG['dynamodb_table_name']
                }
            }
        )
        
        print(f"✅ Lambda function '{CONFIG['lambda_function_name']}' created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error creating Lambda function: {str(e)}")
        return False

def update_lambda_function():
    """Update the Lambda function"""
    try:
        print(f"Updating Lambda function '{CONFIG['lambda_function_name']}'...")
        
        # Create a zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
            # Add the Lambda function code
            if os.path.exists(CONFIG['lambda_file']):
                zip_file.write(CONFIG['lambda_file'])
                print(f"✅ Added {CONFIG['lambda_file']} to deployment package")
            else:
                print(f"❌ Error: {CONFIG['lambda_file']} not found")
                return False
        
        # Get the zip file content
        zip_buffer.seek(0)
        zip_content = zip_buffer.read()
        
        # Update the Lambda function
        lambda_client = boto3.client('lambda')
        response = lambda_client.update_function_code(
            FunctionName=CONFIG['lambda_function_name'],
            ZipFile=zip_content,
            Publish=True
        )
        
        # Check if environment variables are set
        config_response = lambda_client.get_function_configuration(
            FunctionName=CONFIG['lambda_function_name']
        )
        
        env_vars = config_response.get('Environment', {}).get('Variables', {})
        
        if 'KNOWLEDGE_BASE_TABLE' not in env_vars:
            print("Adding environment variable for knowledge base table...")
            
            updated_vars = env_vars.copy()
            updated_vars['KNOWLEDGE_BASE_TABLE'] = CONFIG['dynamodb_table_name']
            
            lambda_client.update_function_configuration(
                FunctionName=CONFIG['lambda_function_name'],
                Environment={
                    'Variables': updated_vars
                }
            )
        
        print(f"✅ Lambda function '{CONFIG['lambda_function_name']}' updated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return False

def check_api_gateway():
    """Check if the API Gateway exists"""
    try:
        api_client = boto3.client('apigateway')
        response = api_client.get_rest_apis()
        
        for api in response.get('items', []):
            if api['name'] == CONFIG['api_gateway_name']:
                print(f"✅ API Gateway '{CONFIG['api_gateway_name']}' exists")
                return api['id']
        
        print(f"❌ API Gateway '{CONFIG['api_gateway_name']}' not found")
        return None
    except Exception as e:
        print(f"❌ Error checking API Gateway: {str(e)}")
        return None

def create_api_gateway():
    """Create the API Gateway"""
    try:
        print(f"Creating API Gateway '{CONFIG['api_gateway_name']}'...")
        
        api_client = boto3.client('apigateway')
        
        # Create the API
        api_response = api_client.create_rest_api(
            name=CONFIG['api_gateway_name'],
            description='API for S3 Autonomous Agent',
            endpointConfiguration={
                'types': ['REGIONAL']
            }
        )
        
        api_id = api_response['id']
        
        # Get the root resource ID
        resources_response = api_client.get_resources(
            restApiId=api_id
        )
        
        root_id = None
        for resource in resources_response['items']:
            if resource['path'] == '/':
                root_id = resource['id']
                break
        
        if not root_id:
            print("❌ Error: Could not find root resource")
            return None
        
        # Create a resource
        resource_response = api_client.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='s3agent'
        )
        
        resource_id = resource_response['id']
        
        # Create a POST method
        api_client.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='POST',
            authorizationType='NONE',
            apiKeyRequired=False
        )
        
        # Create a method response
        api_client.put_method_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='POST',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Origin': True
            },
            responseModels={
                'application/json': 'Empty'
            }
        )
        
        # Create an OPTIONS method for CORS
        api_client.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE',
            apiKeyRequired=False
        )
        
        # Create an OPTIONS method response
        api_client.put_method_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Origin': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Headers': True
            },
            responseModels={
                'application/json': 'Empty'
            }
        )
        
        # Create an OPTIONS integration
        api_client.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            integrationHttpMethod='OPTIONS',
            requestTemplates={
                'application/json': '{"statusCode": 200}'
            }
        )
        
        # Create an OPTIONS integration response
        api_client.put_integration_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Origin': "'*'",
                'method.response.header.Access-Control-Allow-Methods': "'POST,OPTIONS'",
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
            },
            responseTemplates={
                'application/json': ''
            }
        )
        
        # Get the Lambda function ARN
        lambda_client = boto3.client('lambda')
        lambda_response = lambda_client.get_function(
            FunctionName=CONFIG['lambda_function_name']
        )
        
        lambda_arn = lambda_response['Configuration']['FunctionArn']
        
        # Create a Lambda integration
        api_client.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='POST',
            type='AWS',
            integrationHttpMethod='POST',
            uri=f"arn:aws:apigateway:{boto3.session.Session().region_name}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations",
            requestTemplates={
                'application/json': '{\n  "body": $input.json("$")\n}'
            }
        )
        
        # Create an integration response
        api_client.put_integration_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='POST',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            },
            responseTemplates={
                'application/json': ''
            }
        )
        
        # Add permission for API Gateway to invoke Lambda
        region = boto3.session.Session().region_name
        account_id = boto3.client('sts').get_caller_identity()['Account']
        
        try:
            lambda_client.add_permission(
                FunctionName=CONFIG['lambda_function_name'],
                StatementId=f"apigateway-invoke-{int(time.time())}",
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f"arn:aws:execute-api:{region}:{account_id}:{api_id}/*/*/s3agent"
            )
        except lambda_client.exceptions.ResourceConflictException:
            print("Permission already exists, continuing...")
        
        # Deploy the API
        api_client.create_deployment(
            restApiId=api_id,
            stageName='prod',
            stageDescription='Production',
            description='Production deployment'
        )
        
        # Get the API URL
        api_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/prod/s3agent"
        
        print(f"✅ API Gateway '{CONFIG['api_gateway_name']}' created successfully")
        print(f"API URL: {api_url}")
        
        return api_url
        
    except Exception as e:
        print(f"❌ Error creating API Gateway: {str(e)}")
        return None

def update_html_file(api_url):
    """Update the HTML file with the API URL"""
    try:
        if not os.path.exists(CONFIG['html_file']):
            print(f"❌ HTML file '{CONFIG['html_file']}' not found")
            return False
        
        print(f"Updating HTML file '{CONFIG['html_file']}' with API URL...")
        
        with open(CONFIG['html_file'], 'r') as file:
            content = file.read()
        
        # Replace the API endpoint
        updated_content = content.replace(
            "const API_ENDPOINT = 'https://your-api-gateway-url.amazonaws.com/prod/s3agent';",
            f"const API_ENDPOINT = '{api_url}';"
        )
        
        with open(CONFIG['html_file'], 'w') as file:
            file.write(updated_content)
        
        print(f"✅ HTML file '{CONFIG['html_file']}' updated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error updating HTML file: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Setup S3 Autonomous Agent')
    parser.add_argument('--update', action='store_true', help='Update existing resources')
    args = parser.parse_args()
    
    print_header("S3 Autonomous Agent Setup")
    
    # Check AWS credentials
    print_step(1, "Checking AWS credentials")
    if not check_aws_credentials():
        sys.exit(1)
    
    # Check/create DynamoDB table
    print_step(2, "Checking DynamoDB table")
    if not check_dynamodb_table():
        if args.update or input("Create DynamoDB table? (y/n): ").lower() == 'y':
            if not create_dynamodb_table():
                sys.exit(1)
        else:
            sys.exit(1)
    
    # Seed knowledge base
    print_step(3, "Seeding knowledge base")
    if args.update or input("Seed knowledge base? (y/n): ").lower() == 'y':
        if not seed_knowledge_base():
            sys.exit(1)
    
    # Check/create Lambda function
    print_step(4, "Checking Lambda function")
    lambda_exists = check_lambda_function()
    
    if not lambda_exists:
        if args.update or input("Create Lambda function? (y/n): ").lower() == 'y':
            if not create_lambda_function():
                sys.exit(1)
        else:
            sys.exit(1)
    elif args.update or input("Update Lambda function? (y/n): ").lower() == 'y':
        if not update_lambda_function():
            sys.exit(1)
    
    # Check/create API Gateway
    print_step(5, "Checking API Gateway")
    api_id = check_api_gateway()
    
    if not api_id:
        if args.update or input("Create API Gateway? (y/n): ").lower() == 'y':
            api_url = create_api_gateway()
            if not api_url:
                sys.exit(1)
        else:
            sys.exit(1)
    else:
        region = boto3.session.Session().region_name
        api_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/prod/s3agent"
        print(f"API URL: {api_url}")
    
    # Update HTML file
    print_step(6, "Updating HTML file")
    if args.update or input("Update HTML file with API URL? (y/n): ").lower() == 'y':
        if not update_html_file(api_url):
            sys.exit(1)
    
    print_header("Setup Complete!")
    print(f"API URL: {api_url}")
    print(f"HTML Interface: {CONFIG['html_file']}")
    print("\nYou can now open the HTML file in your browser to use the S3 Autonomous Agent.")

if __name__ == "__main__":
    main()