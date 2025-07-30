"""
Final AWS Agent - Direct AWS operations with minimal Claude usage
"""
import json
import boto3
import subprocess
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Get AWS credentials
def get_aws_credentials():
    try:
        result = subprocess.run(['aws', 'configure', 'get', 'aws_access_key_id'], capture_output=True, text=True)
        access_key = result.stdout.strip()
        result = subprocess.run(['aws', 'configure', 'get', 'aws_secret_access_key'], capture_output=True, text=True)
        secret_key = result.stdout.strip()
        result = subprocess.run(['aws', 'configure', 'get', 'region'], capture_output=True, text=True)
        region = result.stdout.strip() or 'us-east-1'
        return access_key, secret_key, region
    except:
        return None, None, None

access_key, secret_key, region = get_aws_credentials()
session = boto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)

# AWS Functions
def list_s3_buckets():
    try:
        s3 = session.client('s3')
        response = s3.list_buckets()
        output = "Your S3 Buckets:\n"
        for bucket in response['Buckets']:
            date = bucket['CreationDate'].strftime('%Y-%m-%d')
            output += f"• {bucket['Name']} (created: {date})\n"
        return output
    except Exception as e:
        return f"Error: {str(e)}"

def list_s3_objects(bucket_name):
    try:
        s3 = session.client('s3')
        response = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            output = f"Objects in {bucket_name}:\n"
            for obj in response['Contents']:
                size = f"{obj['Size']} bytes"
                output += f"• {obj['Key']} ({size})\n"
            return output
        else:
            return f"Bucket {bucket_name} is empty"
    except Exception as e:
        return f"Error: {str(e)}"

def list_ec2_instances():
    try:
        ec2 = session.client('ec2')
        response = ec2.describe_instances()
        output = "Your EC2 Instances:\n"
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                name = "Unnamed"
                if 'Tags' in instance:
                    for tag in instance['Tags']:
                        if tag['Key'] == 'Name':
                            name = tag['Value']
                output += f"• {instance['InstanceId']} ({name}) - {instance['State']['Name']}\n"
        return output
    except Exception as e:
        return f"Error: {str(e)}"

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
    return """
    <html><body>
    <h1>🚀 SevaAI Final AWS Agent</h1>
    <p><b>Direct AWS Operations - No Throttling!</b></p>
    <div style="background:#f0f8ff;padding:10px;margin:10px 0;border-radius:5px;">
        <b>Available Commands:</b><br>
        • "list s3 buckets" or "show my buckets"<br>
        • "list objects in bucket [name]" or "show contents of [bucket]"<br>
        • "list ec2 instances" or "show my instances"
    </div>
    <div id="chat" style="height:400px;overflow-y:auto;border:1px solid #ccc;padding:10px;margin:10px 0;background:#f9f9f9;"></div>
    <input id="input" style="width:80%;padding:8px;" placeholder="Try: list s3 buckets">
    <button onclick="send()" style="padding:8px 15px;background:#ff9900;color:white;border:none;">Send</button>
    <script>
    async function send() {
        const msg = document.getElementById('input').value;
        if (!msg) return;
        
        document.getElementById('chat').innerHTML += '<div style="margin:10px 0;padding:8px;background:#e3f2fd;border-radius:5px;text-align:right;"><b>You:</b> ' + msg + '</div>';
        document.getElementById('input').value = '';
        
        try {
            const res = await fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({messages: [{role: 'user', content: msg}]})
            });
            const data = await res.json();
            
            const response = document.createElement('div');
            response.style.cssText = 'margin:10px 0;padding:8px;background:#f1f1f1;border-radius:5px;white-space:pre-wrap;';
            response.innerHTML = '<b>AI:</b> ' + data.content;
            document.getElementById('chat').appendChild(response);
            document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
        } catch(e) {
            document.getElementById('chat').innerHTML += '<div style="margin:10px 0;padding:8px;background:#ffebee;border-radius:5px;"><b>Error:</b> ' + e.message + '</div>';
        }
    }
    document.getElementById('input').addEventListener('keypress', e => e.key === 'Enter' && send());
    </script>
    </body></html>
    """

@app.post("/chat")
async def chat(request: ChatRequest):
    user_message = request.messages[-1].content.lower()
    
    # Direct command matching
    if "s3" in user_message and "bucket" in user_message:
        if "objects" in user_message or "contents" in user_message or "files" in user_message:
            # Extract bucket name
            original_message = request.messages[-1].content
            words = original_message.split()
            bucket_name = None
            for i, word in enumerate(words):
                if "bucket" in word.lower() and i + 1 < len(words):
                    bucket_name = words[i + 1]
                    break
                elif word.startswith("tarbucket") or word.endswith("bucket"):
                    bucket_name = word
                    break
            
            if bucket_name:
                result = list_s3_objects(bucket_name)
            else:
                result = "Please specify bucket name. Example: 'list objects in bucket mybucket'"
        else:
            result = list_s3_buckets()
    
    elif "ec2" in user_message and "instance" in user_message:
        result = list_ec2_instances()
    
    else:
        result = """I can help you with AWS operations:

• List S3 buckets: "list s3 buckets"
• List objects in bucket: "list objects in bucket [name]"  
• List EC2 instances: "list ec2 instances"

What would you like to do?"""
    
    return ChatResponse(role="assistant", content=result)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8095)