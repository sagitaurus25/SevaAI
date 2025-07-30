# 🚀 SevaAI Agent Squad Implementation Plan

## Overview
Transform your current SevaAI agent from a simple command generator into an enterprise-grade, intelligent AWS operations assistant using AWS Labs Agent Squad framework.

## Current Analysis
Based on your existing structure:
- **Current**: Simple pattern-matching command generator (`llm_command_generator.py`)
- **Infrastructure**: AWS MCP server, Bedrock Agent capabilities, FastAPI backend
- **Target**: Multi-agent orchestration with intelligent routing and specialized agents

## Phase 1: Agent Squad Integration (Week 1)

### 1.1 Install Agent Squad Framework
```bash
# Navigate to your main project
cd /Users/tar/Desktop/SevaAI/seva-agent

# Install Agent Squad with AWS support
pip install "agent-squad[aws]"

# Update requirements
echo "agent-squad[aws]>=0.1.15" >> requirements.txt
```

### 1.2 Replace Command Generator with Agent Squad
Create new Agent Squad orchestrator to replace your current `llm_command_generator.py`:

**File: `seva-agent/src/agent_squad_orchestrator.py`**
```python
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
```

### 1.3 Update Backend Integration
Modify your backend to use Agent Squad:

**File: `aws-agent-mvp/backend/services/agent_squad_service.py`**
```python
import sys
import os
sys.path.append('/Users/tar/Desktop/SevaAI/seva-agent/src')

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
```

## Phase 2: Specialized Agents & Tool Integration (Week 2)

### 2.1 Create AWS Service-Specific Agents with Tools
Enhance agents with actual AWS CLI command generation and execution capabilities:

**File: `seva-agent/src/tools/aws_tools.py`**
```python
import boto3
import subprocess
import json
from typing import Dict, Any, List

class AWSTools:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.ec2_client = boto3.client('ec2')
        self.lambda_client = boto3.client('lambda')
        self.iam_client = boto3.client('iam')
        self.cloudwatch_client = boto3.client('cloudwatch')
    
    def generate_s3_command(self, operation: str, bucket: str = None, key: str = None, **kwargs) -> str:
        """Generate AWS CLI commands for S3 operations"""
        if operation == "list_buckets":
            return "aws s3 ls"
        elif operation == "list_objects" and bucket:
            recursive = "--recursive" if kwargs.get('recursive') else ""
            return f"aws s3 ls s3://{bucket}/ {recursive}".strip()
        elif operation == "create_bucket" and bucket:
            region = kwargs.get('region', 'us-east-1')
            return f"aws s3 mb s3://{bucket} --region {region}"
        elif operation == "upload_file" and bucket and key:
            local_file = kwargs.get('local_file', key)
            return f"aws s3 cp {local_file} s3://{bucket}/{key}"
        elif operation == "download_file" and bucket and key:
            local_file = kwargs.get('local_file', key)
            return f"aws s3 cp s3://{bucket}/{key} {local_file}"
        else:
            return f"# Unsupported S3 operation: {operation}"
    
    def generate_ec2_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for EC2 operations"""
        region = kwargs.get('region', 'us-east-1')
        
        if operation == "list_instances":
            state_filter = f"--filters Name=instance-state-name,Values={kwargs['state']}" if kwargs.get('state') else ""
            return f"aws ec2 describe-instances --region {region} {state_filter} --query 'Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,PublicIpAddress]' --output table".strip()
        elif operation == "start_instance":
            instance_id = kwargs.get('instance_id')
            return f"aws ec2 start-instances --region {region} --instance-ids {instance_id}"
        elif operation == "stop_instance":
            instance_id = kwargs.get('instance_id')
            return f"aws ec2 stop-instances --region {region} --instance-ids {instance_id}"
        elif operation == "create_security_group":
            group_name = kwargs.get('group_name')
            description = kwargs.get('description', 'Created by SevaAI')
            return f"aws ec2 create-security-group --region {region} --group-name {group_name} --description '{description}'"
        else:
            return f"# Unsupported EC2 operation: {operation}"
    
    def generate_lambda_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for Lambda operations"""
        region = kwargs.get('region', 'us-east-1')
        
        if operation == "list_functions":
            runtime_filter = f"--query 'Functions[?starts_with(Runtime, `{kwargs['runtime']}`)]'" if kwargs.get('runtime') else ""
            return f"aws lambda list-functions --region {region} {runtime_filter} --query 'Functions[*].[FunctionName,Runtime,LastModified]' --output table".strip()
        elif operation == "invoke_function":
            function_name = kwargs.get('function_name')
            payload = kwargs.get('payload', '{}')
            return f"aws lambda invoke --region {region} --function-name {function_name} --payload '{payload}' response.json"
        elif operation == "update_function_code":
            function_name = kwargs.get('function_name')
            zip_file = kwargs.get('zip_file')
            return f"aws lambda update-function-code --region {region} --function-name {function_name} --zip-file fileb://{zip_file}"
        else:
            return f"# Unsupported Lambda operation: {operation}"

# Global instance
aws_tools = AWSTools()
```

