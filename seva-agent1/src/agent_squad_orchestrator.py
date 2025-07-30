import os
import asyncio
from typing import Dict, Any, Optional
from agent_squad.orchestrator import AgentSquad
from agent_squad.agents import (
    BedrockLLMAgent, 
    BedrockLLMAgentOptions,
    AmazonBedrockAgent,
    AmazonBedrockAgentOptions
)
from agent_squad.storage import InMemoryChatStorage

class SevaAgentSquad:
    def __init__(self):
        """Initialize the Agent Squad with specialized AWS agents"""
        self.orchestrator = AgentSquad()
        self._setup_agents()
    
    def _setup_agents(self):
        """Configure specialized agents for different AWS services"""
        
        # 1. S3 Operations Agent
        s3_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
            name="S3Agent",
            description="""Expert in Amazon S3 operations including:
            - Bucket management (create, list, delete, configure)
            - Object operations (upload, download, list, move, copy)
            - Bucket policies and permissions
            - S3 storage classes and lifecycle policies
            - S3 event notifications and triggers
            """,
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            streaming=True
        ))
        
        # 2. EC2 Operations Agent  
        ec2_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
            name="EC2Agent",
            description="""Specialist in Amazon EC2 and compute services:
            - EC2 instance management (launch, stop, start, terminate)
            - Security groups and network configuration
            - Key pairs and SSH access
            - EBS volumes and snapshots
            - Auto Scaling and Load Balancers
            - Instance types and pricing optimization
            """,
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            streaming=True
        ))
        
        # 3. Lambda Operations Agent
        lambda_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
            name="LambdaAgent", 
            description="""Expert in AWS Lambda and serverless services:
            - Lambda function management (create, update, delete, invoke)
            - Function configuration and environment variables
            - Lambda triggers and event sources
            - Serverless architecture design
            - API Gateway integration
            - Lambda layers and deployment packages
            """,
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            streaming=True
        ))
        
        # 4. IAM Security Agent
        iam_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
            name="IAMAgent",
            description="""Security specialist for AWS Identity and Access Management:
            - User and role management
            - Policy creation and analysis
            - Permission troubleshooting
            - Security best practices
            - Access key management
            - Multi-factor authentication setup
            """,
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0", 
            streaming=True
        ))
        
        # 5. Monitoring & Troubleshooting Agent
        monitoring_agent = BedrockLLMAgent(BedrockLLMAgentOptions(
            name="MonitoringAgent",
            description="""Expert in AWS monitoring and troubleshooting:
            - CloudWatch metrics, logs, and alarms
            - AWS CloudTrail event analysis
            - Cost optimization and billing analysis
            - Performance monitoring and optimization
            - Service health and status checks
            - Troubleshooting common AWS issues
            """,
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            streaming=True
        ))
        
        # Add all agents to orchestrator
        self.orchestrator.add_agent(s3_agent)
        self.orchestrator.add_agent(ec2_agent) 
        self.orchestrator.add_agent(lambda_agent)
        self.orchestrator.add_agent(iam_agent)
        self.orchestrator.add_agent(monitoring_agent)
    
    async def process_request(self, user_query: str, user_id: str = "default", session_id: str = "default") -> Dict[str, Any]:
        """Process user request through Agent Squad"""
        try:
            response = await self.orchestrator.route_request(
                user_query, 
                user_id, 
                session_id
            )
            
            if response.streaming:
                # Handle streaming response
                content = ""
                async for chunk in response.output:
                    if hasattr(chunk, 'text'):
                        content += chunk.text
                
                return {
                    "success": True,
                    "agent_id": response.metadata.agent_id,
                    "agent_name": response.metadata.agent_name,
                    "content": content,
                    "streaming": True
                }
            else:
                # Handle non-streaming response
                return {
                    "success": True,
                    "agent_id": response.metadata.agent_id,
                    "agent_name": response.metadata.agent_name, 
                    "content": response.output.content,
                    "streaming": False
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Agent Squad processing error: {str(e)}",
                "suggestion": "Try rephrasing your request or ask for help with AWS services"
            }

# Global instance
seva_squad = SevaAgentSquad()