import sys
import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any

# Add the seva-agent src to path
sys.path.append('/Users/tar/Desktop/SevaAI/seva-agent/src')

from mcp_enhanced_integration import mcp_enhanced_squad
from supervisor_orchestrator import seva_supervision

app = FastAPI(title="SevaAI Enhanced Agent Squad")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the enhanced frontend
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open('/Users/tar/Desktop/SevaAI/aws-agent-mvp/frontend/enhanced_index.html', 'r') as f:
        return HTMLResponse(content=f.read())

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

@app.post("/chat")
async def enhanced_chat(request: ChatRequest):
    """Enhanced chat endpoint with Agent Squad and MCP integration"""
    try:
        user_message = request.messages[-1].content if request.messages else ""
        
        # Determine if this is a complex request that needs supervision
        complex_keywords = [
            "deploy", "setup", "configure", "multi", "workflow", 
            "pipeline", "architecture", "infrastructure", "security audit"
        ]
        
        is_complex = any(keyword in user_message.lower() for keyword in complex_keywords)
        
        if is_complex:
            # Use supervisor orchestration for complex requests
            response = await seva_supervision.process_complex_request(
                user_message, 
                user_id="web_user", 
                session_id="web_session"
            )
            
            if response.streaming:
                content = ""
                async for chunk in response.output:
                    if hasattr(chunk, 'text'):
                        content += chunk.text
            else:
                content = response.output.content
            
            return JSONResponse({
                "role": "assistant",
                "content": content,
                "agent_used": response.metadata.agent_name,
                "agent_id": response.metadata.agent_id,
                "orchestration_type": "supervisor",
                "success": True
            })
        else:
            # Use enhanced MCP integration for standard requests
            result = await mcp_enhanced_squad.process_with_knowledge_base(
                user_message,
                user_id="web_user",
                session_id="web_session"
            )
            
            return JSONResponse({
                "role": "assistant",
                "content": result.get("content", "No response generated"),
                "description": result.get("description", ""),
                "command": result.get("command", ""),
                "agent_used": result.get("agent_name", "System"),
                "agent_id": result.get("agent_id", ""),
                "knowledge_base_context": result.get("knowledge_base_context", {}),
                "context_sources": result.get("context_sources", []),
                "orchestration_type": "standard",
                "success": result.get("success", False)
            })
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "role": "assistant", 
                "content": f"I apologize, but I encountered an error: {str(e)}",
                "success": False,
                "error": str(e)
            }
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "framework": "agent-squad", "version": "enhanced-1.0"}

@app.get("/agents")
async def list_agents():
    """List all available agents and their capabilities"""
    return {
        "agents": {
            "S3Agent": "Expert in Amazon S3 storage operations",
            "EC2Agent": "Specialist in compute and instance management", 
            "LambdaAgent": "Expert in serverless functions and Lambda",
            "IAMAgent": "Security and access management specialist",
            "MonitoringAgent": "CloudWatch and monitoring expert"
        },
        "supervisors": {
            "InfrastructureSupervisor": "Coordinates infrastructure teams",
            "DevOpsSupervisor": "Manages DevOps and deployment workflows",
            "SecuritySupervisor": "Orchestrates security and compliance teams"
        },
        "capabilities": [
            "Intelligent intent classification",
            "Multi-agent orchestration", 
            "Knowledge base integration",
            "Command generation",
            "Streaming responses",
            "Context management"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)