# AWS Agentic AI Solution

An intelligent agent system that understands natural language requests for AWS operations, using a combination of a knowledge base and LLMs (Claude or Nova) for parsing and execution.

## Architecture Overview

The AWS Agent solution consists of the following components:

1. **Web Interface**: HTML/JS interface for user interaction
2. **API Gateway**: Handles HTTP and WebSocket requests to the Lambda functions
3. **Agent Orchestrator**: Central Lambda function that routes requests and manages sessions
4. **Service Handlers**: Specialized Lambda functions for different AWS services (S3, EC2, Lambda, etc.)
5. **Knowledge Base**: DynamoDB tables for storing command patterns, session state, and conversation history
6. **LLM Integration**: Amazon Bedrock integration for Claude or Nova models
7. **MCP Integration**: Optional interface with Model Context Protocol servers

## How It Works

1. User submits a natural language request (e.g., "list my buckets")
2. The request is sent to the Agent Orchestrator via API Gateway
3. The Orchestrator first checks the DynamoDB knowledge base for matching patterns
4. If a match is found and all required parameters are present, it routes to the appropriate service handler
5. If a match is found but parameters are missing, it asks the user for the missing information
6. If no match is found, it calls the LLM to parse the intent
7. The parsed intent is stored in the knowledge base for future reference
8. The command is executed and results are returned to the user

## Setup Instructions

### Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Python 3.8+ installed
- Bedrock access enabled in your AWS account

### Deployment

1. Clone this repository:

```bash
git clone https://github.com/yourusername/aws-agent.git
cd aws-agent
```

2. Run the deployment script:

```bash
python deploy_aws_agent.py --region us-east-1
```

Additional deployment options:

```bash
# Use a specific Bedrock model
python deploy_aws_agent.py --region us-east-1 --llm-model anthropic.claude-3-sonnet-20240229-v1:0

# Enable MCP integration
python deploy_aws_agent.py --region us-east-1 --use-mcp --mcp-endpoint https://your-mcp-endpoint.com

# Deploy to a specific VPC
python deploy_aws_agent.py --region us-east-1 --vpc-id vpc-12345678 --subnet-ids subnet-1234,subnet-5678
```

3. Open the generated `agent_interface_deployed.html` file in your browser to start using the agent.

### Deploying to a Customer VPC

To deploy the solution within a customer's VPC:

1. Use the `--vpc-id` and `--subnet-ids` parameters during deployment
2. Ensure the VPC has appropriate NAT Gateway or VPC Endpoints for AWS services
3. Configure security groups to allow necessary traffic
4. Package the solution as a CloudFormation template for easy deployment

## Extending the System

### Adding New Service Handlers

1. Create a new service handler Lambda function (e.g., `ec2_service_handler.py`)
2. Implement the necessary operations for the service
3. Update the deployment script to include the new handler
4. Add command patterns for the new service to the knowledge base

### Adding New Commands

1. Add new command patterns to the knowledge base using the format:

```python
{
    'intent_pattern': 'command pattern',
    'service': 'service_name',
    'action': 'action_name',
    'required_params': ['param1', 'param2'],
    'example_phrases': ['example phrase 1', 'example phrase 2'],
    'needs_followup': True/False,
    'followup_question': 'Question to ask if parameters are missing',
    'syntax_template': 'aws service action --param1 {param1} --param2 {param2}'
}
```

## Security Considerations

- The solution uses IAM roles with appropriate permissions
- All data is encrypted at rest and in transit
- Session isolation ensures user data is protected
- The solution can be deployed within a customer's VPC for additional security
- Consider implementing additional authentication mechanisms for production use

## Monitoring and Logging

- CloudWatch Logs are enabled for all Lambda functions
- Custom metrics can be added for monitoring agent performance
- X-Ray tracing can be enabled for request tracking

## Customization Options

- **UI Customization**: Modify the `agent_interface.html` file to match your branding
- **LLM Selection**: Choose between Claude and Nova models based on your requirements
- **Knowledge Base**: Pre-seed the knowledge base with common commands for your use case
- **MCP Integration**: Enable MCP integration for advanced capabilities

## Troubleshooting

- Check CloudWatch Logs for Lambda function errors
- Verify DynamoDB tables are properly seeded with command patterns
- Ensure Bedrock access is properly configured
- Test API Gateway endpoints directly to isolate issues

## License

This project is licensed under the MIT License - see the LICENSE file for details.