### 2.2 Enhanced Agent with Tool Integration
Update the Agent Squad orchestrator to include tools:

**File: `seva-agent/src/enhanced_agent_squad.py`**
```python
from agent_squad_orchestrator import SevaAgentSquad
from tools.aws_tools import aws_tools
import re
from typing import Dict, Any

class EnhancedSevaAgentSquad(SevaAgentSquad):
    def __init__(self):
        super().__init__()
        self.aws_tools = aws_tools
    
    async def process_request(self, user_query: str, user_id: str = "default", session_id: str = "default") -> Dict[str, Any]:
        """Enhanced processing with command generation"""
        
        # First, get the agent response
        agent_response = await super().process_request(user_query, user_id, session_id)
        
        if not agent_response["success"]:
            return agent_response
        
        # Try to generate actual AWS CLI commands based on the query
        aws_command = self._generate_aws_command(user_query, agent_response["agent_name"])
        
        if aws_command:
            agent_response["command"] = aws_command
            agent_response["description"] = f"{agent_response['content']}\n\n**Generated Command:**\n```bash\n{aws_command}\n```"
        
        return agent_response
    
    def _generate_aws_command(self, query: str, agent_name: str) -> str:
        """Generate AWS CLI commands based on query and agent"""
        query_lower = query.lower()
        
        if agent_name == "S3Agent":
            return self._parse_s3_query(query_lower)
        elif agent_name == "EC2Agent":
            return self._parse_ec2_query(query_lower)
        elif agent_name == "LambdaAgent":
            return self._parse_lambda_query(query_lower)
        elif agent_name == "IAMAgent":
            return self._parse_iam_query(query_lower)
        elif agent_name == "MonitoringAgent":
            return self._parse_monitoring_query(query_lower)
        
        return None
    
    def _parse_s3_query(self, query: str) -> str:
        """Parse S3-related queries and generate commands"""
        if "list" in query and "bucket" in query:
            if "objects" in query or "files" in query:
                # Extract bucket name
                bucket_match = re.search(r'\bin\s+([a-zA-Z0-9\-\.]+)', query)
                if bucket_match:
                    bucket = bucket_match.group(1)
                    recursive = "recursive" in query or "all" in query
                    return self.aws_tools.generate_s3_command("list_objects", bucket=bucket, recursive=recursive)
            else:
                return self.aws_tools.generate_s3_command("list_buckets")
        
        elif "create" in query and "bucket" in query:
            bucket_match = re.search(r'bucket\s+([a-zA-Z0-9\-\.]+)', query)
            if bucket_match:
                bucket = bucket_match.group(1)
                return self.aws_tools.generate_s3_command("create_bucket", bucket=bucket)
        
        elif "upload" in query:
            bucket_match = re.search(r'to\s+([a-zA-Z0-9\-\.]+)', query)
            if bucket_match:
                bucket = bucket_match.group(1)
                return self.aws_tools.generate_s3_command("upload_file", bucket=bucket, key="<your-file>")
        
        return None
    
    def _parse_ec2_query(self, query: str) -> str:
        """Parse EC2-related queries and generate commands"""
        if "list" in query and "instance" in query:
            if "running" in query:
                return self.aws_tools.generate_ec2_command("list_instances", state="running")
            elif "stopped" in query:
                return self.aws_tools.generate_ec2_command("list_instances", state="stopped")
            else:
                return self.aws_tools.generate_ec2_command("list_instances")
        
        elif "start" in query and "instance" in query:
            return self.aws_tools.generate_ec2_command("start_instance", instance_id="<instance-id>")
        
        elif "stop" in query and "instance" in query:
            return self.aws_tools.generate_ec2_command("stop_instance", instance_id="<instance-id>")
        
        return None
    
    def _parse_lambda_query(self, query: str) -> str:
        """Parse Lambda-related queries and generate commands"""
        if "list" in query and "function" in query:
            if "python" in query:
                return self.aws_tools.generate_lambda_command("list_functions", runtime="python")
            else:
                return self.aws_tools.generate_lambda_command("list_functions")
        
        elif "invoke" in query:
            return self.aws_tools.generate_lambda_command("invoke_function", function_name="<function-name>")
        
        return None
    
    def _parse_iam_query(self, query: str) -> str:
        """Parse IAM-related queries and generate commands"""
        if "list" in query and "user" in query:
            return "aws iam list-users --query 'Users[*].[UserName,CreateDate]' --output table"
        elif "list" in query and "role" in query:
            return "aws iam list-roles --query 'Roles[*].[RoleName,CreateDate]' --output table"
        elif "create" in query and "user" in query:
            return "aws iam create-user --user-name <username>"
        
        return None
    
    def _parse_monitoring_query(self, query: str) -> str:
        """Parse monitoring-related queries and generate commands"""
        if "cloudwatch" in query or "metric" in query:
            return "aws cloudwatch list-metrics --output table"
        elif "log" in query:
            return "aws logs describe-log-groups --output table"
        elif "alarm" in query:
            return "aws cloudwatch describe-alarms --output table"
        
        return None

# Global enhanced instance
enhanced_seva_squad = EnhancedSevaAgentSquad()
```

