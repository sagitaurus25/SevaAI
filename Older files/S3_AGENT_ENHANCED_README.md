# Enhanced S3 Autonomous Agent

An intelligent agent that understands natural language requests for AWS S3 operations, using a combination of a DynamoDB knowledge base and Amazon Bedrock's Nova Micro model for parsing. This enhanced version includes conversation history tracking.

## New Features

1. **Conversation History**: The agent now stores conversation history in DynamoDB, allowing it to reference past interactions.
2. **History Command**: Users can type "history" to see their recent conversation history.
3. **Improved UI**: The HTML interface now includes buttons for common actions and better message formatting.

## Architecture

The system consists of the following components:

1. **Frontend**: HTML/JS interface for user interaction
2. **API Gateway**: Handles HTTP requests to the Lambda function
3. **Lambda Function**: Core processing logic
4. **DynamoDB Knowledge Base**: Stores command patterns and required parameters
5. **DynamoDB Conversation History**: Stores user-agent interactions
6. **Amazon Bedrock**: Provides access to Nova Micro for NLP parsing
7. **AWS S3**: The service being controlled by the agent

## How It Works

1. User submits a natural language request (e.g., "list my buckets")
2. The Lambda function first checks the DynamoDB knowledge base for matching patterns
3. If a match is found and all required parameters are present, it executes the command directly
4. If a match is found but parameters are missing, it asks the user for the missing information
5. If no match is found, it calls Nova Micro to parse the intent
6. The parsed intent is stored in the knowledge base for future reference
7. The command is executed and results are returned to the user
8. The conversation is stored in the history table for future reference

## Files in this Project

- `lambda_with_history.py`: Updated Lambda function with conversation history support
- `conversation_history.py`: Module for managing conversation history in DynamoDB
- `setup_history_table.py`: Script to create and seed the conversation history table
- `s3_agent_with_history.html`: Enhanced HTML interface with history support
- `deploy_with_history.py`: Script to deploy the updated Lambda function

## Setup Instructions

### 1. Create DynamoDB Tables

```bash
# Create and seed the knowledge base table
python seed_s3_knowledge_base.py

# Create and seed the conversation history table
python setup_history_table.py
```

### 2. Deploy Lambda Function

```bash
python deploy_with_history.py
```

### 3. Update HTML Interface

Open `s3_agent_with_history.html` in your browser to use the enhanced interface.

## Using the Agent

The agent supports the following commands:

- **S3 Operations**:
  - `list buckets`: Show all S3 buckets
  - `list files in BUCKET`: Show objects in bucket
  - `create bucket NAME`: Create new bucket
  - `copy FILE from BUCKET1 to BUCKET2`: Copy between buckets
  - `delete FILE from BUCKET`: Delete object

- **System Commands**:
  - `help`: Show help message
  - `test`: Test connectivity to AWS services
  - `history`: Show recent conversation history

## Conversation History

The conversation history is stored in DynamoDB with the following attributes:

- `session_id`: Unique identifier for the conversation session
- `timestamp`: Timestamp of the message with role suffix for sorting
- `role`: Either "user" or "bot"
- `message`: The content of the message
- `ttl`: Time-to-live value for automatic expiration (30 days)

## Next Steps

Future enhancements could include:

1. **Multi-service Support**: Add support for EC2, RDS, and other AWS services
2. **Context-aware Responses**: Use conversation history to provide more contextual responses
3. **User Authentication**: Add user authentication to personalize the experience
4. **Analytics**: Track common queries and user satisfaction