import sys
import os
sys.path.append('/Users/tar/Desktop/SevaAI/seva-agent1/src')

from agent_squad_orchestrator import seva_squad
from typing import Dict, Any

class AgentSquadService:
    def __init__(self):
        self.squad = seva_squad
    
    async def generate_aws_command(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process AWS requests through Agent Squad"""
        try:
            user_id = context.get('user_id', 'default') if context else 'default'
            session_id = context.get('session_id', 'default') if context else 'default'
            
            result = await self.squad.process_request(user_query, user_id, session_id)
            
            if result["success"]:
                return {
                    "success": True,
                    "command": f"# Processed by {result['agent_name']}",
                    "description": result["content"],
                    "agent_used": result["agent_name"],
                    "streaming": result.get("streaming", False)
                }
            else:
                return result
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Agent Squad error: {str(e)}",
                "suggestion": "Please try again or contact support"
            }