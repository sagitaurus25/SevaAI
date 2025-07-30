from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

class SessionData(BaseModel):
    session_id: str
    user_id: str
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ConversationEntry(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    command_executed: Optional[str] = None
    execution_result: Optional[str] = None