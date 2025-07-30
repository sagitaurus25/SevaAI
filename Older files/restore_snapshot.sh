#!/bin/bash

# Restore all Lambda functions to Version 1 (working snapshot)
echo "🔄 Restoring all Lambda functions to Version 1..."

# Update function configurations to point to Version 1
aws lambda update-alias --function-name aws-agent-executor --name LIVE --function-version 1 2>/dev/null || \
aws lambda create-alias --function-name aws-agent-executor --name LIVE --function-version 1

aws lambda update-alias --function-name aws-agent-s3-service --name LIVE --function-version 1 2>/dev/null || \
aws lambda create-alias --function-name aws-agent-s3-service --name LIVE --function-version 1

aws lambda update-alias --function-name aws-agent-ec2-service --name LIVE --function-version 1 2>/dev/null || \
aws lambda create-alias --function-name aws-agent-ec2-service --name LIVE --function-version 1

aws lambda update-alias --function-name aws-agent-lambda-service --name LIVE --function-version 1 2>/dev/null || \
aws lambda create-alias --function-name aws-agent-lambda-service --name LIVE --function-version 1

aws lambda update-alias --function-name aws-agent-iam-service --name LIVE --function-version 1 2>/dev/null || \
aws lambda create-alias --function-name aws-agent-iam-service --name LIVE --function-version 1

aws lambda update-alias --function-name aws-agent-cloudwatch-service --name LIVE --function-version 1 2>/dev/null || \
aws lambda create-alias --function-name aws-agent-cloudwatch-service --name LIVE --function-version 1

echo "✅ All functions restored to working Version 1"
echo "📋 Snapshot Details:"
echo "   - Universal Router: Working version with help/upload/objects/move support"
echo "   - S3 Service: Upload, list objects, move objects functionality"
echo "   - EC2 Service: 'What are' natural language support"
echo "   - CloudWatch: Explanations and metrics overview"
echo "   - IAM & Lambda: Basic working versions"

# Update API Gateway to use aliases (optional)
echo ""
echo "💡 To use aliases in API Gateway, update integration to:"
echo "   arn:aws:lambda:us-east-1:418257420035:function:aws-agent-executor:LIVE"