## Phase 3: Multi-Agent Orchestration (Week 3)

### 3.1 Implement SupervisorAgent for Complex Workflows
Add the powerful SupervisorAgent for team coordination:

**File: `seva-agent/src/supervisor_orchestrator.py`**
```python
from agent_squad.orchestrator import AgentSquad
from agent_squad.agents import SupervisorAgent, SupervisorAgentOptions, BedrockLLMAgent, BedrockLLMAgentOptions

class SevaSupervisionSystem:
    def __init__(self):
        self.main_orchestrator = AgentSquad()
        self._setup_supervisor_teams()
    
    def _setup_supervisor_teams(self):
        """Setup supervisor agents with specialized teams"""
        
        # AWS Infrastructure Team
        infrastructure_team = self._create_infrastructure_team()
        infrastructure_supervisor = SupervisorAgent(SupervisorAgentOptions(
            name="InfrastructureSupervisor",
            description="""Coordinates AWS infrastructure operations across multiple services.
            Manages complex workflows involving EC2, VPC, Load Balancers, and networking.
            Specializes in multi-step infrastructure deployments and orchestration.""",
            agents=infrastructure_team
        ))
        
        # DevOps & Deployment Team  
        devops_team = self._create_devops_team()
        devops_supervisor = SupervisorAgent(SupervisorAgentOptions(
            name="DevOpsSupervisor", 
            description="""Orchestrates DevOps workflows and application deployments.
            Coordinates Lambda functions, CI/CD pipelines, and serverless architectures.
            Manages complex deployment scenarios and automation workflows.""",
            agents=devops_team
        ))
        
        # Security & Compliance Team
        security_team = self._create_security_team()
        security_supervisor = SupervisorAgent(SupervisorAgentOptions(
            name="SecuritySupervisor",
            description="""Manages security, compliance, and access control workflows.
            Coordinates IAM policies, security groups, and compliance audits.
            Specializes in multi-service security configurations.""",
            agents=security_team
        ))
        
        # Add supervisors to main orchestrator
        self.main_orchestrator.add_agent(infrastructure_supervisor)
        self.main_orchestrator.add_agent(devops_supervisor)
        self.main_orchestrator.add_agent(security_supervisor)
    
    def _create_infrastructure_team(self):
        """Create infrastructure specialist team"""
        return [
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="EC2Specialist",
                description="Expert in EC2 instances, autoscaling, and compute optimization",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )),
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="NetworkingSpecialist", 
                description="Expert in VPC, subnets, security groups, and load balancers",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )),
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="StorageSpecialist",
                description="Expert in S3, EBS, EFS, and data management solutions",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            ))
        ]
    
    def _create_devops_team(self):
        """Create DevOps specialist team"""
        return [
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="ServerlessSpecialist",
                description="Expert in Lambda, API Gateway, and serverless architectures",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )),
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="ContainerSpecialist",
                description="Expert in ECS, EKS, Docker, and container orchestration", 
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )),
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="PipelineSpecialist",
                description="Expert in CodePipeline, CodeBuild, and CI/CD automation",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            ))
        ]
    
    def _create_security_team(self):
        """Create security specialist team"""  
        return [
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="IAMSpecialist",
                description="Expert in IAM policies, roles, and access management",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )),
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="ComplianceSpecialist",
                description="Expert in AWS Config, CloudTrail, and compliance frameworks",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )),
            BedrockLLMAgent(BedrockLLMAgentOptions(
                name="SecuritySpecialist", 
                description="Expert in security groups, NACLs, and threat detection",
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
            ))
        ]
    
    async def process_complex_request(self, user_query: str, user_id: str = "default", session_id: str = "default"):
        """Process complex multi-service requests through supervisor orchestration"""
        return await self.main_orchestrator.route_request(user_query, user_id, session_id)

# Global supervisor system
seva_supervision = SevaSupervisionSystem()
```

## Phase 4: MCP Integration Enhancement (Week 4)

### 4.1 Enhanced MCP Integration
Integrate your existing AWS Knowledge Base MCP server with Agent Squad:

**File: `seva-agent/src/mcp_enhanced_integration.py`**
```python
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
```

### 4.2 Update Your Existing MCP Server Integration
Enhance your existing AWS Knowledge Base MCP server:

