#!/usr/bin/env python3
import boto3
import json
import argparse
import sys
import requests
from decimal import Decimal
import time

# Configuration
CONFIG = {
    'lambda_function_name': 'SevaAI-S3Agent',
    'dynamodb_table_name': 'S3CommandKnowledgeBase',
    'api_endpoint': 'https://1jbk6z92h3.execute-api.us-east-1.amazonaws.com/prod/s3agent'
}

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

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
    """Check the DynamoDB table and its contents"""
    
    print(f"Checking DynamoDB table: {CONFIG['dynamodb_table_name']}")
    
    try:
        # Create DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        
        # Check if table exists
        try:
            table = dynamodb.Table(CONFIG['dynamodb_table_name'])
            table.load()
            print(f"✅ Table '{CONFIG['dynamodb_table_name']}' exists")
            
            # Print table details
            print(f"Status: {table.table_status}")
            print(f"Item Count: {table.item_count}")
            
            # Scan the table
            response = table.scan()
            items = response.get('Items', [])
            
            print(f"Found {len(items)} items")
            
            if len(items) == 0:
                print("\n⚠️ WARNING: Table is empty")
                print("The knowledge base needs to be seeded with S3 command patterns")
                print("Run the seed_s3_knowledge_base.py script to populate the table")
                return False
            
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
                return False
            
            return True
            
        except dynamodb.meta.client.exceptions.ResourceNotFoundException:
            print(f"❌ Table '{CONFIG['dynamodb_table_name']}' does not exist")
            print("You need to create the table and seed it with S3 command patterns")
            print("Run the seed_s3_knowledge_base.py script to create and populate the table")
            return False
            
    except Exception as e:
        print(f"Error checking DynamoDB table: {str(e)}")
        return False

def check_lambda_function():
    """Check the Lambda function configuration"""
    
    print(f"Checking Lambda function: {CONFIG['lambda_function_name']}")
    
    try:
        # Create Lambda client
        lambda_client = boto3.client('lambda')
        
        # Get function configuration
        try:
            response = lambda_client.get_function(
                FunctionName=CONFIG['lambda_function_name']
            )
            
            # Print basic information
            config = response['Configuration']
            print(f"✅ Function '{CONFIG['lambda_function_name']}' exists")
            print(f"Runtime: {config['Runtime']}")
            print(f"Handler: {config['Handler']}")
            
            # Check handler
            if config['Handler'] != 'lambda_nova_parser_correct.lambda_handler':
                print(f"\n⚠️ WARNING: Handler is set to '{config['Handler']}'")
                print("Expected: 'lambda_nova_parser_correct.lambda_handler'")
                print("The handler should match the filename and function name in your Lambda code")
            
            # Check environment variables
            if 'Environment' in config and 'Variables' in config['Environment']:
                env_vars = config['Environment']['Variables']
                if 'KNOWLEDGE_BASE_TABLE' in env_vars:
                    print(f"✅ KNOWLEDGE_BASE_TABLE environment variable is set to: {env_vars['KNOWLEDGE_BASE_TABLE']}")
                    
                    # Check if it matches the expected table name
                    if env_vars['KNOWLEDGE_BASE_TABLE'] != CONFIG['dynamodb_table_name']:
                        print(f"\n⚠️ WARNING: KNOWLEDGE_BASE_TABLE is set to '{env_vars['KNOWLEDGE_BASE_TABLE']}'")
                        print(f"Expected: '{CONFIG['dynamodb_table_name']}'")
                        print("The environment variable should match the DynamoDB table name")
                else:
                    print("❌ KNOWLEDGE_BASE_TABLE environment variable is not set")
                    print("The Lambda function needs this variable to know which DynamoDB table to use")
                    return False
            else:
                print("❌ No environment variables set")
                print("The Lambda function needs the KNOWLEDGE_BASE_TABLE environment variable")
                return False
            
            # Check timeout
            if config['Timeout'] < 10:
                print(f"\n⚠️ WARNING: Timeout is set to {config['Timeout']} seconds")
                print("Recommended: At least 10 seconds")
                print("The Lambda function might time out when calling Bedrock")
            
            return True
            
        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"❌ Function '{CONFIG['lambda_function_name']}' does not exist")
            print("You need to create the Lambda function")
            return False
            
    except Exception as e:
        print(f"Error checking Lambda function: {str(e)}")
        return False

