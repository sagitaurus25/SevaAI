"""
Working Agent with explicit environment setup
"""
import json
import boto3
import os
import subprocess
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Get credentials from AWS CLI config
def get_aws_credentials():
    try:
        # Get credentials using AWS CLI
        result = subprocess.run(['aws', 'configure', 'get', 'aws_access_key_id'], capture_output=True, text=True)
        access_key = result.stdout.strip()
        
        result = subprocess.run(['aws', 'configure', 'get', 'aws_secret_access_key'], capture_output=True, text=True)
        secret_key = result.stdout.strip()
        
        result = subprocess.run(['aws', 'configure', 'get', 'region'], capture_output=True, text=True)
        region = result.stdout.strip() or 'us-east-1'
        
        return access_key, secret_key, region
    except:
        return None, None, None

# Set up AWS with explicit credentials
access_key, secret_key, region = get_aws_credentials()

if access_key and secret_key:
    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )
    try:
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS connected! Account: {identity['Account']}")
        
        bedrock = session.client('bedrock-runtime')
        AWS_WORKING = True
    except Exception as e:
        print(f"❌ AWS error: {e}")
        AWS_WORKING = False
else:
    print("❌ No AWS credentials found")
    AWS_WORKING = False

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class ChatResponse(BaseModel):
    role: str
    content: str

@app.get("/", response_class=HTMLResponse)
async def root():
    status = "✅ Working" if AWS_WORKING else "❌ Error"
    return f"""
    <html><body>
    <h1>SevaAI Working Agent</h1>
    <p>AWS Status: {status}</p>
    <p><b>Try:</b> "list my s3 buckets" or "show my ec2 instances"</p>
    <div id="chat" style="height:300px;overflow-y:auto;border:1px solid #ccc;padding:10px;margin:10px 0;"></div>
    <input id="input" style="width:80%;padding:5px;" placeholder="Ask me anything...">
    <button onclick="send()" style="padding:5px 10px;">Send</button>
    <script>
    async function send() {{
        const msg = document.getElementById('input').value;
        if (!msg) return;
        
        document.getElementById('chat').innerHTML += '<p><b>You:</b> ' + msg + '</p>';
        document.getElementById('input').value = '';
        
        try {{
            const res = await fetch('/chat', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{messages: [{{role: 'user', content: msg}}]}})
            }});
            const data = await res.json();
            document.getElementById('chat').innerHTML += '<p><b>AI:</b> ' + data.content + '</p>';
            document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
        }} catch(e) {{
            document.getElementById('chat').innerHTML += '<p><b>Error:</b> ' + e.message + '</p>';
        }}
    }}
    document.getElementById('input').addEventListener('keypress', e => e.key === 'Enter' && send());
    </script>
    </body></html>
    """

# AWS Tools
def list_s3_buckets():
    try:
        s3 = session.client('s3')
        response = s3.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        return f"Your S3 buckets: {', '.join(buckets) if buckets else 'None found'}"
    except Exception as e:
        return f"Error listing S3 buckets: {str(e)}"

def list_s3_objects(bucket_name):
    try:
        s3 = session.client('s3')
        response = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            objects = [f"{obj['Key']} ({obj['Size']} bytes)" for obj in response['Contents']]
            return f"Objects in {bucket_name}: {', '.join(objects)}"
        else:
            return f"Bucket {bucket_name} is empty"
    except Exception as e:
        return f"Error listing objects in {bucket_name}: {str(e)}"

def list_ec2_instances():
    try:
        ec2 = session.client('ec2')
        response = ec2.describe_instances()
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append(f"{instance['InstanceId']} ({instance['State']['Name']})")
        return f"Your EC2 instances: {', '.join(instances) if instances else 'None found'}"
    except Exception as e:
        return f"Error listing EC2 instances: {str(e)}"

@app.post("/chat")
async def chat(request: ChatRequest):
    if not AWS_WORKING:
        return ChatResponse(role="assistant", content="AWS not configured. Please check credentials.")
    
    user_message = request.messages[-1].content.lower()
    
    # Check for AWS commands first
    if "tarbucket" in user_message or ("s3" in user_message and "bucket" in user_message):
        if "objects" in user_message or "files" in user_message or "contents" in user_message:
            # Extract bucket name - look for tarbucket specifically
            if "tarbucket102424" in request.messages[-1].content:
                aws_result = list_s3_objects("tarbucket102424")
            else:
                # Try to extract any bucket name
                words = request.messages[-1].content.split()
                bucket_name = None
                for word in words:
                    if "bucket" in word.lower() and word.lower() != "bucket":
                        bucket_name = word
                        break
                if bucket_name:
                    aws_result = list_s3_objects(bucket_name)
                else:
                    aws_result = "Please specify bucket name. Example: 'list objects in bucket mybucket'"
        else:
            aws_result = list_s3_buckets()
        return ChatResponse(role="assistant", content=aws_result)
    elif "ec2" in user_message and "instance" in user_message:
        aws_result = list_ec2_instances()
        return ChatResponse(role="assistant", content=aws_result)
    
    # Otherwise use Claude
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": request.messages[-1].content}],
            "system": "You are SevaAI, an AWS assistant. When users ask about AWS resources, tell them to use specific commands like 'list my s3 buckets' or 'show my ec2 instances'."
        })
        
        response = bedrock.invoke_model(
            modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            body=body
        )
        
        result = json.loads(response["body"].read())
        return ChatResponse(role="assistant", content=result["content"][0]["text"])
        
    except Exception as e:
        return ChatResponse(role="assistant", content=f"Claude error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8093)