**File: `Documents/Cline/MCP/aws-knowledgebase-server/src/enhanced_integration.ts`**
```typescript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { BedrockAgentRuntimeClient, RetrieveAndGenerateCommand } from '@aws-sdk/client-bedrock-agent-runtime';

export class EnhancedKnowledgeBaseServer {
    private bedrockClient: BedrockAgentRuntimeClient;
    private server: Server;
    
    constructor() {
        this.bedrockClient = new BedrockAgentRuntimeClient({
            region: process.env.AWS_REGION || 'us-east-1'
        });
        
        this.server = new Server(
            {
                name: 'aws-enhanced-knowledgebase',
                version: '1.1.0'
            },
            {
                capabilities: {
                    tools: {}
                }
            }
        );
        
        this.setupTools();
    }
    
    private setupTools() {
        this.server.setRequestHandler('tools/list', async () => ({
            tools: [
                {
                    name: 'query_aws_knowledge_base',
                    description: 'Query AWS knowledge base for relevant information',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            query: { type: 'string', description: 'The query to search for' },
                            service: { type: 'string', description: 'AWS service context (optional)' },
                            max_results: { type: 'number', description: 'Maximum results to return', default: 5 }
                        },
                        required: ['query']
                    }
                },
                {
                    name: 'get_aws_best_practices',
                    description: 'Get AWS best practices for specific services',
                    inputSchema: {
                        type: 'object', 
                        properties: {
                            service: { type: 'string', description: 'AWS service name' },
                            topic: { type: 'string', description: 'Specific topic or operation' }
                        },
                        required: ['service']
                    }
                },
                {
                    name: 'analyze_aws_error',
                    description: 'Analyze AWS error messages and provide solutions',
                    inputSchema: {
                        type: 'object',
                        properties: {
                            error_message: { type: 'string', description: 'AWS error message' },
                            service: { type: 'string', description: 'AWS service where error occurred' },
                            context: { type: 'string', description: 'Additional context about the operation' }
                        },
                        required: ['error_message']
                    }
                }
            ]
        }));
        
        this.server.setRequestHandler('tools/call', async (request) => {
            const { name, arguments: args } = request.params;
            
            switch (name) {
                case 'query_aws_knowledge_base':
                    return await this.queryKnowledgeBase(args.query, args.service, args.max_results);
                    
                case 'get_aws_best_practices':
                    return await this.getAWSBestPractices(args.service, args.topic);
                    
                case 'analyze_aws_error':
                    return await this.analyzeAWSError(args.error_message, args.service, args.context);
                    
                default:
                    throw new Error(`Unknown tool: ${name}`);
            }
        });
    }
    
    private async queryKnowledgeBase(query: string, service?: string, maxResults: number = 5) {
        try {
            // Enhanced query with service context
            const enhancedQuery = service ? `${service}: ${query}` : query;
            
            const command = new RetrieveAndGenerateCommand({
                input: {
                    text: enhancedQuery
                },
                retrieveAndGenerateConfiguration: {
                    type: 'KNOWLEDGE_BASE',
                    knowledgeBaseConfiguration: {
                        knowledgeBaseId: process.env.KNOWLEDGE_BASE_ID,
                        modelArn: `arn:aws:bedrock:${process.env.AWS_REGION}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0`
                    }
                }
            });
            
            const response = await this.bedrockClient.send(command);
            
            return {
                content: [
                    {
                        type: 'text',
                        text: JSON.stringify({
                            answer: response.output?.text,
                            sources: response.citations?.map(citation => ({
                                content: citation.generatedResponsePart?.textResponsePart?.text,
                                source: citation.retrievedReferences?.[0]?.location?.s3Location?.uri
                            })) || [],
                            confidence: this.calculateConfidence(response),
                            service_context: service
                        }, null, 2)
                    }
                ]
            };
            
        } catch (error) {
            return {
                content: [
                    {
                        type: 'text',
                        text: JSON.stringify({
                            error: `Knowledge base query failed: ${error.message}`,
                            query: query,
                            service: service
                        }, null, 2)
                    }
                ]
            };
        }
    }
    
    private async getAWSBestPractices(service: string, topic?: string) {
        const query = topic ? 
            `Best practices for ${service} ${topic}` : 
            `AWS ${service} best practices and recommendations`;
            
        return await this.queryKnowledgeBase(query, service);
    }
    
    private async analyzeAWSError(errorMessage: string, service?: string, context?: string) {
        const query = `
        Error Analysis Request:
        Error Message: ${errorMessage}
        Service: ${service || 'Unknown'}
        Context: ${context || 'No additional context'}
        
        Please provide:
        1. Root cause analysis
        2. Step-by-step resolution
        3. Prevention strategies
        4. Related AWS documentation
        `;
        
        return await this.queryKnowledgeBase(query, service);
    }
    
    private calculateConfidence(response: any): number {
        // Simple confidence calculation based on response quality
        if (!response.output?.text) return 0.0;
        
        const textLength = response.output.text.length;
        const hasCitations = response.citations && response.citations.length > 0;
        
        let confidence = 0.5; // Base confidence
        
        if (textLength > 100) confidence += 0.2;
        if (textLength > 500) confidence += 0.1;
        if (hasCitations) confidence += 0.2;
        
        return Math.min(confidence, 1.0);
    }
    
    async start() {
        const transport = new StdioServerTransport();
        await this.server.connect(transport);
    }
}
```

## Phase 5: Frontend Integration & Testing

### 5.1 Update Frontend to Support Agent Squad
Update your existing frontend to display agent information:

