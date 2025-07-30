# S3 Autonomous Agent Setup Guide

This guide will help you set up the S3 Autonomous Agent with DynamoDB knowledge base integration.

## Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.6+ with boto3 installed
- AWS account with access to Lambda, DynamoDB, API Gateway, and Bedrock

## Files

- `lambda_nova_parser_correct.py`: Main Lambda function with knowledge base integration
- `seed_s3_knowledge_base.py`: Script to seed the DynamoDB knowledge base
- `test_aws_knowledge_base.py`: Script to test the DynamoDB knowledge base
- `update_lambda_function.py`: Script to update the Lambda function
- `test_s3_agent_api.py`: Script to test the S3 agent API
- `setup_s3_agent.py`: Comprehensive setup script
- `s3_agent_interface.html`: HTML interface for the S3 agent

## Quick Setup

The easiest way to set up the S3 agent is to use the comprehensive setup script:

```bash
python setup_s3_agent.py
```

This script will:
1. Check AWS credentials
2. Create/check the DynamoDB table
3. Seed the knowledge base
4. Create/update the Lambda function
5. Create/check the API Gateway
6. Update the HTML file with the API URL

## Manual Setup

If you prefer to set up the components manually, follow these steps:

### 1. Create and Seed DynamoDB Table

```bash
python seed_s3_knowledge_base.py
```

### 2. Test the Knowledge Base

```bash
python test_aws_knowledge_base.py --test
python test_aws_knowledge_base.py --list
python test_aws_knowledge_base.py --query "list buckets"
```

### 3. Update Lambda Function

```bash
python update_lambda_function.py
```

### 4. Test the API

Update the API endpoint in `test_s3_agent_api.py` and run:

```bash
python test_s3_agent_api.py --message "list buckets"
```

Or use interactive mode:

```bash
python test_s3_agent_api.py
```

### 5. Update HTML Interface

Update the API endpoint in `s3_agent_interface.html` and open it in a web browser.

## Updating Existing Resources

To update existing resources, use the `--update` flag with the setup script:

```bash
python setup_s3_agent.py --update
```

## Troubleshooting

### DynamoDB Issues

If you encounter issues with the DynamoDB table:

```bash
python test_aws_knowledge_base.py --test
```

### Lambda Function Issues

Check the Lambda function logs in CloudWatch.

### API Gateway Issues

Test the API directly:

```bash
curl -X POST -H "Content-Type: application/json" -d '{"message":"list buckets","session_id":"test"}' https://your-api-gateway-url.amazonaws.com/prod/s3agent
```

## IAM Permissions

The Lambda function needs these permissions:

- S3 (ListBuckets, ListObjects, CreateBucket, etc.)
- DynamoDB (GetItem, PutItem, Scan)
- Bedrock (InvokeModel)

Example policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
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
```