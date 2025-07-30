import boto3
import json

def add_inline_policy():
    """Add an inline policy directly to the Lambda role"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Adding inline S3 policy to Lambda function: {FUNCTION_NAME}")
    
    try:
        # Get the Lambda function's execution role
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
        role_arn = response['Configuration']['Role']
        role_name = role_arn.split('/')[-1]
        
        print(f"Lambda function role: {role_name}")
        
        # Create IAM client
        iam_client = boto3.client('iam')
        
        # Create inline policy with full S3 access
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "s3:*",
                    "Resource": "*"
                }
            ]
        }
        
        # Put the inline policy
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='S3FullAccessInline',
            PolicyDocument=json.dumps(policy_document)
        )
        
        print(f"✅ Added inline policy to role: {role_name}")
        print("It may take a few minutes for the permissions to propagate.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding inline policy: {str(e)}")
        return False

if __name__ == "__main__":
    add_inline_policy()