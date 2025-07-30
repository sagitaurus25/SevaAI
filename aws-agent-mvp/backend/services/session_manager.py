import redis.asyncio as redis
import json
import os
from typing import Optional
from datetime import datetime, timedelta

from models.session import SessionData

class SessionManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True
        )
        self.session_ttl = int(os.getenv("SESSION_TTL", 3600))  # 1 hour default
    
    async def create_session(self, session_data: SessionData) -> bool:
        """Create a new session"""
        try:
            session_key = f"session:{session_data.session_id}"
            session_json = session_data.model_dump_json()
            
            await self.redis_client.setex(
                session_key, 
                self.session_ttl, 
                session_json
            )
            return True
        except Exception as e:
            print(f"Error creating session: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data"""
        try:
            session_key = f"session:{session_id}"
            session_json = await self.redis_client.get(session_key)
            
            if session_json:
                session_data = SessionData.model_validate_json(session_json)
                # Extend TTL on access
                await self.redis_client.expire(session_key, self.session_ttl)
                return session_data
            return None
        except Exception as e:
            print(f"Error getting session: {e}")
            return None
    
    async def update_session(self, session_data: SessionData) -> bool:
        """Update session data"""
        try:
            session_data.updated_at = datetime.utcnow()
            session_key = f"session:{session_data.session_id}"
            session_json = session_data.model_dump_json()
            
            await self.redis_client.setex(
                session_key, 
                self.session_ttl, 
                session_json
            )
            return True
        except Exception as e:
            print(f"Error updating session: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        try:
            session_key = f"session:{session_id}"
            await self.redis_client.delete(session_key)
            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False
    
    async def get_active_sessions(self) -> list:
        """Get all active session IDs"""
        try:
            keys = await self.redis_client.keys("session:*")
            return [key.replace("session:", "") for key in keys]
        except Exception as e:
            print(f"Error getting active sessions: {e}")
            return []
        