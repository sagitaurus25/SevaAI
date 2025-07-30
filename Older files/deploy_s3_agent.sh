#!/bin/bash

# S3 Agent Deployment Script
echo "Deploying S3 Autonomous Agent..."

# Create DynamoDB table and seed knowledge base
echo "Creating and seeding knowledge base..."
python seed_s3_knowledge_base.py

# Create deployment package
echo "Creating deployment package..."
zip -r s3_agent.zip lambda_nova_parser_correct.py

# Deploy Lambda function
# Uncomment and modify the following lines with your AWS account details
# echo "Deploying Lambda function..."
# aws lambda create-function \
#   --function-name S3Agent \
#   --runtime python3.9 \
#   --handler lambda_nova_parser_correct.lambda_handler \
#   --zip-file fileb://s3_agent.zip \
#   --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-s3-dynamodb-bedrock-role \
#   --timeout 30 \
#   --memory-size 256

# Or update existing Lambda function
# aws lambda update-function-code \
#   --function-name S3Agent \
#   --zip-file fileb://s3_agent.zip

echo "Deployment complete!"
echo "Don't forget to update the API_ENDPOINT in s3_agent_interface.html with your API Gateway URL."