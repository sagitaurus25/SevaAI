# S3 Workflow Agent

An intelligent agent that understands natural language requests for AWS S3 operations and complex workflows, using a combination of a knowledge base and LLM (Claude Sonnet or Nova Micro) for parsing.

## Architecture

The system consists of the following components:

1. **Frontend**: HTML/JS interface for user interaction
2. **API Gateway**: Handles HTTP requests to the Lambda function
3. **Lambda Function**: Core processing logic
4. **DynamoDB Knowledge Base**: Stores command patterns and required parameters
5. **DynamoDB Workflow Definitions**: Stores workflow definitions and parameters
6. **DynamoDB Workflow Executions**: Tracks workflow execution status
7. **Step Functions**: Orchestrates complex workflow execution
8. **Lambda Functions**: Implement individual workflow steps
9. **Amazon Bedrock**: Provides access to Nova Micro for NLP parsing
10. **AWS S3**: The primary service being controlled by the agent
11. **CloudWatch**: For logging and monitoring

## Supported Workflows

### 1. Inventory Reports Workflow
- Configure S3 inventory
- Set appropriate output format (CSV/ORC)
- Schedule weekly frequency

### 2. Log Analysis Workflow
- Query CloudWatch logs for error entries
- Group by error type and frequency
- Generate summary statistics
- Present actionable insights

### 3. Lifecycle Management Workflow
- Create lifecycle configuration
- Set transition rules to Glacier after 30 days
- Configure expiration after 365 days
- Apply to log file prefixes

## How It Works

1. User submits a natural language request (e.g., "run inventory report for my-bucket")
2. The Lambda function first checks the DynamoDB knowledge base for matching patterns
3. If a match is found and all required parameters are present, it executes the command directly
4. If a match is found but parameters are missing, it asks the user for the missing information
5. If no match is found, it calls Nova Micro to parse the intent
6. For workflow requests, it retrieves the workflow definition and starts a Step Functions execution
7. Step Functions orchestrates the workflow by calling the appropriate Lambda functions
8. The workflow status is tracked in DynamoDB and can be queried by the user
9. Results are returned to the user through the chat interface

## Cost Optimization

This architecture is designed to be cost-effective:

1. **Serverless Architecture**: Pay only for what you use, with no idle resources
2. **DynamoDB On-Demand Capacity**: Scales automatically with usage
3. **Lambda Functions**: Minimal compute time for individual workflow steps
4. **Step Functions Express Workflows**: Cost-effective for short-lived workflows
5. **Nova Micro**: Lower cost LLM for intent parsing
6. **Knowledge Base Caching**: Reduces LLM calls for common patterns

## Setup Instructions

### 1. Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.8+ installed
- Boto3 library installed

### 2. Deploy the Solution

Run the setup script to deploy the entire solution:

```bash
python setup_workflow_agent.py --region us-east-1
```

This script will:
- Create necessary IAM roles
- Create DynamoDB tables
- Seed the knowledge base and workflow definitions
- Deploy Lambda functions
- Create Step Functions state machines
- Set up API Gateway
- Update the frontend with the API URL

### 3. Access the Interface

Open `s3_agent_workflow_interface.html` in your web browser to interact with the agent.

## Using the Agent

### Basic S3 Commands

- `list buckets` - Show all S3 buckets
- `list files in BUCKET` - Show objects in bucket
- `create bucket NAME` - Create new bucket
- `copy FILE from BUCKET1 to BUCKET2` - Copy between buckets
- `delete FILE from BUCKET` - Delete object

### Workflow Commands

- `list workflows` - Show available workflows
- `run inventory report workflow for my-bucket` - Execute the inventory report workflow
- `workflow status EXECUTION_ID` - Check the status of a workflow execution

## Extending the System

### Adding New Workflows

1. Add the workflow definition to `workflow_schema.py`
2. Implement the workflow steps in `workflow_lambdas.py`
3. Update the frontend to display the new workflow

### Adding New S3 Operations

1. Add the operation pattern to `seed_knowledge_base.py`
2. Implement the corresponding function in `execute_s3_command()`
3. Re-seed the knowledge base

### Adding Support for Other AWS Services

1. Add new service patterns to the knowledge base
2. Implement a new execution function (e.g., `execute_ec2_command()`)
3. Update the `execute_command()` function to route to the new service handler

## Troubleshooting

If you encounter issues:

1. Check CloudWatch Logs for Lambda function errors
2. Verify IAM permissions are correctly set up
3. Ensure DynamoDB tables are properly seeded
4. Check Step Functions execution history for workflow errors

## Security Considerations

- The agent uses IAM roles with least privilege principles
- API Gateway can be configured with authentication
- Consider encrypting sensitive data in DynamoDB
- Implement VPC endpoints for enhanced security

## Future Enhancements

- Add support for more AWS services (EC2, RDS, etc.)
- Implement more complex workflows
- Add user authentication and multi-user support
- Enhance the UI with workflow visualization
- Implement conversation history and context awareness