def check_lambda_permissions():
    """Check the Lambda function permissions"""
    
    print(f"Checking Lambda function permissions")
    
    try:
        # Create Lambda client
        lambda_client = boto3.client('lambda')
        
        # Get function configuration
        try:
            response = lambda_client.get_function(
                FunctionName=CONFIG['lambda_function_name']
            )
            
            # Get the role
            role_arn = response['Configuration']['Role']
            role_name = role_arn.split('/')[-1]
            
            print(f"Role: {role_name}")
            
            # Create IAM client
            iam_client = boto3.client('iam')
            
            # Check permissions
            has_s3 = False
            has_dynamodb = False
            has_bedrock = False
            
            # Check attached policies
            try:
                policies_response = iam_client.list_attached_role_policies(
                    RoleName=role_name
                )
                
                print("\nAttached Policies:")
                for policy in policies_response['AttachedPolicies']:
                    print(f"  {policy['PolicyName']}")
                    
                    # Check for AWS managed policies
                    if policy['PolicyName'] in ['AmazonS3FullAccess', 'AmazonS3ReadOnlyAccess']:
                        has_s3 = True
                    elif policy['PolicyName'] in ['AmazonDynamoDBFullAccess', 'AmazonDynamoDBReadOnlyAccess']:
                        has_dynamodb = True
                    
                    # Get policy details for custom policies
                    try:
                        policy_response = iam_client.get_policy(
                            PolicyArn=policy['PolicyArn']
                        )
                        
                        # Get policy version details
                        version_response = iam_client.get_policy_version(
                            PolicyArn=policy['PolicyArn'],
                            VersionId=policy_response['Policy']['DefaultVersionId']
                        )
                        
                        # Check for required permissions
                        policy_document = version_response['PolicyVersion']['Document']
                        
                        for statement in policy_document.get('Statement', []):
                            actions = statement.get('Action', [])
                            if isinstance(actions, str):
                                actions = [actions]
                            
                            for action in actions:
                                if isinstance(action, str):
                                    if action.startswith('s3:') or action == 's3:*':
                                        has_s3 = True
                                    elif action.startswith('dynamodb:') or action == 'dynamodb:*':
                                        has_dynamodb = True
                                    elif action.startswith('bedrock:') or action == 'bedrock:*':
                                        has_bedrock = True
                    except Exception as e:
                        print(f"  Error checking policy details: {str(e)}")
                
                # Check inline policies
                inline_policies_response = iam_client.list_role_policies(
                    RoleName=role_name
                )
                
                if inline_policies_response['PolicyNames']:
                    print("\nInline Policies:")
                    for policy_name in inline_policies_response['PolicyNames']:
                        print(f"  {policy_name}")
                        
                        # Get policy details
                        try:
                            policy_response = iam_client.get_role_policy(
                                RoleName=role_name,
                                PolicyName=policy_name
                            )
                            
                            # Check for required permissions
                            policy_document = policy_response['PolicyDocument']
                            
                            for statement in policy_document.get('Statement', []):
                                actions = statement.get('Action', [])
                                if isinstance(actions, str):
                                    actions = [actions]
                                
                                for action in actions:
                                    if isinstance(action, str):
                                        if action.startswith('s3:') or action == 's3:*':
                                            has_s3 = True
                                        elif action.startswith('dynamodb:') or action == 'dynamodb:*':
                                            has_dynamodb = True
                                        elif action.startswith('bedrock:') or action == 'bedrock:*':
                                            has_bedrock = True
                        except Exception as e:
                            print(f"  Error checking inline policy details: {str(e)}")
                
                print("\nPermission Summary:")
                print(f"  S3 Permissions: {'✅ Yes' if has_s3 else '❌ No'}")
                print(f"  DynamoDB Permissions: {'✅ Yes' if has_dynamodb else '❌ No'}")
                print(f"  Bedrock Permissions: {'✅ Yes' if has_bedrock else '❌ No'}")
                
                if not has_s3:
                    print("\n⚠️ WARNING: Lambda function does not have S3 permissions")
                    print("The function needs S3 permissions to list buckets, objects, etc.")
                
                if not has_dynamodb:
                    print("\n⚠️ WARNING: Lambda function does not have DynamoDB permissions")
                    print("The function needs DynamoDB permissions to access the knowledge base")
                
                if not has_bedrock:
                    print("\n⚠️ WARNING: Lambda function does not have Bedrock permissions")
                    print("The function needs Bedrock permissions to use Nova Micro")
                
                return has_s3 and has_dynamodb and has_bedrock
                
            except Exception as e:
                print(f"Error checking role policies: {str(e)}")
                return False
            
        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"❌ Function '{CONFIG['lambda_function_name']}' does not exist")
            return False
            
    except Exception as e:
        print(f"Error checking Lambda permissions: {str(e)}")
        return False

