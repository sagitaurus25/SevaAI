"""FastAPI server for containerized agent."""
import json
import time
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

# Import the agent
from src.agent import agent

app = FastAPI(title="Seva Data Analyst Agent")

# Configure CORS
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
    stream: bool = False

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/info")
async def get_info():
    """Return information about the agent."""
    return {
        "name": "Seva Data Analyst Agent",
        "version": "1.0.0",
        "description": "An AI assistant for data analysis tasks",
        "tools": [tool.name for tool in agent.tools]
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    """Process a chat request."""
    try:
        # Convert messages to the format expected by the agent
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Handle streaming response
        if request.stream:
            return StreamingResponse(
                stream_response(messages),
                media_type="text/event-stream"
            )
        
        # Handle non-streaming response
        response = agent.process_messages(messages)
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def stream_response(messages):
    """Stream the agent's response."""
    try:
        # Get streaming response from agent
        for chunk in agent.process_messages_stream(messages):
            # Format as server-sent event
            yield f"data: {json.dumps(chunk)}\n\n"
        
        # End of stream
        yield "data: [DONE]\n\n"
    except Exception as e:
        error_json = json.dumps({"error": str(e)})
        yield f"data: {error_json}\n\n"
        yield "data: [DONE]\n\n"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)