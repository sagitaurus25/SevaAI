import boto3
import json
import time

def create_lambda_role():
    """Create an IAM role for the Lambda function"""
    
    # Role name
    ROLE_NAME = 'SevaAI-S3Agent-Role'
    
    print(f"Creating IAM role: {ROLE_NAME}")
    
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
                "Resource": "arn:aws:dynamodb:*:*:table/S3CommandKnowledgeBase"
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
            response = iam_client.get_role(RoleName=ROLE_NAME)
            print(f"✅ IAM role '{ROLE_NAME}' already exists")
            return response['Role']['Arn']
        except iam_client.exceptions.NoSuchEntityException:
            # Role doesn't exist, create it
            pass
        
        # Create the role with the trust policy
        response = iam_client.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for SevaAI S3 Agent Lambda function'
        )
        
        role_arn = response['Role']['Arn']
        
        # Create the policy
        policy_name = f"{ROLE_NAME}-Policy"
        policy_response = iam_client.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(permissions_policy),
            Description='Policy for SevaAI S3 Agent Lambda function'
        )
        
        policy_arn = policy_response['Policy']['Arn']
        
        # Attach the policy to the role
        iam_client.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn=policy_arn
        )
        
        # Wait for the role to be available
        print("Waiting for the role to be available (10 seconds)...")
        time.sleep(10)
        
        print(f"✅ IAM role '{ROLE_NAME}' created successfully")
        print(f"Role ARN: {role_arn}")
        
        return role_arn
        
    except Exception as e:
        print(f"❌ Error creating IAM role: {str(e)}")
        return None

if __name__ == "__main__":
    role_arn = create_lambda_role()
    if role_arn:
        print(f"\nUse this Role ARN when creating the Lambda function:")
        print(f"{role_arn}")