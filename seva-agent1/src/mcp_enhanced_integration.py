import subprocess
import json
import asyncio
from typing import Dict, Any, List
from enhanced_agent_squad import enhanced_seva_squad

class MCPEnhancedAgentSquad:
    def __init__(self):
        self.agent_squad = enhanced_seva_squad
        self.mcp_server_path = "/Users/tar/Documents/Cline/MCP/aws-knowledgebase-server"
    
    async def process_with_knowledge_base(self, user_query: str, user_id: str = "default", session_id: str = "default") -> Dict[str, Any]:
        """Process request with both Agent Squad and Knowledge Base context"""
        
        # Step 1: Get relevant context from Knowledge Base via MCP
        kb_context = await self._query_knowledge_base(user_query)
        
        # Step 2: Enhance the user query with KB context
        enhanced_query = self._enhance_query_with_context(user_query, kb_context)
        
        # Step 3: Process through Agent Squad
        agent_response = await self.agent_squad.process_request(enhanced_query, user_id, session_id)
        
        # Step 4: Combine results
        if agent_response["success"]:
            agent_response["knowledge_base_context"] = kb_context
            agent_response["context_sources"] = self._extract_sources(kb_context)
        
        return agent_response
    
    async def _query_knowledge_base(self, query: str) -> Dict[str, Any]:
        """Query the AWS Knowledge Base via MCP server"""
        try:
            # This would use your existing MCP server
            # For now, simulate the knowledge base response
            return {
                "relevant_docs": [
                    f"AWS Best Practices for {self._extract_service(query)}",
                    f"Common patterns and solutions",
                    f"Error handling recommendations"
                ],
                "confidence": 0.85,
                "source": "aws-knowledge-base"
            }
        except Exception as e:
            return {
                "error": f"Knowledge base query failed: {str(e)}",
                "relevant_docs": [],
                "confidence": 0.0
            }
    
    def _enhance_query_with_context(self, original_query: str, context: Dict[str, Any]) -> str:
        """Enhance user query with knowledge base context"""
        if context.get("relevant_docs"):
            context_text = "\n".join(context["relevant_docs"])
            return f"""
            Original Query: {original_query}
            
            Relevant Context from Knowledge Base:
            {context_text}
            
            Please provide a comprehensive response considering both the query and the context above.
            """
        return original_query
    
    def _extract_service(self, query: str) -> str:
        """Extract AWS service from query"""
        services = {
            "s3": ["s3", "bucket", "object", "storage"],
            "ec2": ["ec2", "instance", "server", "compute"],
            "lambda": ["lambda", "function", "serverless"],
            "iam": ["iam", "user", "role", "permission", "policy"],
            "cloudwatch": ["cloudwatch", "monitoring", "logs", "metrics"]
        }
        
        query_lower = query.lower()
        for service, keywords in services.items():
            if any(keyword in query_lower for keyword in keywords):
                return service.upper()
        
        return "General AWS"
    
    def _extract_sources(self, context: Dict[str, Any]) -> List[str]:
        """Extract source information from context"""
        return context.get("relevant_docs", [])

# Global MCP-enhanced instance
mcp_enhanced_squad = MCPEnhancedAgentSquad()