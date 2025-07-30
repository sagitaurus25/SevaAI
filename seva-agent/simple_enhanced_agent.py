"""
Simple Enhanced AWS Agent - Works without AWS credentials for testing
"""
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI(title="SevaAI Simple Enhanced AWS Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        <title>SevaAI Enhanced AWS Agent</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            #chatbox { height: 400px; border: 1px solid #ddd; padding: 10px; overflow-y: auto; margin-bottom: 10px; }
            #input { width: 80%; padding: 8px; }
            button { padding: 8px 15px; background: #4CAF50; color: white; border: none; cursor: pointer; }
            .user-msg { text-align: right; margin: 5px; padding: 8px; background: #e1ffc7; border-radius: 5px; }
            .bot-msg { text-align: left; margin: 5px; padding: 8px; background: #f1f1f1; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>SevaAI Enhanced AWS Agent</h1>
        <div id="chatbox"></div>
        <div>
            <input type="text" id="input" placeholder="Ask about AWS services..." />
            <button onclick="sendMessage()">Send</button>
        </div>
        <script>
            const chatbox = document.getElementById('chatbox');
            const input = document.getElementById('input');
            
            addBotMessage("Hello! I'm SevaAI. I can help with S3, EC2, Lambda, IAM, and other AWS services. What would you like to know?");
            
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
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ messages: [{ role: 'user', content: text }] }),
                    });
                    
                    const data = await response.json();
                    addBotMessage(data.content);
                    
                } catch (error) {
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
        
        # Simple responses for AWS services
        if "s3" in user_message:
            response = "I can help with S3 operations like listing buckets, managing objects, and setting policies. What specific S3 task do you need help with?"
        elif "ec2" in user_message:
            response = "For EC2, I can help with instance management, security groups, and networking. What EC2 operation are you looking for?"
        elif "lambda" in user_message:
            response = "I can assist with Lambda functions, including deployment, invocation, and monitoring. What Lambda task do you need help with?"
        elif "iam" in user_message:
            response = "For IAM, I can help with users, roles, policies, and permissions. What IAM operation do you need?"
        elif "rds" in user_message:
            response = "I can help with RDS database management, snapshots, and monitoring. What RDS task are you working on?"
        elif "cloudwatch" in user_message:
            response = "For CloudWatch, I can help with metrics, alarms, and logs. What monitoring do you need?"
        else:
            response = f"I understand you're asking about: '{request.messages[-1].content}'. I can help with AWS services like S3, EC2, Lambda, IAM, RDS, CloudWatch, VPC, and more. What specific AWS task do you need help with?"
        
        return ChatResponse(role="assistant", content=response)
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8087)