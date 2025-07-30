# S3 Autonomous Agent

An intelligent agent that understands natural language requests for AWS S3 operations, using a combination of a knowledge base and LLM (Claude Sonnet or Nova Micro) for parsing.

## Architecture

![Architecture Diagram](https://via.placeholder.com/800x400?text=S3+Agent+Architecture)

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

## Knowledge Base Structure

The DynamoDB table stores command patterns with the following attributes:

- `intent_pattern`: Primary key, the simplified command pattern
- `service`: AWS service (e.g., "s3")
- `action`: Specific action to perform (e.g., "list_buckets")
- `required_params`: List of required parameters for the action
- `example_phrases`: Sample phrases that match this pattern
- `needs_followup`: Boolean indicating if additional information is needed
- `followup_question`: Question to ask the user if information is missing
- `syntax_template`: Template showing the correct syntax for the command

## Setup Instructions

### 1. Create DynamoDB Table

Run the seed script to create and populate the knowledge base:

```bash
python seed_knowledge_base.py
```

### 2. Deploy Lambda Function

Package and deploy the Lambda function:

```bash
zip -r s3_agent.zip s3_agent_lambda.py
aws lambda create-function --function-name S3Agent \
  --runtime python3.9 --handler s3_agent_lambda.lambda_handler \
  --zip-file fileb://s3_agent.zip \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-s3-dynamodb-bedrock-role
```

### 3. Configure API Gateway

Create an API Gateway endpoint and connect it to your Lambda function.

### 4. Update Frontend

Update the API endpoint in your HTML/JS frontend.

## Required IAM Permissions

The Lambda function needs permissions for:

- S3 (ListBuckets, ListObjects, CreateBucket, etc.)
- DynamoDB (GetItem, PutItem, Scan)
- Bedrock (InvokeModel)

## Testing

Use the test script to verify knowledge base functionality:

```bash
# List all patterns
python test_knowledge_base.py --list

# Test a specific query
python test_knowledge_base.py --query "list my buckets"

# Interactive mode
python test_knowledge_base.py
```

## Extending the System

To add support for new S3 operations:

1. Add the operation pattern to `seed_knowledge_base.py`
2. Implement the corresponding function in `execute_s3_command()`
3. Re-seed the knowledge base

To add support for other AWS services:

1. Add new service patterns to the knowledge base
2. Implement a new execution function (e.g., `execute_ec2_command()`)
3. Update the `execute_command()` function to route to the new service handler