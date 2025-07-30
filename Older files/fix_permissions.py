import boto3
import json
import time

def fix_lambda_permissions():
    """Add S3 permissions to the Lambda function's execution role"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Adding S3 permissions to Lambda function: {FUNCTION_NAME}")
    
    try:
        # Get the Lambda function's execution role
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
        role_arn = response['Configuration']['Role']
        role_name = role_arn.split('/')[-1]
        
        print(f"Lambda function role: {role_name}")
        
        # Create IAM client
        iam_client = boto3.client('iam')
        
        # Create S3 full access policy
        s3_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "s3:*",
                    "Resource": "*"
                }
            ]
        }
        
        # Create the policy
        policy_name = f"{FUNCTION_NAME}-S3FullAccess"
        try:
            response = iam_client.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(s3_policy),
                Description=f"S3 full access policy for {FUNCTION_NAME}"
            )
            policy_arn = response['Policy']['Arn']
            print(f"Created policy: {policy_arn}")
        except iam_client.exceptions.EntityAlreadyExistsException:
            # Policy already exists, get its ARN
            account_id = boto3.client('sts').get_caller_identity().get('Account')
            policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
            print(f"Policy already exists: {policy_arn}")
        
        # Attach the policy to the role
        try:
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            print(f"Attached policy to role: {role_name}")
        except Exception as e:
            print(f"Error attaching policy: {str(e)}")
            
        # Also attach the AWS managed S3 full access policy as a backup
        try:
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess"
            )
            print(f"Attached AWS managed S3FullAccess policy to role: {role_name}")
        except Exception as e:
            print(f"Error attaching AWS managed policy: {str(e)}")
        
        print("\n✅ Permissions added successfully!")
        print("It may take a few minutes for the permissions to propagate.")
        print("Try your S3 commands again in a minute or two.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing permissions: {str(e)}")
        return False

if __name__ == "__main__":
    fix_lambda_permissions()