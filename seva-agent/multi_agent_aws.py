"""
Multi-Agent AWS System
"""
import json
import boto3
import subprocess
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from orchestrator import AgentOrchestrator

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

# Initialize system
access_key, secret_key, region = get_aws_credentials()
session = boto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
orchestrator = AgentOrchestrator(session)

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
    services = orchestrator.get_available_services()
    
    services_html = ""
    for service, capabilities in services.items():
        services_html += f"<div style='margin:10px 0;'><b>{service.upper()}:</b> {', '.join(capabilities)}</div>"
    
    return f"""
    <html><body>
    <h1>🤖 SevaAI - Your new IT Admin</h1>
    <div style="background:#e8f5e8;padding:15px;margin:15px 0;border-radius:8px;">
        <h3>🏗️ Architecture</h3>
        <p><b>Service-Specific Agents:</b> Each AWS service has its own specialized agent</p>
        <p><b>Intelligent Routing:</b> Commands automatically routed to the right agent</p>
        <p><b>Nova Micro Fallback:</b> General questions handled by Nova</p>
    </div>
    
    <div style="background:#f0f8ff;padding:15px;margin:15px 0;border-radius:8px;">
        <h3>🚀 Available Services & Capabilities</h3>
        {services_html}
    </div>
    
  
    
    <div id="chat" style="height:400px;overflow-y:auto;border:1px solid #ccc;padding:15px;margin:15px 0;background:#f9f9f9;border-radius:8px;"></div>
    <div style="display:flex;gap:10px;">
        <input id="input" style="flex:1;padding:10px;border:1px solid #ccc;border-radius:4px;" placeholder="Ask about AWS services or anything else...">
        <button onclick="send()" style="padding:10px 20px;background:#ff9900;color:white;border:none;border-radius:4px;cursor:pointer;">Send</button>
    </div>
    
    <script>
    async function send() {{
        const msg = document.getElementById('input').value;
        if (!msg) return;
        
        document.getElementById('chat').innerHTML += '<div style="margin:10px 0;padding:10px;background:#e3f2fd;border-radius:8px;text-align:right;"><b>You:</b> ' + msg + '</div>';
        document.getElementById('input').value = '';
        
        const loading = document.createElement('div');
        loading.style.cssText = 'margin:10px 0;padding:10px;background:#f1f1f1;border-radius:8px;';
        loading.innerHTML = '<b>🤖 SevaAI:</b> Processing...';
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
            response.style.cssText = 'margin:10px 0;padding:10px;background:#f1f1f1;border-radius:8px;white-space:pre-wrap;';
            response.innerHTML = '<b>🤖 SevaAI:</b> ' + data.content;
            document.getElementById('chat').appendChild(response);
            document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
        }} catch(e) {{
            document.getElementById('chat').removeChild(loading);
            document.getElementById('chat').innerHTML += '<div style="margin:10px 0;padding:10px;background:#ffebee;border-radius:8px;"><b>Error:</b> ' + e.message + '</div>';
        }}
    }}
    
    document.getElementById('input').addEventListener('keypress', e => e.key === 'Enter' && send());
    </script>
    </body></html>
    """

@app.get("/services")
async def get_services():
    """Get available services and capabilities"""
    return orchestrator.get_available_services()

@app.post("/chat")
async def chat(request: ChatRequest):
    user_message = request.messages[-1].content
    
    # Route command through orchestrator
    result = orchestrator.route_command(user_message)
    
    # Format response for display
    formatted_response = orchestrator.format_response(result)
    
    return ChatResponse(role="assistant", content=formatted_response)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8097)