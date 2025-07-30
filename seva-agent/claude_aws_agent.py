"""
Claude AWS Agent - Claude generates and executes AWS CLI commands
"""
import json
import boto3
import subprocess
import re
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

if access_key and secret_key:
    session = boto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
    try:
        bedrock = session.client('bedrock-runtime')
        AWS_WORKING = True
    except Exception as e:
        AWS_WORKING = False
else:
    AWS_WORKING = False

def execute_aws_command(command):
    """Execute AWS operations using boto3 instead of CLI"""
    try:
        if "s3 ls" in command and "s3://" not in command:
            # List S3 buckets
            s3 = session.client('s3')
            response = s3.list_buckets()
            output = ""
            for bucket in response['Buckets']:
                date = bucket['CreationDate'].strftime('%Y-%m-%d %H:%M:%S')
                output += f"{date} {bucket['Name']}\n"
            return output
        elif "s3 ls s3://" in command:
            # List S3 objects
            bucket_name = command.split('s3://')[1].rstrip('/')
            s3 = session.client('s3')
            response = s3.list_objects_v2(Bucket=bucket_name)
            if 'Contents' in response:
                output = ""
                for obj in response['Contents']:
                    date = obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S')
                    size = obj['Size']
                    output += f"{date} {size:>10} {obj['Key']}\n"
                return output
            else:
                return "Bucket is empty"
        elif "ec2 describe-instances" in command:
            # List EC2 instances
            ec2 = session.client('ec2')
            response = ec2.describe_instances()
            output = ""
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    output += f"{instance['InstanceId']} {instance['State']['Name']} {instance['InstanceType']}\n"
            return output
        else:
            return f"Command not supported via boto3: {command}"
    except Exception as e:
        return f"Execution error: {str(e)}"

def call_claude_with_tools(user_message):
    """Call Claude with AWS tool capability"""
    system_prompt = """You are SevaAI, an AWS assistant. When users ask about AWS resources, you should:

1. Generate the appropriate AWS CLI command
2. Wrap the command in <aws_command> tags
3. Explain what the command does

Example:
User: "list my s3 buckets"
Response: "I'll list your S3 buckets using this command:

<aws_command>aws s3 ls</aws_command>

This command lists all S3 buckets in your account."

Available AWS services: S3, EC2, Lambda, IAM, RDS, CloudWatch, etc.
Only suggest safe read-only commands unless explicitly asked for modifications."""

    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": user_message}],
            "system": system_prompt
        })
        
        response = bedrock.invoke_model(
            modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            body=body
        )
        
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]
    except Exception as e:
        return f"Claude error: {str(e)}"

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
    <h1>🤖 SevaAI Claude AWS Agent</h1>
    <p>AWS Status: {status}</p>
    <p><b>Claude generates and executes AWS CLI commands!</b></p>
    <div id="chat" style="height:400px;overflow-y:auto;border:1px solid #ccc;padding:10px;margin:10px 0;background:#f9f9f9;"></div>
    <input id="input" style="width:80%;padding:8px;" placeholder="Ask about your AWS resources...">
    <button onclick="send()" style="padding:8px 15px;background:#ff9900;color:white;border:none;">Send</button>
    <script>
    async function send() {{
        const msg = document.getElementById('input').value;
        if (!msg) return;
        
        document.getElementById('chat').innerHTML += '<div style="margin:10px 0;padding:8px;background:#e3f2fd;border-radius:5px;text-align:right;"><b>You:</b> ' + msg + '</div>';
        document.getElementById('input').value = '';
        
        const loading = document.createElement('div');
        loading.style.cssText = 'margin:10px 0;padding:8px;background:#f1f1f1;border-radius:5px;';
        loading.innerHTML = '<b>AI:</b> Thinking...';
        document.getElementById('chat').appendChild(loading);
        document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
        
        try {{
            const res = await fetch('/chat', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{messages: [{{role: 'user', content: msg}}]}})
            }});
            const data = await res.json();
            
            document.getElementById('chat').removeChild(loading);
            
            const response = document.createElement('div');
            response.style.cssText = 'margin:10px 0;padding:8px;background:#f1f1f1;border-radius:5px;white-space:pre-wrap;';
            response.innerHTML = '<b>AI:</b> ' + data.content;
            document.getElementById('chat').appendChild(response);
            document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
        }} catch(e) {{
            document.getElementById('chat').removeChild(loading);
            document.getElementById('chat').innerHTML += '<div style="margin:10px 0;padding:8px;background:#ffebee;border-radius:5px;"><b>Error:</b> ' + e.message + '</div>';
        }}
    }}
    document.getElementById('input').addEventListener('keypress', e => e.key === 'Enter' && send());
    </script>
    </body></html>
    """

@app.post("/chat")
async def chat(request: ChatRequest):
    if not AWS_WORKING:
        return ChatResponse(role="assistant", content="AWS not configured. Please check credentials.")
    
    user_message = request.messages[-1].content
    
    # Get Claude's response
    claude_response = call_claude_with_tools(user_message)
    
    # Look for AWS commands in Claude's response
    aws_commands = re.findall(r'<aws_command>(.*?)</aws_command>', claude_response)
    
    if aws_commands:
        # Execute the AWS command
        command = aws_commands[0].strip()
        command_output = execute_aws_command(command)
        
        # Combine Claude's explanation with command output
        final_response = claude_response.replace(f'<aws_command>{command}</aws_command>', f'**Command:** `{command}`')
        final_response += f"\n\n**Output:**\n```\n{command_output}\n```"
        
        return ChatResponse(role="assistant", content=final_response)
    else:
        # No AWS command, return Claude's response as-is
        return ChatResponse(role="assistant", content=claude_response)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8094)