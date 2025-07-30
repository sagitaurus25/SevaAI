"""
Minimal Working Agent - Tested credentials
"""
import json
import boto3
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Test credentials on startup
try:
    session = boto3.Session()
    sts = session.client('sts')
    identity = sts.get_caller_identity()
    print(f"✅ AWS connected! Account: {identity['Account']}")
    
    bedrock = session.client('bedrock-runtime', region_name='us-east-1')
    print("✅ Bedrock client created")
    AWS_WORKING = True
except Exception as e:
    print(f"❌ AWS error: {e}")
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
    <h1>SevaAI Minimal Agent</h1>
    <p>AWS Status: {status}</p>
    <div id="chat"></div>
    <input id="input" placeholder="Type message...">
    <button onclick="send()">Send</button>
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
        }} catch(e) {{
            document.getElementById('chat').innerHTML += '<p><b>Error:</b> ' + e.message + '</p>';
        }}
    }}
    document.getElementById('input').addEventListener('keypress', e => e.key === 'Enter' && send());
    </script>
    </body></html>
    """

@app.post("/chat")
async def chat(request: ChatRequest):
    if not AWS_WORKING:
        return ChatResponse(role="assistant", content="AWS not configured properly")
    
    try:
        # Simple Claude call
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": request.messages[-1].content}]
        })
        
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=body
        )
        
        result = json.loads(response["body"].read())
        return ChatResponse(role="assistant", content=result["content"][0]["text"])
        
    except Exception as e:
        return ChatResponse(role="assistant", content=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8092)