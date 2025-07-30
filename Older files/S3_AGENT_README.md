# S3 Autonomous Agent

An intelligent agent that understands natural language requests for AWS S3 operations, using a combination of a DynamoDB knowledge base and Amazon Bedrock's Nova Micro model for parsing.

## Architecture

The system consists of the following components:

1. **Frontend**: HTML/JS interface for user interaction
2. **API Gateway**: Handles HTTP requests to the Lambda function
3. **Lambda Function**: Core processing logic
4. **DynamoDB Knowledge Base**: Stores command patterns and required parameters
5. **Amazon Bedrock**: Provides access to Nova Micro for NLP parsing
6. **AWS S3**: The service being controlled by the agent

## How It Works

1. User submits a natural language request (e.g., "list my buckets")
2. The Lambda function first checks the DynamoDB knowledge base for matching patterns
3. If a match is found and all required parameters are present, it executes the command directly
4. If a match is found but parameters are missing, it asks the user for the missing information
5. If no match is found, it calls Nova Micro to parse the intent
6. The parsed intent is stored in the knowledge base for future reference
7. The command is executed and results are returned to the user

## Files in this Project

- `lambda_nova_parser_correct.py`: Main Lambda function with knowledge base integration
- `seed_s3_knowledge_base.py`: Script to create and seed the DynamoDB knowledge base
- `test_s3_knowledge_base.py`: Tool to test knowledge base queries
- `s3_agent_interface.html`: Frontend HTML interface
- `deploy_s3_agent.sh`: Deployment script

## Setup Instructions

### 1. Create DynamoDB Table and Seed Knowledge Base

```bash
python seed_s3_knowledge_base.py
```

### 2. Deploy Lambda Function

Edit `deploy_s3_agent.sh` with your AWS account details, then run:

```bash
chmod +x deploy_s3_agent.sh
./deploy_s3_agent.sh
```

### 3. Configure API Gateway

Create an API Gateway endpoint and connect it to your Lambda function.

### 4. Update Frontend

Edit `s3_agent_interface.html` and update the `API_ENDPOINT` variable with your API Gateway URL.

## Testing

Use the test script to verify knowledge base functionality:

```bash
# List all patterns
python test_s3_knowledge_base.py --list

# Test a specific query
python test_s3_knowledge_base.py --query "list my buckets"

# Interactive mode
python test_s3_knowledge_base.py
```

## Required IAM Permissions

The Lambda function needs permissions for:

- S3 (ListBuckets, ListObjects, CreateBucket, etc.)
- DynamoDB (GetItem, PutItem, Scan)
- Bedrock (InvokeModel)

## Example IAM Policy

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

## Extending the System

To add support for new S3 operations:

1. Add the operation pattern to `seed_s3_knowledge_base.py`
2. Implement the corresponding function in `execute_s3_command()`
3. Re-seed the knowledge base

To add support for other AWS services:

1. Add new service patterns to the knowledge base
2. Implement a new execution function (e.g., `execute_ec2_command()`)
3. Update the `execute_command()` function to route to the new service handler