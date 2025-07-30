"""
Fixed AWS Agent with proper credentials and Claude integration
"""
import os
import json
import boto3
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI(title="SevaAI Fixed AWS Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Bedrock for Claude
try:
    bedrock = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1"
    )
    BEDROCK_AVAILABLE = True
except Exception as e:
    BEDROCK_AVAILABLE = False
    print(f"Bedrock error: {e}")

class AWSTools:
    def __init__(self):
        try:
            self.session = boto3.Session(region_name='us-east-1')
            # Test credentials
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            self.credentials_valid = True
            self.account_id = identity['Account']
        except Exception as e:
            self.credentials_valid = False
            self.account_id = None
            print(f"AWS credential error: {e}")
    
    def list_s3_buckets(self):
        if not self.credentials_valid:
            return "AWS credentials not configured. Run: aws configure"
        try:
            s3 = self.session.client('s3')
            response = s3.list_buckets()
            buckets = [bucket['Name'] for bucket in response['Buckets']]
            return f"Your S3 buckets: {', '.join(buckets) if buckets else 'None found'}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def list_ec2_instances(self):
        if not self.credentials_valid:
            return "AWS credentials not configured. Run: aws configure"
        try:
            ec2 = self.session.client('ec2')
            response = ec2.describe_instances()
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append(f"{instance['InstanceId']} ({instance['State']['Name']})")
            return f"Your EC2 instances: {', '.join(instances) if instances else 'None found'}"
        except Exception as e:
            return f"Error: {str(e)}"

aws_tools = AWSTools()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class ChatResponse(BaseModel):
    role: str
    content: str

def call_claude(messages):
    if not BEDROCK_AVAILABLE:
        return "Claude not available. Please configure AWS Bedrock access."
    
    try:
        # Use Claude 3.5 Sonnet
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": messages,
            "system": "You are SevaAI, an AWS assistant. Help users with AWS services like S3, EC2, Lambda, etc. Be helpful and concise."
        }
        
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )
        
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]
    except Exception as e:
        return f"Claude error: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def root():
    creds_status = "✅ Connected" if aws_tools.credentials_valid else "❌ Not configured"
    claude_status = "✅ Available" if BEDROCK_AVAILABLE else "❌ Not available"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SevaAI Fixed AWS Agent</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #232f3e; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .status {{ background: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 20px; }}
            #chatbox {{ height: 400px; border: 1px solid #ddd; padding: 15px; overflow-y: auto; margin-bottom: 15px; border-radius: 4px; }}
            #input {{ width: calc(100% - 100px); padding: 10px; border: 1px solid #ddd; border-radius: 4px; }}
            button {{ padding: 10px 20px; background: #ff9900; color: white; border: none; cursor: pointer; border-radius: 4px; margin-left: 10px; }}
            .user-msg {{ text-align: right; margin: 10px 0; padding: 10px; background: #e3f2fd; border-radius: 8px; }}
            .bot-msg {{ text-align: left; margin: 10px 0; padding: 10px; background: #f1f1f1; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 SevaAI Fixed AWS Agent</h1>
            <p>AWS + Claude 3.5 Sonnet Integration</p>
        </div>
        
        <div class="status">
            <strong>Status:</strong><br>
            AWS Credentials: {creds_status}<br>
            Claude 3.5 Sonnet: {claude_status}
        </div>
        
        <div id="chatbox"></div>
        <div>
            <input type="text" id="input" placeholder="Ask about AWS or get help..." />
            <button onclick="sendMessage()">Send</button>
        </div>
        
        <script>
            const chatbox = document.getElementById('chatbox');
            const input = document.getElementById('input');
            
            addBotMessage("Hello! I'm SevaAI with Claude 3.5 Sonnet. I can help with AWS services and answer questions. What would you like to know?");
            
            function addUserMessage(text) {{
                const div = document.createElement('div');
                div.className = 'user-msg';
                div.textContent = text;
                chatbox.appendChild(div);
                chatbox.scrollTop = chatbox.scrollHeight;
            }}
            
            function addBotMessage(text) {{
                const div = document.createElement('div');
                div.className = 'bot-msg';
                div.textContent = text;
                chatbox.appendChild(div);
                chatbox.scrollTop = chatbox.scrollHeight;
            }}
            
            async function sendMessage() {{
                const text = input.value.trim();
                if (!text) return;
                
                addUserMessage(text);
                input.value = '';
                
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'bot-msg';
                loadingDiv.textContent = 'Thinking...';
                chatbox.appendChild(loadingDiv);
                
                try {{
                    const response = await fetch('/chat', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ messages: [{{ role: 'user', content: text }}] }}),
                    }});
                    
                    const data = await response.json();
                    chatbox.removeChild(loadingDiv);
                    addBotMessage(data.content);
                    
                }} catch (error) {{
                    chatbox.removeChild(loadingDiv);
                    addBotMessage(`Error: ${{error.message}}`);
                }}
            }}
            
            input.addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') sendMessage();
            }});
        </script>
    </body>
    </html>
    """

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        user_message = request.messages[-1].content.lower()
        
        # Handle AWS-specific commands
        if "s3" in user_message and "bucket" in user_message:
            aws_result = aws_tools.list_s3_buckets()
            if BEDROCK_AVAILABLE:
                claude_response = call_claude([{"role": "user", "content": f"Explain this AWS result: {aws_result}"}])
                response = f"{aws_result}\n\n{claude_response}"
            else:
                response = aws_result
        elif "ec2" in user_message and "instance" in user_message:
            aws_result = aws_tools.list_ec2_instances()
            if BEDROCK_AVAILABLE:
                claude_response = call_claude([{"role": "user", "content": f"Explain this AWS result: {aws_result}"}])
                response = f"{aws_result}\n\n{claude_response}"
            else:
                response = aws_result
        else:
            # Use Claude for general questions
            if BEDROCK_AVAILABLE:
                response = call_claude([{"role": "user", "content": request.messages[-1].content}])
            else:
                response = "I can help with AWS services. Try asking about S3 buckets or EC2 instances. For Claude integration, please configure AWS Bedrock access."
        
        return ChatResponse(role="assistant", content=response)
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8089)