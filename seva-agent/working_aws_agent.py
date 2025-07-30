"""
Working AWS Agent with real AWS service integration
"""
import os
import json
import boto3
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI(title="SevaAI Working AWS Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS Tools
class AWSTools:
    def __init__(self):
        self.session = boto3.Session(
            region_name=os.environ.get("AWS_REGION", "us-east-1")
        )
    
    def list_s3_buckets(self):
        try:
            s3 = self.session.client('s3')
            response = s3.list_buckets()
            buckets = [bucket['Name'] for bucket in response['Buckets']]
            return f"Your S3 buckets: {', '.join(buckets)}"
        except Exception as e:
            return f"Error listing S3 buckets: {str(e)}"
    
    def list_ec2_instances(self):
        try:
            ec2 = self.session.client('ec2')
            response = ec2.describe_instances()
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append(f"{instance['InstanceId']} ({instance['State']['Name']})")
            return f"Your EC2 instances: {', '.join(instances) if instances else 'None found'}"
        except Exception as e:
            return f"Error listing EC2 instances: {str(e)}"
    
    def list_lambda_functions(self):
        try:
            lambda_client = self.session.client('lambda')
            response = lambda_client.list_functions()
            functions = [func['FunctionName'] for func in response['Functions']]
            return f"Your Lambda functions: {', '.join(functions) if functions else 'None found'}"
        except Exception as e:
            return f"Error listing Lambda functions: {str(e)}"

aws_tools = AWSTools()

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
    <!DOCTYPE html>
    <html>
    <head>
        <title>SevaAI Working AWS Agent</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .header { background: #232f3e; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            #chatbox { height: 400px; border: 1px solid #ddd; padding: 15px; overflow-y: auto; margin-bottom: 15px; border-radius: 4px; }
            #input { width: calc(100% - 100px); padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
            button { padding: 10px 20px; background: #ff9900; color: white; border: none; cursor: pointer; border-radius: 4px; margin-left: 10px; }
            .user-msg { text-align: right; margin: 10px 0; padding: 10px; background: #e3f2fd; border-radius: 8px; }
            .bot-msg { text-align: left; margin: 10px 0; padding: 10px; background: #f1f1f1; border-radius: 8px; }
            .examples { background: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 SevaAI Working AWS Agent</h1>
            <p>Real AWS service integration - S3, EC2, Lambda, and more!</p>
        </div>
        
        <div class="examples">
            <strong>Try these commands:</strong><br>
            • "list my s3 buckets"<br>
            • "show my ec2 instances"<br>
            • "what lambda functions do I have"
        </div>
        
        <div id="chatbox"></div>
        <div>
            <input type="text" id="input" placeholder="Ask about your AWS resources..." />
            <button onclick="sendMessage()">Send</button>
        </div>
        
        <script>
            const chatbox = document.getElementById('chatbox');
            const input = document.getElementById('input');
            
            addBotMessage("Hello! I'm connected to your AWS account. Try asking me to list your S3 buckets, EC2 instances, or Lambda functions!");
            
            function addUserMessage(text) {
                const div = document.createElement('div');
                div.className = 'user-msg';
                div.textContent = text;
                chatbox.appendChild(div);
                chatbox.scrollTop = chatbox.scrollHeight;
            }
            
            function addBotMessage(text) {
                const div = document.createElement('div');
                div.className = 'bot-msg';
                div.textContent = text;
                chatbox.appendChild(div);
                chatbox.scrollTop = chatbox.scrollHeight;
            }
            
            async function sendMessage() {
                const text = input.value.trim();
                if (!text) return;
                
                addUserMessage(text);
                input.value = '';
                
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'bot-msg';
                loadingDiv.textContent = 'Checking your AWS resources...';
                chatbox.appendChild(loadingDiv);
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ messages: [{ role: 'user', content: text }] }),
                    });
                    
                    const data = await response.json();
                    chatbox.removeChild(loadingDiv);
                    addBotMessage(data.content);
                    
                } catch (error) {
                    chatbox.removeChild(loadingDiv);
                    addBotMessage(`Error: ${error.message}`);
                }
            }
            
            input.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') sendMessage();
            });
        </script>
    </body>
    </html>
    """

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        user_message = request.messages[-1].content.lower()
        
        if "s3" in user_message and "bucket" in user_message:
            response = aws_tools.list_s3_buckets()
        elif "ec2" in user_message and "instance" in user_message:
            response = aws_tools.list_ec2_instances()
        elif "lambda" in user_message and "function" in user_message:
            response = aws_tools.list_lambda_functions()
        else:
            response = "I can help you list your AWS resources. Try asking me to 'list my s3 buckets', 'show my ec2 instances', or 'what lambda functions do I have'."
        
        return ChatResponse(role="assistant", content=response)
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8088)