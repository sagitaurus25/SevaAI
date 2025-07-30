#!/usr/bin/env python3
import boto3
import json
import os
import sys
import time
import zipfile
import io

# Configuration
CONFIG = {
    'lambda_function_name': 'SevaAI-S3Agent',
    'role_name': 'SevaAI-S3Agent-Role',
    'dynamodb_table_name': 'S3CommandKnowledgeBase',
    'lambda_file': 'lambda_nova_parser_correct.py'
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

def create_lambda_role():
    """Create an IAM role for the Lambda function"""
    
    print(f"Creating/checking IAM role: {CONFIG['role_name']}")
    
    # Define the trust policy for Lambda
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Define the permissions policy
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:*:*:*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket",
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListAllMyBuckets",
                    "s3:CreateBucket"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:Scan"
                ],
                "Resource": f"arn:aws:dynamodb:*:*:table/{CONFIG['dynamodb_table_name']}"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel"
                ],
                "Resource": "*"
            }
        ]
    }
    
    try:
        # Create the IAM client
        iam_client = boto3.client('iam')
        
        # Check if the role already exists
        try:
            response = iam_client.get_role(RoleName=CONFIG['role_name'])
            print(f"✅ IAM role '{CONFIG['role_name']}' already exists")
            return response['Role']['Arn']
        except iam_client.exceptions.NoSuchEntityException:
            # Role doesn't exist, create it
            pass
        
        # Create the role with the trust policy
        response = iam_client.create_role(
            RoleName=CONFIG['role_name'],
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for SevaAI S3 Agent Lambda function'
        )
        
        role_arn = response['Role']['Arn']
        
        # Create the policy
        policy_name = f"{CONFIG['role_name']}-Policy"
        policy_response = iam_client.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(permissions_policy),
            Description='Policy for SevaAI S3 Agent Lambda function'
        )
        
        policy_arn = policy_response['Policy']['Arn']
        
        # Attach the policy to the role
        iam_client.attach_role_policy(
            RoleName=CONFIG['role_name'],
            PolicyArn=policy_arn
        )
        
        # Wait for the role to be available
        print("Waiting for the role to be available (10 seconds)...")
        time.sleep(10)
        
        print(f"✅ IAM role '{CONFIG['role_name']}' created successfully")
        
        return role_arn
        
    except Exception as e:
        print(f"❌ Error creating IAM role: {str(e)}")
        return None

def create_lambda_function(role_arn):
    """Create the Lambda function with knowledge base integration"""
    
    print(f"Creating Lambda function: {CONFIG['lambda_function_name']}")
    
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
    try:
        lambda_client = boto3.client('lambda')
        
        # Check if the function already exists
        try:
            lambda_client.get_function(FunctionName=CONFIG['lambda_function_name'])
            print(f"Lambda function '{CONFIG['lambda_function_name']}' already exists, updating...")
            
            # Update the function code
            response = lambda_client.update_function_code(
                FunctionName=CONFIG['lambda_function_name'],
                ZipFile=zip_content,
                Publish=True
            )
            
            # Update the configuration
            lambda_client.update_function_configuration(
                FunctionName=CONFIG['lambda_function_name'],
                Role=role_arn,
                Environment={
                    'Variables': {
                        'KNOWLEDGE_BASE_TABLE': CONFIG['dynamodb_table_name']
                    }
                }
            )
            
            print(f"✅ Lambda function '{CONFIG['lambda_function_name']}' updated successfully")
            return True
            
        except lambda_client.exceptions.ResourceNotFoundException:
            # Function doesn't exist, create it
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
        print(f"❌ Error creating/updating Lambda function: {str(e)}")
        return False

def main():
    print_header("S3 Autonomous Agent Quick Setup")
    
    # Check AWS credentials
    print_step(1, "Checking AWS credentials")
    if not check_aws_credentials():
        sys.exit(1)
    
    # Create IAM role
    print_step(2, "Creating IAM role")
    role_arn = create_lambda_role()
    if not role_arn:
        sys.exit(1)
    
    # Create Lambda function
    print_step(3, "Creating Lambda function")
    if not create_lambda_function(role_arn):
        sys.exit(1)
    
    print_header("Setup Complete!")
    print("The Lambda function has been created/updated successfully.")
    print("\nNext steps:")
    print("1. Create an API Gateway endpoint for the Lambda function")
    print("2. Update the HTML interface with the API Gateway URL")
    print("3. Test the S3 agent")

if __name__ == "__main__":
    main()