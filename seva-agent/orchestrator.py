"""
Multi-Agent Orchestrator
"""
import boto3
import json
from typing import Dict, List, Any, Optional
from agents.base_agent import BaseAgent
from agents.s3_agent import S3Agent
from agents.ec2_agent import EC2Agent
from agents.lambda_agent import LambdaAgent
from agents.iam_agent import IAMAgent
from agents.cloudwatch_agent import CloudWatchAgent
from agents.vpc_agent import VPCAgent

class AgentOrchestrator:
    def __init__(self, session: boto3.Session):
        self.session = session
        self.agents = self._initialize_agents()
        self.nova_client = session.client('bedrock-runtime')
    
    def _initialize_agents(self) -> List[BaseAgent]:
        """Initialize all service agents"""
        return [
            S3Agent(self.session),
            EC2Agent(self.session),
            LambdaAgent(self.session),
            IAMAgent(self.session),
            CloudWatchAgent(self.session),
            VPCAgent(self.session)
        ]
    
    def get_available_services(self) -> Dict[str, List[str]]:
        """Get all available services and their capabilities"""
        services = {}
        for agent in self.agents:
            services[agent.get_service_name()] = agent.get_capabilities()
        return services
    
    def route_command(self, command: str) -> Dict[str, Any]:
        """Route command to appropriate agent(s) using Nova for intelligent routing"""
        
        # Find agents that can handle this command
        capable_agents = [agent for agent in self.agents if agent.can_handle(command)]
        
        print(f"DEBUG: Command '{command}'")
        print(f"DEBUG: Capable agents: {[agent.get_service_name() for agent in capable_agents]}")
        
        if not capable_agents:
            # No AWS agent can handle it, use Nova for general response
            return self._call_nova(command)
        
        if len(capable_agents) == 1:
            # Single agent can handle it
            print(f"DEBUG: Single agent {capable_agents[0].get_service_name()} handling command")
            return capable_agents[0].execute(command)
        
        # Multiple agents can handle it - ask Nova to route
        print(f"DEBUG: Multiple agents, using Nova routing")
        return self._nova_route_command(command, capable_agents)
    
    def execute_workflow(self, commands: List[str]) -> List[Dict[str, Any]]:
        """Execute multiple commands with dependency resolution"""
        results = []
        
        for command in commands:
            result = self.route_command(command)
            results.append(result)
            
            # If there's an error, stop the workflow
            if "error" in result:
                break
        
        return results
    
    def _nova_route_command(self, command: str, capable_agents: List[BaseAgent]) -> Dict[str, Any]:
        """Use Nova to intelligently route multi-agent commands"""
        try:
            agent_info = {}
            for agent in capable_agents:
                agent_info[agent.get_service_name()] = agent.get_capabilities()
            
            routing_prompt = f"""
Command: "{command}"

Available agents and their capabilities:
{json.dumps(agent_info, indent=2)}

Analyze this command and choose the MOST APPROPRIATE single agent. Respond with ONLY the service name.

Routing Rules:
- S3 bucket policies, bucket operations, object operations → 's3'
- IAM user policies, role policies, user management → 'iam' 
- EC2 instances, security groups → 'ec2'
- Lambda functions → 'lambda'
- VPC networks, subnets → 'vpc'
- CloudWatch alarms, metrics → 'cloudwatch'

Key Context:
- "bucket policy" = S3 service (not IAM)
- "user policy" = IAM service
- "grant s3 permissions" = IAM service (creates policies for users)
- "list buckets" = S3 service

Choose the agent that directly manages the PRIMARY resource mentioned in the command."""
            
            body = json.dumps({
                "messages": [
                    {
                        "role": "user", 
                        "content": [{"text": routing_prompt}]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 20,
                    "temperature": 0.0
                }
            })
            
            response = self.nova_client.invoke_model(
                modelId="amazon.nova-micro-v1:0",
                body=body
            )
            
            result = json.loads(response["body"].read())
            chosen_service = result["output"]["message"]["content"][0]["text"].strip().lower()
            print(f"DEBUG: Nova chose service: '{chosen_service}'")
            
            # Find the chosen agent
            for agent in capable_agents:
                if agent.get_service_name() == chosen_service:
                    print(f"DEBUG: Executing with {chosen_service} agent")
                    return agent.execute(command)
            
            # Fallback: Use specificity scoring
            return self._score_based_routing(command, capable_agents)
            
        except Exception as e:
            # Fallback to specificity scoring if Nova routing fails
            return self._score_based_routing(command, capable_agents)
    
    def _score_based_routing(self, command: str, capable_agents: List[BaseAgent]) -> Dict[str, Any]:
        """Fallback routing using specificity scoring"""
        scores = []
        
        for agent in capable_agents:
            score = 0
            service = agent.get_service_name()
            
            # Primary resource scoring
            if "bucket" in command.lower() and service == "s3":
                score += 10
            elif "user" in command.lower() and service == "iam":
                score += 10
            elif "instance" in command.lower() and service == "ec2":
                score += 10
            elif "function" in command.lower() and service == "lambda":
                score += 10
            elif "vpc" in command.lower() and service == "vpc":
                score += 10
            elif "alarm" in command.lower() and service == "cloudwatch":
                score += 10
            
            # Action scoring
            capabilities = agent.get_capabilities()
            for capability in capabilities:
                if any(word in command.lower() for word in capability.split('_')):
                    score += 1
            
            scores.append((score, agent))
        
        # Return agent with highest score
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[0][1].execute(command)
            

    
    def _call_nova(self, user_message: str) -> Dict[str, Any]:
        """Call Nova Micro for general questions"""
        try:
            # Add context about available AWS services
            services_info = self.get_available_services()
            context = f"Available AWS services: {list(services_info.keys())}. "
            context += "For AWS operations, suggest specific commands like 'list s3 buckets' or 'list ec2 instances'."
            
            body = json.dumps({
                "messages": [
                    {
                        "role": "user", 
                        "content": [{"text": f"Answer in maximum 3 lines. {context} {user_message}"}]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 200,
                    "temperature": 0.7
                }
            })
            
            response = self.nova_client.invoke_model(
                modelId="amazon.nova-micro-v1:0",
                body=body
            )
            
            result = json.loads(response["body"].read())
            return {
                "service": "nova",
                "operation": "general_query",
                "result": result["output"]["message"]["content"][0]["text"]
            }
        except Exception as e:
            return {
                "service": "nova",
                "operation": "general_query",
                "error": str(e)
            }
    
    def format_response(self, result: Dict[str, Any]) -> str:
        """Format agent response for display"""
        if "error" in result:
            return f"❌ Error: {result['error']}"
        
        service = result.get("service", "unknown")
        operation = result.get("operation", "unknown")
        
        # Add agent identifier header
        agent_header = f"🤖 {service.upper()}Agent responding:\n"
        
        if service == "nova":
            return f"🌆 NovaAgent responding:\n{result.get('result', 'No response')}"
        
        elif service == "s3":
            if operation == "download_object":
                bucket = result.get("bucket")
                key = result.get("key")
                url = result.get("download_url")
                filename = key.split('/')[-1]  # Get just the filename
                return f"{agent_header}⬇️ <a href='{url}' download='{filename}' style='color:#ff9900;text-decoration:underline;'>Click to download {filename}</a> from '{bucket}'"
            
            elif operation in ["move_object", "copy_object"]:
                source_bucket = result.get("source_bucket")
                dest_bucket = result.get("dest_bucket")
                key = result.get("key")
                op_type = "Moved" if operation == "move_object" else "Copied"
                return f"{agent_header}📦 {op_type} '{key}' from '{source_bucket}' to '{dest_bucket}'"
            
            elif operation == "list_buckets":
                buckets = result.get("result", [])
                if not buckets:
                    return "No S3 buckets found"
                
                response = f"{agent_header}📦 Found {result.get('count', 0)} S3 buckets:\n"
                for bucket in buckets:
                    response += f"• {bucket['name']} (created: {bucket['created'][:10]})\n"
                return response
            
            elif operation == "list_objects":
                objects = result.get("result", [])
                bucket = result.get("bucket", "unknown")
                
                if not objects:
                    return f"{agent_header}📦 Bucket '{bucket}' is empty"
                
                response = f"{agent_header}📁 Found {result.get('count', 0)} objects in '{bucket}':\n"
                for obj in objects:
                    size_mb = obj['size'] / 1024 / 1024
                    response += f"• {obj['key']} ({size_mb:.2f} MB)\n"
                return response
        
        elif service == "ec2":
            if operation == "list_instances":
                instances = result.get("result", [])
                if not instances:
                    return "No EC2 instances found"
                
                response = f"{agent_header}🖥️ Found {result.get('count', 0)} EC2 instances:\n"
                for instance in instances:
                    response += f"• {instance['id']} ({instance['name']}) - {instance['state']}\n"
                return response
        
        elif service == "lambda":
            if operation == "list_functions":
                functions = result.get("result", [])
                if not functions:
                    return "No Lambda functions found"
                
                response = f"{agent_header}⚡ Found {result.get('count', 0)} Lambda functions:\n"
                for func in functions:
                    response += f"• {func['name']} ({func['runtime']}) - {func['memory']}MB\n"
                return response
        
        elif service == "iam":
            if operation == "list_users":
                users = result.get("result", [])
                if not users:
                    return "No IAM users found"
                
                response = f"{agent_header}👥 Found {result.get('count', 0)} IAM users:\n"
                for user in users:
                    response += f"• {user['name']} (created: {user['created'][:10]})\n"
                return response
            elif operation == "list_roles":
                roles = result.get("result", [])
                response = f"{agent_header}🔐 Found {result.get('count', 0)} IAM roles:\n"
                for role in roles:
                    response += f"• {role['name']}\n"
                return response
            elif operation == "grant_s3_permissions":
                return f"{agent_header}✅ {result.get('result', 'S3 permissions granted')}"
        
        elif service == "cloudwatch":
            if operation == "list_alarms":
                alarms = result.get("result", [])
                if not alarms:
                    return "No CloudWatch alarms found"
                
                response = f"{agent_header}🚨 Found {result.get('count', 0)} CloudWatch alarms:\n"
                for alarm in alarms:
                    response += f"• {alarm['name']} - {alarm['state']}\n"
                return response
        
        elif service == "vpc":
            if operation == "list_vpcs":
                vpcs = result.get("result", [])
                if not vpcs:
                    return "No VPCs found"
                
                response = f"{agent_header}🌐 Found {result.get('count', 0)} VPCs:\n"
                for vpc in vpcs:
                    default = " (default)" if vpc['is_default'] else ""
                    response += f"• {vpc['id']} ({vpc['name']}) - {vpc['cidr']}{default}\n"
                return response
            elif operation == "list_subnets":
                subnets = result.get("result", [])
                response = f"{agent_header}🔗 Found {result.get('count', 0)} subnets:\n"
                for subnet in subnets:
                    response += f"• {subnet['id']} ({subnet['name']}) - {subnet['cidr']} in {subnet['az']}\n"
                return response
        

        
        elif service == "s3" and operation == "get_bucket_size":
            bucket = result.get("bucket")
            stats = result.get("result", {})
            size = stats.get('total_size_gb', 'Unknown')
            count = stats.get('object_count', 'Unknown')
            if isinstance(size, str) and "Access denied" in size:
                return f"{agent_header}❌ Cannot access bucket '{bucket}': {stats.get('error', 'Permission denied')}"
            return f"{agent_header}📊 Bucket '{bucket}' size: {size} GB ({count} objects)"
        
        elif service == "s3" and operation == "analyze_storage_class":
            bucket = result.get("bucket")
            stats = result.get("result", {})
            total = result.get("total_objects", 0)
            
            if not stats:
                return f"{agent_header}📉 No objects found in '{bucket}'"
            
            response = f"{agent_header}📉 Storage analysis for '{bucket}' ({total} objects):\n"
            for storage_class, data in stats.items():
                size_mb = data['size'] / (1024 * 1024)
                response += f"• {storage_class}: {data['count']} objects ({size_mb:.2f} MB)\n"
            return response
        
        elif service == "s3" and operation == "get_bucket_info":
            bucket = result.get("bucket")
            info = result.get("result", {})
            return f"{agent_header}📝 Bucket '{bucket}' info:\n• Region: {info.get('region')}\n• Has Policy: {info.get('has_policy')}\n• Owner: {info.get('owner')}"
        
        elif service == "s3" and operation == "test_bucket_access":
            buckets = result.get("result", [])
            accessible = [b for b in buckets if b.get('accessible')]
            
            response = f"{agent_header}🔍 Bucket access test ({len(accessible)} accessible out of {len(buckets)}):\n"
            for bucket in buckets:
                status = "✅" if bucket.get('accessible') else "❌"
                response += f"{status} {bucket['name']}\n"
            return response
        
        elif service == "s3" and operation == "get_bucket_policy":
            bucket = result.get("bucket")
            policy_info = result.get("result", {})
            
            if not policy_info.get("has_policy"):
                return f"{agent_header}📜 Bucket '{bucket}' has no policy configured"
            
            policy = policy_info.get("policy", {})
            statements = policy.get("Statement", [])
            
            response = f"{agent_header}📜 Bucket '{bucket}' policy ({len(statements)} statements):\n"
            for i, stmt in enumerate(statements, 1):
                effect = stmt.get('Effect', 'Unknown')
                actions = stmt.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]
                response += f"• Statement {i}: {effect} - {', '.join(actions[:3])}{'...' if len(actions) > 3 else ''}\n"
            
            return response
        
        elif service == "s3" and operation == "delete_object":
            bucket = result.get("bucket")
            key = result.get("key")
            return f"{agent_header}🗑️ Deleted '{key}' from bucket '{bucket}'"
        
        elif service == "s3" and operation in ["upload_file_to_s3", "download_file_from_s3"]:
            bucket = result.get("bucket")
            key = result.get("key")
            local_path = result.get("local_path")
            if operation == "upload_file_to_s3":
                return f"{agent_header}⬆️ Uploaded '{key}' from {local_path} to bucket '{bucket}'"
            else:
                return f"{agent_header}⬇️ Downloaded '{key}' from bucket '{bucket}' to {local_path}"
        

        # Default formatting
        return f"{agent_header}✅ {operation}: {result.get('result', 'Success')}"