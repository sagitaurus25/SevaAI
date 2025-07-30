"""
Working Claude Agent - Uses boto3 session with explicit config
"""
import json
import boto3
from botocore.config import Config
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI(title="SevaAI Working Claude Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create session with explicit config to avoid encoding issues
session = boto3.Session()
bedrock = session.client(
    'bedrock-runtime',
    region_name='us-east-1',
    config=Config(
        retries={'max_attempts': 3},
        signature_version='v4'
    )
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class ChatResponse(BaseModel):
    role: str
    content: str

def call_claude(user_message):
    try:
        # Try Claude 3 Haiku first (simpler model)
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": user_message}]
        })
        
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=body,
            contentType='application/json'
        )
        
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]
    except Exception as e:
        return f"Claude error: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SevaAI Working Claude Agent</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .header { background: #232f3e; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            #chatbox { height: 400px; border: 1px solid #ddd; padding: 15px; overflow-y: auto; margin-bottom: 15px; border-radius: 4px; }
            #input { width: calc(100% - 100px); padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
            button { padding: 10px 20px; background: #ff9900; color: white; border: none; cursor: pointer; border-radius: 4px; margin-left: 10px; }
            .user-msg { text-align: right; margin: 10px 0; padding: 10px; background: #e3f2fd; border-radius: 8px; }
            .bot-msg { text-align: left; margin: 10px 0; padding: 10px; background: #f1f1f1; border-radius: 8px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 SevaAI Working Claude Agent</h1>
            <p>Claude 3 Haiku - Fixed Signature Issues</p>
        </div>
        
        <div id="chatbox"></div>
        <div>
            <input type="text" id="input" placeholder="Ask me anything..." />
            <button onclick="sendMessage()">Send</button>
        </div>
        
        <script>
            const chatbox = document.getElementById('chatbox');
            const input = document.getElementById('input');
            
            addBotMessage("Hello! I'm SevaAI with Claude 3 Haiku. How can I help you today?");
            
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
                loadingDiv.textContent = 'Thinking...';
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
        user_message = request.messages[-1].content
        response = call_claude(user_message)
        return ChatResponse(role="assistant", content=response)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8091)