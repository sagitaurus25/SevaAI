# S3 Agent Quick Setup Guide

This guide will help you quickly set up the S3 Autonomous Agent with DynamoDB knowledge base integration.

## Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.6+ with boto3 installed
- AWS account with access to Lambda, DynamoDB, API Gateway, and Bedrock

## Quick Setup

Run the quick setup script to create the IAM role and Lambda function:

```bash
python quick_setup.py
```

This script will:
1. Check AWS credentials
2. Create an IAM role with the necessary permissions
3. Create or update the Lambda function

## Manual Setup

If you prefer to set up the components manually:

### 1. Create IAM Role

```bash
python create_lambda_role.py
```

### 2. Create Lambda Function

```bash
python create_lambda_function.py
```

## Testing

After setting up the Lambda function, you can test the knowledge base:

```bash
python test_aws_knowledge_base.py --test
python test_aws_knowledge_base.py --list
```

## Next Steps

1. Create an API Gateway endpoint for the Lambda function
2. Update the HTML interface with the API Gateway URL
3. Test the S3 agent

## Troubleshooting

### Lambda Function Issues

If you encounter issues with the Lambda function:

1. Check the IAM role permissions
2. Make sure the Lambda function has the correct environment variables
3. Check the Lambda function logs in CloudWatch

### DynamoDB Issues

If you encounter issues with the DynamoDB table:

1. Make sure the table exists
2. Check the table name in the Lambda function environment variables
3. Test the knowledge base using `test_aws_knowledge_base.py`