def check_api_endpoint():
    """Check the API endpoint"""
    
    print(f"Checking API endpoint: {CONFIG['api_endpoint']}")
    
    try:
        # Send a simple request
        response = requests.post(
            CONFIG['api_endpoint'],
            headers={
                'Content-Type': 'application/json'
            },
            json={
                'message': 'help',
                'session_id': 'test-session'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ API endpoint is accessible (Status: {response.status_code})")
            
            # Check response format
            try:
                data = response.json()
                if 'response' in data:
                    print("✅ API response format is correct")
                    print(f"Response: {data['response'][:100]}...")
                    return True
                else:
                    print("❌ API response format is incorrect")
                    print(f"Expected 'response' field, got: {json.dumps(data)[:100]}...")
                    return False
            except Exception as e:
                print(f"❌ Error parsing API response: {str(e)}")
                print(f"Response: {response.text[:100]}...")
                return False
        else:
            print(f"❌ API endpoint returned status code {response.status_code}")
            print(f"Response: {response.text[:100]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing API endpoint: {str(e)}")
        return False

def test_s3_command(command):
    """Test a specific S3 command"""
    
    print(f"Testing S3 command: '{command}'")
    
    try:
        # Send the command to the API
        response = requests.post(
            CONFIG['api_endpoint'],
            headers={
                'Content-Type': 'application/json'
            },
            json={
                'message': command,
                'session_id': 'test-session'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ Command sent successfully (Status: {response.status_code})")
            
            # Check response
            try:
                data = response.json()
                if 'response' in data:
                    print(f"Response: {data['response']}")
                    return True
                else:
                    print(f"❌ API response format is incorrect")
                    print(f"Expected 'response' field, got: {json.dumps(data)}")
                    return False
            except Exception as e:
                print(f"❌ Error parsing API response: {str(e)}")
                print(f"Response: {response.text}")
                return False
        else:
            print(f"❌ API endpoint returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing API endpoint: {str(e)}")
        return False

def check_lambda_logs():
    """Check CloudWatch logs for the Lambda function"""
    
    print(f"Checking CloudWatch logs for Lambda function: {CONFIG['lambda_function_name']}")
    
    try:
        # Create CloudWatch Logs client
        logs_client = boto3.client('logs')
        
        # Get the log group name for the Lambda function
        log_group_name = f"/aws/lambda/{CONFIG['lambda_function_name']}"
        
        # Calculate the start time (10 minutes ago)
        start_time = int((time.time() - 600) * 1000)
        end_time = int(time.time() * 1000)
        
        # Get log streams
        try:
            response = logs_client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=5
            )
            
            if not response.get('logStreams'):
                print(f"No log streams found for {log_group_name}")
                return False
            
            # Get logs from the most recent stream
            stream = response['logStreams'][0]
            stream_name = stream['logStreamName']
            print(f"\nMost recent log stream: {stream_name}")
            
            try:
                log_events = logs_client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=stream_name,
                    startTime=start_time,
                    endTime=end_time,
                    limit=20
                )
                
                if not log_events['events']:
                    print("No log events found in this stream for the last 10 minutes")
                    return False
                
                print("\nRecent log events:")
                for event in log_events['events']:
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event['timestamp'] / 1000))
                    message = event['message']
                    print(f"{timestamp}: {message}")
                
                # Check for common errors
                errors = []
                for event in log_events['events']:
                    message = event['message'].lower()
                    if 'error' in message or 'exception' in message:
                        errors.append(event['message'])
                
                if errors:
                    print("\n⚠️ WARNING: Found errors in the logs:")
                    for error in errors:
                        print(f"  {error}")
                    return False
                
                return True
                
            except Exception as e:
                print(f"Error getting logs for stream {stream_name}: {str(e)}")
                return False
                
        except logs_client.exceptions.ResourceNotFoundException:
            print(f"❌ Log group '{log_group_name}' does not exist")
            print("The Lambda function might not have been invoked yet")
            return False
            
    except Exception as e:
        print(f"Error checking CloudWatch logs: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Troubleshoot S3 Agent')
    parser.add_argument('--function', '-f', help='Lambda function name')
    parser.add_argument('--table', '-t', help='DynamoDB table name')
    parser.add_argument('--endpoint', '-e', help='API endpoint URL')
    parser.add_argument('--test', action='store_true', help='Test S3 commands')
    
    args = parser.parse_args()
    
    # Update configuration if provided
    if args.function:
        CONFIG['lambda_function_name'] = args.function
    if args.table:
        CONFIG['dynamodb_table_name'] = args.table
    if args.endpoint:
        CONFIG['api_endpoint'] = args.endpoint
    
    print_header("S3 Agent Troubleshooting")
    
    # Check AWS credentials
    print_step(1, "Checking AWS credentials")
    if not check_aws_credentials():
        sys.exit(1)
    
    # Check DynamoDB table
    print_step(2, "Checking DynamoDB table")
    dynamodb_ok = check_dynamodb_table()
    
    # Check Lambda function
    print_step(3, "Checking Lambda function")
    lambda_ok = check_lambda_function()
    
    # Check Lambda permissions
    print_step(4, "Checking Lambda permissions")
    permissions_ok = check_lambda_permissions()
    
    # Check API endpoint
    print_step(5, "Checking API endpoint")
    api_ok = check_api_endpoint()
    
    # Check Lambda logs
    print_step(6, "Checking Lambda logs")
    logs_ok = check_lambda_logs()
    
    # Test S3 commands
    if args.test:
        print_step(7, "Testing S3 commands")
        test_s3_command("list buckets")
        test_s3_command("list files")
        test_s3_command("help")
    
    # Print summary
    print_header("Troubleshooting Summary")
    print(f"DynamoDB Table: {'✅ OK' if dynamodb_ok else '❌ Issues found'}")
    print(f"Lambda Function: {'✅ OK' if lambda_ok else '❌ Issues found'}")
    print(f"Lambda Permissions: {'✅ OK' if permissions_ok else '❌ Issues found'}")
    print(f"API Endpoint: {'✅ OK' if api_ok else '❌ Issues found'}")
    print(f"Lambda Logs: {'✅ OK' if logs_ok else '❌ Issues found'}")
    
    if not (dynamodb_ok and lambda_ok and permissions_ok and api_ok):
        print("\n⚠️ Issues were found that need to be addressed")
        
        if not dynamodb_ok:
            print("\nDynamoDB Issues:")
            print("1. Make sure the table exists")
            print("2. Make sure the table is seeded with S3 command patterns")
            print("3. Run the seed_s3_knowledge_base.py script to create and populate the table")
        
        if not lambda_ok:
            print("\nLambda Function Issues:")
            print("1. Make sure the Lambda function exists")
            print("2. Make sure the handler is set to 'lambda_nova_parser_correct.lambda_handler'")
            print("3. Make sure the KNOWLEDGE_BASE_TABLE environment variable is set")
        
        if not permissions_ok:
            print("\nLambda Permissions Issues:")
            print("1. Make sure the Lambda function has S3 permissions")
            print("2. Make sure the Lambda function has DynamoDB permissions")
            print("3. Make sure the Lambda function has Bedrock permissions")
        
        if not api_ok:
            print("\nAPI Endpoint Issues:")
            print("1. Make sure the API Gateway is configured correctly")
            print("2. Make sure the API Gateway is integrated with the Lambda function")
            print("3. Make sure CORS is enabled")
    else:
        print("\n✅ All checks passed!")
        print("If you're still experiencing issues, check the Lambda logs for more details")

if __name__ == "__main__":
    main()