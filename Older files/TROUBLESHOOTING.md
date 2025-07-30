# S3 Agent Troubleshooting Guide

If you're encountering errors with the S3 agent, follow these troubleshooting steps:

## 1. Check API Gateway Configuration

Make sure your API Gateway is properly configured:

1. Log in to AWS Console and go to API Gateway
2. Select your API (e.g., "SevaAI-S3Agent-API")
3. Check that you have a resource called "s3agent" with a POST method
4. Verify that the POST method is integrated with your Lambda function
5. Make sure CORS is enabled
6. Verify that the API is deployed to a stage (e.g., "prod")

## 2. Check Lambda Function

Verify that your Lambda function is properly configured:

1. Log in to AWS Console and go to Lambda
2. Select your function (e.g., "SevaAI-S3Agent")
3. Check that the runtime is Python 3.9
4. Verify that the handler is set to "lambda_nova_parser_correct.lambda_handler"
5. Check that the environment variable "KNOWLEDGE_BASE_TABLE" is set to "S3CommandKnowledgeBase"
6. Check the execution role to ensure it has the necessary permissions

## 3. Check CloudWatch Logs

Check the CloudWatch logs for your Lambda function:

```bash
python check_lambda_logs.py --function SevaAI-S3Agent --minutes 10
```

Look for error messages that might indicate what's going wrong.

## 4. Test Lambda Function Directly

Test the Lambda function directly to bypass API Gateway:

```bash
python test_lambda_direct.py --function SevaAI-S3Agent --message "list buckets"
```

If this works but the API Gateway doesn't, the issue is likely with the API Gateway configuration.

## 5. Check DynamoDB Table

Verify that your DynamoDB table exists and has the correct items:

1. Log in to AWS Console and go to DynamoDB
2. Select "Tables" and find "S3CommandKnowledgeBase"
3. Click "Explore table items" to view the contents
4. Verify that there are items with intent patterns like "list buckets", "list files", etc.

## 6. Common Issues and Solutions

### "Function not found" error

This means the Lambda function doesn't exist or you don't have permission to access it. Create the function using the AWS Console.

### "Error processing your request" in the UI

This could be due to:
- API Gateway URL is incorrect (should include the resource path, e.g., "/s3agent")
- CORS is not enabled on the API Gateway
- Lambda function is throwing an error

### Lambda function errors

Common Lambda function errors:
- Missing environment variables
- Insufficient permissions
- Errors in the code
- Timeout (default is 3 seconds, you might need to increase it)

### DynamoDB errors

Common DynamoDB errors:
- Table doesn't exist
- Insufficient permissions
- Items not properly formatted

## 7. Update HTML Interface

Make sure your HTML interface is using the correct API endpoint:

```javascript
const API_ENDPOINT = 'https://your-api-id.execute-api.region.amazonaws.com/stage/s3agent';
```

Note that the endpoint should include the resource path ("/s3agent") at the end.