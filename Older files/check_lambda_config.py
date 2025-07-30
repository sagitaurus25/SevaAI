import boto3
import json

def check_lambda_config(function_name):
    """Check the configuration of a Lambda function"""
    
    print(f"Checking configuration for Lambda function: {function_name}")
    print("-" * 80)
    
    try:
        # Create Lambda client
        lambda_client = boto3.client('lambda')
        
        # Get function configuration
        response = lambda_client.get_function(
            FunctionName=function_name
        )
        
        # Print basic information
        config = response['Configuration']
        print(f"Function Name: {config['FunctionName']}")
        print(f"Runtime: {config['Runtime']}")
        print(f"Handler: {config['Handler']}")
        print(f"Role: {config['Role']}")
        print(f"Timeout: {config['Timeout']} seconds")
        print(f"Memory Size: {config['MemorySize']} MB")
        
        # Print environment variables
        if 'Environment' in config and 'Variables' in config['Environment']:
            print("\nEnvironment Variables:")
            for key, value in config['Environment']['Variables'].items():
                print(f"  {key}: {value}")
        else:
            print("\nNo environment variables set")
        
        # Check for KNOWLEDGE_BASE_TABLE
        if 'Environment' not in config or 'Variables' not in config['Environment'] or 'KNOWLEDGE_BASE_TABLE' not in config['Environment']['Variables']:
            print("\n⚠️ WARNING: KNOWLEDGE_BASE_TABLE environment variable is not set")
            print("The Lambda function needs this variable to know which DynamoDB table to use")
            print("You can add it by updating the Lambda function configuration")
        
        # Print tags
        if 'Tags' in response:
            print("\nTags:")
            for key, value in response['Tags'].items():
                print(f"  {key}: {value}")
        
        # Check permissions
        print("\nChecking permissions...")
        
        # Get the role
        role_arn = config['Role']
        role_name = role_arn.split('/')[-1]
        
        iam_client = boto3.client('iam')
        
        try:
            # Get attached policies
            policies_response = iam_client.list_attached_role_policies(
                RoleName=role_name
            )
            
            print("\nAttached Policies:")
            for policy in policies_response['AttachedPolicies']:
                print(f"  {policy['PolicyName']}: {policy['PolicyArn']}")
                
                # Get policy details
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
                
                # Check for S3 permissions
                has_s3 = False
                has_dynamodb = False
                has_bedrock = False
                
                for statement in policy_document.get('Statement', []):
                    actions = statement.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    
                    for action in actions:
                        if action.startswith('s3:'):
                            has_s3 = True
                        elif action.startswith('dynamodb:'):
                            has_dynamodb = True
                        elif action.startswith('bedrock:'):
                            has_bedrock = True
            
            # Get inline policies
            inline_policies_response = iam_client.list_role_policies(
                RoleName=role_name
            )
            
            print("\nInline Policies:")
            for policy_name in inline_policies_response['PolicyNames']:
                print(f"  {policy_name}")
                
                # Get policy details
                policy_response = iam_client.get_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
                
                # Check for required permissions
                policy_document = policy_response['PolicyDocument']
                
                # Check for S3 permissions
                for statement in policy_document.get('Statement', []):
                    actions = statement.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    
                    for action in actions:
                        if action.startswith('s3:'):
                            has_s3 = True
                        elif action.startswith('dynamodb:'):
                            has_dynamodb = True
                        elif action.startswith('bedrock:'):
                            has_bedrock = True
            
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
            
        except Exception as e:
            print(f"Error checking permissions: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"Error checking Lambda configuration: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Check Lambda function configuration')
    parser.add_argument('--function', '-f', default='SevaAI-S3Agent', help='Lambda function name')
    
    args = parser.parse_args()
    
    check_lambda_config(args.function)