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