"""
Minimal web interface with AWS Bedrock
"""
import os
import json
import boto3
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any

# Import AWS tools
from aws_tools import AWSTools

# AWS credentials
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = "us-east-1"

# Initialize Bedrock client
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# Initialize AWS tools
aws_tools = AWSTools(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# System prompt
SYSTEM_PROMPT = """
You are a helpful AI data analyst assistant with access to AWS services. You can help with data analysis tasks, 
provide insights on data processing techniques, assist with data visualization recommendations, and access AWS services.

You have access to the following AWS services:
1. S3 - for listing buckets and objects
2. EC2 - for listing instances
3. Lambda - for listing functions
4. IAM - for listing users
5. RDS - for describing database instances

When the user asks about their AWS resources, you can use the appropriate AWS tool to retrieve the information.
"""

from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI()

# Mount the static HTML file
app.mount("/static", StaticFiles(directory=Path(__file__).parent), name="static")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class ChatResponse(BaseModel):
    role: str
    content: str

from fastapi.responses import RedirectResponse

@app.get("/")
async def root():
    """Redirect to the HTML file"""
    return RedirectResponse(url="/static/index.html")

@app.get("/test")
async def test():
    """Test endpoint"""
    return {"message": "API is working!"}

@app.get("/aws/s3/buckets")
async def list_s3_buckets():
    """List S3 buckets"""
    result = aws_tools.list_s3_buckets()
    return JSONResponse(content=json.loads(result))

@app.get("/aws/s3/objects/{bucket_name}")
async def list_s3_objects(bucket_name: str, prefix: str = ""):
    """List S3 objects"""
    result = aws_tools.list_s3_objects(bucket_name, prefix)
    return JSONResponse(content=json.loads(result))

@app.get("/aws/ec2/instances")
async def list_ec2_instances():
    """List EC2 instances"""
    result = aws_tools.list_ec2_instances()
    return JSONResponse(content=json.loads(result))

@app.get("/aws/lambda/functions")
async def list_lambda_functions():
    """List Lambda functions"""
    result = aws_tools.list_lambda_functions()
    return JSONResponse(content=json.loads(result))

@app.get("/aws/iam/users")
async def list_iam_users():
    """List IAM users"""
    result = aws_tools.list_iam_users()
    return JSONResponse(content=json.loads(result))

@app.get("/aws/rds/instances")
async def describe_rds_instances():
    """Describe RDS instances"""
    result = aws_tools.describe_rds_instances()
    return JSONResponse(content=json.loads(result))

from fastapi.middleware.cors import CORSMiddleware

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/echo", response_model=ChatResponse)
async def echo(request: ChatRequest):
    """Process the user's message with AWS Bedrock"""
    try:
        # Get the user message
        user_message = request.messages[-1].content if request.messages else ""
        
        # Check if the message is asking about AWS services
        aws_info = None
        
        # Simple keyword matching for AWS service requests
        if "list s3 buckets" in user_message.lower() or "show s3 buckets" in user_message.lower():
            aws_info = {"type": "s3_buckets", "data": json.loads(aws_tools.list_s3_buckets())}
        elif "list ec2" in user_message.lower() or "show ec2" in user_message.lower():
            aws_info = {"type": "ec2_instances", "data": json.loads(aws_tools.list_ec2_instances())}
        elif "list lambda" in user_message.lower() or "show lambda" in user_message.lower():
            aws_info = {"type": "lambda_functions", "data": json.loads(aws_tools.list_lambda_functions())}
        elif "list iam" in user_message.lower() or "show iam" in user_message.lower():
            aws_info = {"type": "iam_users", "data": json.loads(aws_tools.list_iam_users())}
        elif "list rds" in user_message.lower() or "show rds" in user_message.lower():
            aws_info = {"type": "rds_instances", "data": json.loads(aws_tools.describe_rds_instances())}
        
        # If AWS info was requested, include it in the message to Claude
        if aws_info:
            user_message = f"{user_message}\n\nHere is the requested AWS information:\n{json.dumps(aws_info['data'], indent=2)}"
        
        # Format messages for Claude
        formatted_messages = [{"role": "user", "content": user_message}]
        
        # Create the Claude 3 request body
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.7,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }
        
        # Call Bedrock with Claude 3.7 Sonnet model
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",  # Claude 3 Sonnet
            body=json.dumps(body)
        )
        
        # Parse the response for Claude 3
        response_body = json.loads(response["body"].read().decode("utf-8"))
        content = response_body.get("content", [])
        if content and isinstance(content, list) and len(content) > 0:
            content = content[0].get("text", "No response generated")
        else:
            content = "No response generated"
        
        return ChatResponse(role="assistant", content=content)
    except Exception as e:
        return ChatResponse(role="assistant", content=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)