**File: `aws-agent-mvp/frontend/enhanced_index.html`**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SevaAI - Enterprise AWS Agent Squad</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        
        .header .subtitle {
            color: #7f8c8d;
            font-size: 1.2em;
        }
        
        .agent-status {
            display: flex;
            justify-content: space-around;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .agent-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin: 5px;
            text-align: center;
            min-width: 150px;
            border-left: 4px solid #3498db;
        }
        
        .agent-card.active {
            border-left-color: #2ecc71;
            background: #e8f5e8;
        }
        
        #chatbox { 
            height: 500px; 
            border: 2px solid #e1e8ed; 
            padding: 20px; 
            overflow-y: auto; 
            margin-bottom: 20px; 
            border-radius: 10px;
            background: #fafbfc;
        }
        
        .message {
            margin: 15px 0;
            padding: 15px;
            border-radius: 10px;
            max-width: 80%;
        }
        
        .user-msg { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-left: auto;
        }
        
        .bot-msg { 
            background: #f1f3f4;
            border-left: 4px solid #4285f4;
        }
        
        .agent-info {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
            font-weight: bold;
        }
        
        .command-block {
            background: #2d3748;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            margin: 10px 0;
            overflow-x: auto;
        }
        
        .input-area {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        #input { 
            flex: 1;
            padding: 15px; 
            border: 2px solid #e1e8ed;
            border-radius: 25px;
            font-size: 16px;
            outline: none;
        }
        
        #input:focus {
            border-color: #4285f4;
        }
        
        button { 
            padding: 15px 30px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            border: none; 
            border-radius: 25px;
            cursor: pointer; 
            font-size: 16px;
            font-weight: bold;
            transition: transform 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
        }
        
        .examples {
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        
        .example-queries {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .example-query {
            background: white;
            padding: 10px;
            border-radius: 8px;
            cursor: pointer;
            border: 1px solid #e1e8ed;
            transition: all 0.3s ease;
        }
        
        .example-query:hover {
            background: #e3f2fd;
            transform: translateY(-2px);
        }
        
        .loading {
            display: none;
            color: #666;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 SevaAI Agent Squad</h1>
            <p class="subtitle">Enterprise AWS Operations Assistant</p>
        </div>
        
        <div class="agent-status">
            <div class="agent-card" id="s3-agent">
                <strong>S3 Agent</strong><br>
                <small>Storage Operations</small>
            </div>
            <div class="agent-card" id="ec2-agent">
                <strong>EC2 Agent</strong><br>
                <small>Compute Management</small>
            </div>
            <div class="agent-card" id="lambda-agent">
                <strong>Lambda Agent</strong><br>
                <small>Serverless Functions</small>
            </div>
            <div class="agent-card" id="iam-agent">
                <strong>IAM Agent</strong><br>
                <small>Security & Access</small>
            </div>
            <div class="agent-card" id="monitoring-agent">
                <strong>Monitoring Agent</strong><br>
                <small>CloudWatch & Logs</small>
            </div>
        </div>
        
        <div id="chatbox"></div>
        
        <div class="input-area">
            <input type="text" id="input" placeholder="Ask about AWS operations... (e.g., 'List my S3 buckets' or 'Show running EC2 instances')" />
            <button onclick="sendMessage()">Send</button>
        </div>
        
        <div class="examples">
            <h3>🚀 Try These Example Queries:</h3>
            <div class="example-queries">
                <div class="example-query" onclick="setQuery(this.textContent)">
                    List all objects in my-bucket recursively
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    Show me all running EC2 instances
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    List my Python Lambda functions
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    Create a new S3 bucket called my-new-bucket
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    Show CloudWatch alarms that are triggered
                </div>
                <div class="example-query" onclick="setQuery(this.textContent)">
                    Help me troubleshoot Lambda function errors
                </div>
            </div>
        </div>
    </div>

    <script>
        const chatbox = document.getElementById('chatbox');
        const input = document.getElementById('input');
        
        // Agent name mapping
        const agentMapping = {
            'S3Agent': 's3-agent',
            'EC2Agent': 'ec2-agent', 
            'LambdaAgent': 'lambda-agent',
            'IAMAgent': 'iam-agent',
            'MonitoringAgent': 'monitoring-agent'
        };
        
        // Add initial welcome message
        addBotMessage("👋 Welcome to SevaAI Agent Squad! I'm your intelligent AWS operations assistant powered by specialized AI agents. Each agent is an expert in specific AWS services and can help you with operations, troubleshooting, and best practices.", "System");
        
        function setQuery(query) {
            input.value = query;
            input.focus();
        }
        
        function highlightActiveAgent(agentName) {
            // Reset all agents
            Object.values(agentMapping).forEach(id => {
                document.getElementById(id).classList.remove('active');
            });
            
            // Highlight active agent
            if (agentMapping[agentName]) {
                document.getElementById(agentMapping[agentName]).classList.add('active');
            }
        }
        
        function addUserMessage(text) {
            const div = document.createElement('div');
            div.className = 'message user-msg';
            div.textContent = text;
            chatbox.appendChild(div);
            chatbox.scrollTop = chatbox.scrollHeight;
        }
        
        function addBotMessage(text, agentName = null) {
            const div = document.createElement('div');
            div.className = 'message bot-msg';
            
            let html = '';
            if (agentName && agentName !== 'System') {
                html += `<div class="agent-info">🤖 ${agentName} Agent</div>`;
                highlightActiveAgent(agentName);
            }
            
            // Parse markdown-style code blocks
            if (text.includes('```')) {
                const parts = text.split(/```(\w*)\n?/);
                let processedText = '';
                
                for (let i = 0; i < parts.length; i++) {
                    if (i % 3 === 0) {
                        processedText += parts[i];
                    } else if (i % 3 === 2) {
                        processedText += `<div class="command-block">${parts[i]}</div>`;
                    }
                }
                html += processedText;
            } else {
                html += text.replace(/\n/g, '<br>');
            }
            
            div.innerHTML = html;
            chatbox.appendChild(div);
            chatbox.scrollTop = chatbox.scrollHeight;
        }
        
        function showLoading() {
            const div = document.createElement('div');
            div.className = 'message bot-msg loading';
            div.innerHTML = '<div class="agent-info">🔄 Processing...</div>Analyzing your request and routing to the appropriate agent...';
            div.id = 'loading-message';
            chatbox.appendChild(div);
            chatbox.scrollTop = chatbox.scrollHeight;
        }
        
        function hideLoading() {
            const loadingMsg = document.getElementById('loading-message');
            if (loadingMsg) {
                loadingMsg.remove();
            }
        }
        
        async function sendMessage() {
            const text = input.value.trim();
            if (!text) return;
            
            addUserMessage(text);
            input.value = '';
            showLoading();
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        messages: [{ role: 'user', content: text }]
                    }),
                });
                
                hideLoading();
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                
                // Extract agent name and content
                const agentName = data.agent_used || data.agent_name || 'System';
                let content = data.content || data.description || 'No response generated';
                
                // Add command if available
                if (data.command && data.command !== '# Processed by ' + agentName) {
                    content += `\n\n**Generated Command:**\n\`\`\`bash\n${data.command}\n\`\`\``;
                }
                
                addBotMessage(content, agentName);
                
            } catch (error) {
                hideLoading();
                addBotMessage(`Sorry, there was an error processing your request: ${error.message}`, 'System');
                console.error('Error:', error);
            }
        }
        
        // Allow pressing Enter to send message
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
        
        // Auto-focus input
        input.focus();
    </script>
</body>
</html>
```

### 5.2 Update Backend App to Use Enhanced Agent Squad
Update your main Flask/FastAPI app:

**File: `aws-agent-mvp/backend/app_enhanced.py`**
```python
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
```

## Phase 6: Testing & Deployment Scripts

### 6.1 Comprehensive Testing Script
Create a testing script to validate all components:

**File: `seva-agent/test_agent_squad.py`**
```python
import asyncio
import sys
sys.path.append('src')

from agent_squad_orchestrator import seva_squad
from enhanced_agent_squad import enhanced_seva_squad  
from supervisor_orchestrator import seva_supervision
from mcp_enhanced_integration import mcp_enhanced_squad

async def test_basic_agent_squad():
    """Test basic Agent Squad functionality"""
    print("🧪 Testing Basic Agent Squad...")
    
    test_queries = [
        "List my S3 buckets",
        "Show running EC2 instances", 
        "List Python Lambda functions",
        "Show IAM users",
        "Check CloudWatch alarms"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        result = await seva_squad.process_request(query)
        print(f"✅ Agent: {result.get('agent_name', 'Unknown')}")
        print(f"📋 Response: {result.get('content', 'No response')[:100]}...")

async def test_enhanced_agent_squad():
    """Test enhanced Agent Squad with command generation"""
    print("\n🔧 Testing Enhanced Agent Squad...")
    
    test_queries = [
        "List objects in my-data-bucket recursively",
        "Show all stopped EC2 instances",
        "Create a bucket called test-bucket-2024"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        result = await enhanced_seva_squad.process_request(query)
        print(f"✅ Agent: {result.get('agent_name', 'Unknown')}")
        if result.get('command'):
            print(f"💻 Command: {result.get('command')}")

async def test_supervisor_orchestration():
    """Test supervisor orchestration for complex workflows"""
    print("\n👥 Testing Supervisor Orchestration...")
    
    complex_query = "Deploy a secure web application infrastructure with load balancer, EC2 instances, and RDS database"
    print(f"\n📝 Complex Query: {complex_query}")
    
    result = await seva_supervision.process_complex_request(complex_query)
    
    if result.streaming:
        print("🌊 Streaming response received")
        content = ""
        async for chunk in result.output:
            if hasattr(chunk, 'text'):
                content += chunk.text
        print(f"📋 Final Response: {content[:200]}...")
    else:
        print(f"📋 Response: {result.output.content[:200]}...")

async def test_mcp_integration():
    """Test MCP knowledge base integration"""
    print("\n📚 Testing MCP Knowledge Base Integration...")
    
    query = "What are S3 best practices for security?"
    print(f"\n📝 Query: {query}")
    
    result = await mcp_enhanced_squad.process_with_knowledge_base(query)
    print(f"✅ Success: {result.get('success', False)}")
    print(f"📚 KB Context: {result.get('knowledge_base_context', {})}")
    print(f"📋 Response: {result.get('content', 'No response')[:150]}...")

async def main():
    """Run all tests"""
    print("🚀 SevaAI Agent Squad Test Suite")
    print("=" * 50)
    
    try:
        await test_basic_agent_squad()
        await test_enhanced_agent_squad()
        await test_supervisor_orchestration() 
        await test_mcp_integration()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
```

### 6.2 Deployment Script
Create a deployment script for easy setup:

**File: `seva-agent/deploy_agent_squad.py`**
```python
#!/usr/bin/env python3
import os
import subprocess
import sys

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return None

def setup_environment():
    """Set up the Python environment and dependencies"""
    print("📦 Setting up Agent Squad environment...")
    
    # Install Agent Squad
    run_command("pip install 'agent-squad[aws]'", "Installing Agent Squad framework")
    
    # Install additional dependencies
    additional_deps = [
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.23.0", 
        "boto3>=1.26.0",
        "pydantic>=2.0.0"
    ]
    
    for dep in additional_deps:
        run_command(f"pip install '{dep}'", f"Installing {dep}")

def configure_aws_credentials():
    """Configure AWS credentials"""
    print("🔐 Configuring AWS credentials...")
    
    # Check if AWS CLI is configured
    result = run_command("aws sts get-caller-identity", "Checking AWS credentials")
    
    if result:
        print("✅ AWS credentials are configured")
        return True
    else:
        print("❌ AWS credentials not found. Please run: aws configure")
        return False

def setup_directory_structure():
    """Create necessary directory structure"""
    print("📁 Setting up directory structure...")
    
    directories = [
        "src/tools",
        "src/agents", 
        "logs",
        "config"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def create_environment_file():
    """Create .env file with necessary environment variables"""
    print("⚙️ Creating environment configuration...")
    
    env_content = """# SevaAI Agent Squad Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_REGION=us-east-1

# Agent Squad Configuration
AGENT_SQUAD_LOG_LEVEL=INFO
AGENT_SQUAD_MAX_TOKENS=4096
AGENT_SQUAD_TEMPERATURE=0.7

# Knowledge Base Configuration (if available)
KNOWLEDGE_BASE_ID=your-knowledge-base-id
KNOWLEDGE_BASE_REGION=us-east-1

# MCP Server Configuration
MCP_SERVER_PORT=3000
MCP_SERVER_HOST=localhost
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env file")

def test_installation():
    """Test the installation"""
    print("🧪 Testing installation...")
    
    test_script = """
import sys
sys.path.append('src')

try:
    from agent_squad.orchestrator import AgentSquad
    from agent_squad.agents import BedrockLLMAgent, BedrockLLMAgentOptions
    print("✅ Agent Squad import successful")
    
    # Test basic orchestrator creation
    orchestrator = AgentSquad()
    print("✅ Orchestrator creation successful")
    
    print("🎉 Installation test passed!")
    
except Exception as e:
    print(f"❌ Installation test failed: {str(e)}")
    sys.exit(1)
"""
    
    with open('test_install.py', 'w') as f:
        f.write(test_script)
    
    result = run_command("python test_install.py", "Running installation test")
    
    # Clean up test file
    os.remove('test_install.py')
    
    return result is not None

def create_startup_script():
    """Create startup script for the enhanced backend"""
    print("🚀 Creating startup script...")
    
    startup_content = """#!/bin/bash
# SevaAI Agent Squad Startup Script

echo "🤖 Starting SevaAI Agent Squad..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Environment variables loaded"
fi

# Check AWS credentials
echo "🔐 Checking AWS credentials..."
aws sts get-caller-identity > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ AWS credentials verified"
else
    echo "❌ AWS credentials not found. Please run: aws configure"
    exit 1
fi

# Start the enhanced backend
echo "🚀 Starting enhanced backend server..."
cd /Users/tar/Desktop/SevaAI/aws-agent-mvp/backend
python app_enhanced.py

echo "📊 SevaAI Agent Squad is running on http://localhost:8085"
"""
    
    with open('start_seva_agent_squad.sh', 'w') as f:
        f.write(startup_content)
    
    # Make executable
    os.chmod('start_seva_agent_squad.sh', 0o755)
    print("✅ Created startup script: start_seva_agent_squad.sh")

def main():
    """Main deployment function"""
    print("🎯 SevaAI Agent Squad Deployment")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Run deployment steps
    setup_directory_structure()
    setup_environment()
    
    if not configure_aws_credentials():
        print("⚠️ Please configure AWS credentials and run again")
        return
    
    create_environment_file()
    
    if test_installation():
        create_startup_script()
        
        print("\n" + "=" * 50)
        print("🎉 Deployment completed successfully!")
        print("\n📋 Next Steps:")
        print("1. Review and update .env file with your specific configuration")
        print("2. If using Knowledge Base, update KNOWLEDGE_BASE_ID in .env")
        print("3. Run: ./start_seva_agent_squad.sh")
        print("4. Open: http://localhost:8085")
        print("\n🚀 Your Agent Squad is ready to serve!")
    else:
        print("❌ Deployment failed during testing")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### 6.3 Quick Setup Guide
Create a quick setup guide:

**File: `seva-agent/AGENT_SQUAD_SETUP.md`**
```markdown
# 🚀 SevaAI Agent Squad Quick Setup Guide

## Prerequisites
- Python 3.8+
- AWS CLI configured
- AWS Bedrock access to Claude models

## 🏃‍♂️ Quick Start (5 minutes)

### 1. Run Automated Deployment
```bash
cd /Users/tar/Desktop/SevaAI/seva-agent
python deploy_agent_squad.py
```

### 2. Configure Environment
Edit `.env` file with your specific settings:
```bash
nano .env
```

### 3. Start the Agent Squad
```bash
./start_seva_agent_squad.sh
```

### 4. Access the Interface
Open http://localhost:8085 in your browser

## 🧪 Manual Testing

### Test Individual Components:
```bash
# Test basic Agent Squad
python test_agent_squad.py

# Test specific functionality
python -c "
import asyncio
import sys
sys.path.append('src')
from agent_squad_orchestrator import seva_squad

async def test():
    result = await seva_squad.process_request('List my S3 buckets')
    print(f'Agent: {result[\"agent_name\"]}')
    print(f'Response: {result[\"content\"][:100]}...')

asyncio.run(test())
"
```

## 🔧 Advanced Configuration

### Enable Knowledge Base Integration
1. Create AWS Bedrock Knowledge Base
2. Update `KNOWLEDGE_BASE_ID` in `.env`
3. Restart the service

### Add Custom Agents
1. Create new agent in `src/agents/`
2. Register in `agent_squad_orchestrator.py`
3. Restart service

### Configure MCP Server
1. Update MCP server path in configuration
2. Ensure MCP server is running
3. Test connection

## 📊 Monitoring & Troubleshooting

### Check Logs
```bash
tail -f logs/agent_squad.log
```

### Test AWS Connection
```bash
aws sts get-caller-identity
aws bedrock list-foundation-models --region us-east-1
```

### Verify Agent Squad Installation
```bash
python -c "from agent_squad.orchestrator import AgentSquad; print('✅ Agent Squad installed')"
```

## 🚨 Common Issues

### Issue: "No module named 'agent_squad'"
**Solution:** Run `pip install "agent-squad[aws]"`

### Issue: "AWS credentials not found"
**Solution:** Run `aws configure`

### Issue: "Bedrock access denied"
**Solution:** Request model access in AWS Bedrock console

### Issue: "Import errors"
**Solution:** Check Python path and dependencies

## 🎯 Next Steps

1. **Customize Agents**: Modify agent descriptions and capabilities
2. **Add Tools**: Integrate additional AWS tools and capabilities
3. **Scale Up**: Deploy to AWS Lambda or ECS for production
4. **Monitor**: Set up CloudWatch monitoring and alerting

## 📚 Documentation Links

- [Agent Squad GitHub](https://github.com/awslabs/agent-squad)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [MCP Protocol](https://modelcontextprotocol.io/)

## 🆘 Support

If you encounter issues:
1. Check this troubleshooting guide
2. Review logs in `logs/` directory
3. Test individual components
4. Verify AWS permissions and access
```

## Implementation Timeline Summary

| Week | Focus | Key Deliverables |
|------|-------|------------------|
| **Week 1** | Agent Squad Integration | ✅ Framework installed<br>✅ Basic orchestrator working<br>✅ 5 specialized agents |
| **Week 2** | Specialized Agents & Tools | ✅ AWS CLI command generation<br>✅ Enhanced agent capabilities<br>✅ Tool integration |
| **Week 3** | Multi-Agent Orchestration | ✅ SupervisorAgent implementation<br>✅ Team coordination<br>✅ Complex workflow handling |
| **Week 4** | MCP Integration | ✅ Knowledge Base integration<br>✅ Enhanced context awareness<br>✅ Production-ready system |

## 🎯 Expected Outcomes

### Before (Current State)
- ❌ Simple pattern matching
- ❌ Limited AWS service support
- ❌ No intelligent routing
- ❌ Basic command generation

### After (Agent Squad Implementation)
- ✅ **Intelligent Intent Classification** - Automatically routes to best agent
- ✅ **5 Specialized AWS Agents** - S3, EC2, Lambda, IAM, Monitoring experts
- ✅ **Multi-Agent Orchestration** - Complex workflows with team coordination
- ✅ **Knowledge Base Integration** - Enhanced context from AWS documentation
- ✅ **Production-Ready Architecture** - Scalable, maintainable, enterprise-grade
- ✅ **Advanced Command Generation** - Context-aware AWS CLI commands
- ✅ **Streaming Responses** - Real-time interaction
- ✅ **Context Management** - Maintains conversation history across agents

## 🚀 Ready to Start?

Would you like me to begin with **Phase 1: Agent Squad Integration** by:

1. Installing the Agent Squad framework
2. Creating the basic orchestrator with 5 specialized agents
3. Updating your backend to use the new system
4. Testing the basic functionality

Just say "Start Phase 1" and I'll begin the implementation!