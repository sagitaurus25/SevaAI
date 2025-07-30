import boto3
import json
import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

class LLMCommandGenerator:
    def __init__(self):
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.nova_micro_model = 'us.amazon.nova-micro-v1:0'
        self.nova_pro_model = 'us.amazon.nova-pro-v1:0'
        
        # Intelligent command patterns
        self.command_patterns = {
            # S3 Patterns
            "s3_list_all": {
                "patterns": [r"list.*s3.*bucket", r"show.*s3.*bucket", r"list.*bucket", r"show.*bucket"],
                "command": "aws s3 ls",
                "description": "Lists all S3 buckets in your account"
            },
            "s3_list_filtered": {
                "patterns": [r"list.*bucket.*created.*(\d{4})", r"show.*bucket.*created.*(\d{4})", r"bucket.*from.*(\d{4})"],
                "command_template": "aws s3api list-buckets --query 'Buckets[?CreationDate >= `{year}-01-01` && CreationDate < `{next_year}-01-01`].[Name,CreationDate]' --output table",
                "description": "Lists S3 buckets created in {year}"
            },
            "s3_list_recent": {
                "patterns": [r"list.*bucket.*recent", r"show.*bucket.*recent", r"newest.*bucket", r"latest.*bucket"],
                "command": "aws s3api list-buckets --query 'reverse(sort_by(Buckets, &CreationDate))[:10].[Name,CreationDate]' --output table",
                "description": "Lists 10 most recently created S3 buckets"
            },
            # Add these new patterns after the existing S3 patterns:

            "s3_list_objects": {
                "patterns": [
                    r"list.*objects.*in\s+([a-zA-Z0-9\-\.]+)",
                    r"show.*objects.*in\s+([a-zA-Z0-9\-\.]+)", 
                    r"list.*files.*in\s+([a-zA-Z0-9\-\.]+)",
                    r"show.*files.*in\s+([a-zA-Z0-9\-\.]+)"
                ],
                "command_template": "aws s3 ls s3://{bucket}/",
                "description": "Lists objects in S3 bucket '{bucket}'"
            },

            "s3_list_objects_recursive": {
                "patterns": [
                    r"list.*all.*objects.*in\s+([a-zA-Z0-9\-\.]+)",
                    r"show.*all.*objects.*in\s+([a-zA-Z0-9\-\.]+)",
                    r"list.*objects.*recursively.*in\s+([a-zA-Z0-9\-\.]+)"
                ],
                "command_template": "aws s3 ls s3://{bucket}/ --recursive",
                "description": "Lists all objects recursively in S3 bucket '{bucket}'"
            },

            "s3_list_objects_simple": {
                "patterns": [
                    r"list.*objects?.*['\"]*([a-zA-Z0-9\-\.]+)['\"]*",
                    r"show.*objects?.*['\"]*([a-zA-Z0-9\-\.]+)['\"]*"
                ],
                "command_template": "aws s3 ls s3://{bucket}/",
                "description": "Lists top-level objects in S3 bucket '{bucket}'"
            },
            
            # EC2 Patterns
            "ec2_list_all": {
                "patterns": [r"list.*ec2.*instance", r"show.*ec2.*instance", r"list.*instance", r"show.*instance", r"list.*server", r"show.*server"],
                "command": "aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,Placement.AvailabilityZone,Tags[?Key==`Name`].Value|[0]]' --output table",
                "description": "Lists all EC2 instances in your account"
            },
            "ec2_list_running": {
                "patterns": [r"list.*running.*instance", r"show.*running.*instance", r"running.*ec2", r"active.*instance"],
                "command": "aws ec2 describe-instances --filters Name=instance-state-name,Values=running --query 'Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,Placement.AvailabilityZone,Tags[?Key==`Name`].Value|[0]]' --output table",
                "description": "Lists running EC2 instances"
            },
            "ec2_list_stopped": {
                "patterns": [r"list.*stopped.*instance", r"show.*stopped.*instance", r"stopped.*ec2"],
                "command": "aws ec2 describe-instances --filters Name=instance-state-name,Values=stopped --query 'Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,Placement.AvailabilityZone,Tags[?Key==`Name`].Value|[0]]' --output table",
                "description": "Lists stopped EC2 instances"
            },
            
            # Lambda Patterns
            "lambda_list_all": {
                "patterns": [r"list.*lambda.*function", r"show.*lambda.*function", r"list.*function", r"show.*function"],
                "command": "aws lambda list-functions --query 'Functions[*].[FunctionName,Runtime,LastModified,CodeSize]' --output table",
                "description": "Lists all Lambda functions in your account"
            },
            "lambda_list_filtered": {
                "patterns": [r"list.*function.*created.*(\d{4})", r"show.*function.*created.*(\d{4})", r"function.*from.*(\d{4})"],
                "command_template": "aws lambda list-functions --query 'Functions[?LastModified >= `{year}-01-01` && LastModified < `{next_year}-01-01`].[FunctionName,Runtime,LastModified]' --output table",
                "description": "Lists Lambda functions last modified in {year}"
            },
            "lambda_by_runtime": {
                "patterns": [r"list.*function.*python", r"show.*function.*python", r"python.*function"],
                "command": "aws lambda list-functions --query 'Functions[?starts_with(Runtime, `python`)].[FunctionName,Runtime,LastModified]' --output table",
                "description": "Lists Python Lambda functions"
            },
            
            # IAM Patterns
            "iam_list_users": {
                "patterns": [r"list.*iam.*user", r"show.*iam.*user", r"list.*user", r"show.*user"],
                "command": "aws iam list-users --query 'Users[*].[UserName,CreateDate,PasswordLastUsed]' --output table",
                "description": "Lists IAM users in your account"
            },
            
            # RDS Patterns
            "rds_list_instances": {
                "patterns": [r"list.*rds.*instance", r"show.*rds.*instance", r"list.*database", r"show.*database"],
                "command": "aws rds describe-db-instances --query 'DBInstances[*].[DBInstanceIdentifier,DBInstanceStatus,Engine,DBInstanceClass]' --output table",
                "description": "Lists RDS database instances"
            }
        }
    
    async def generate_aws_command(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate AWS CLI command using intelligent pattern matching first, then LLM fallback"""
        try:
            print(f"🔍 Analyzing query: '{user_query}'")
            
            # First, try intelligent pattern matching
            pattern_result = self._match_intelligent_patterns(user_query)
            if pattern_result["success"]:
                print(f"✅ Pattern match found: {pattern_result['pattern_name']}")
                return pattern_result
            
            print("📝 No pattern match, trying LLM...")
            # If no pattern matches, try LLM (but expect it might fail)
            try:
                model_id = self._select_model(user_query)
                command_result = await self._call_nova_llm(user_query, model_id, context)
                validated_result = self._validate_command(command_result)
                
                # Extra validation: make sure LLM result makes sense
                if self._validate_llm_response(user_query, validated_result):
                    print("✅ LLM generated valid command")
                    return validated_result
                else:
                    print("❌ LLM response doesn't match query")
                    return self._generate_fallback_response(user_query)
                    
            except Exception as e:
                print(f"❌ LLM failed: {e}")
                return self._generate_fallback_response(user_query)
            
        except Exception as e:
            print(f"❌ Error in generate_aws_command: {e}")
            return {
                "success": False,
                "error": f"Failed to generate command: {str(e)}",
                "suggestion": "Try a more specific request like 'list my S3 buckets' or 'show EC2 instances'"
            }
    
    def _match_intelligent_patterns(self, user_query: str) -> Dict[str, Any]:   
        """Match user query against intelligent patterns"""
        query_lower = user_query.lower().strip()
        print(f"🔍 Matching against: '{query_lower}'")
        
        for pattern_name, pattern_config in self.command_patterns.items():
            for pattern in pattern_config["patterns"]:
                match = re.search(pattern, query_lower)
                if match:
                    print(f"✅ Pattern: '{pattern}' matched!")
                    print(f"📝 Captured groups: {match.groups()}")

                    # Handle templates with captured groups
                    if "command_template" in pattern_config:
                        if match.groups():
                            if pattern_name.startswith("s3_list_filtered"):
                                # Year-based filtering
                                year = match.group(1)
                                next_year = str(int(year) + 1)
                                command = pattern_config["command_template"].format(year=year, next_year=next_year)
                                description = pattern_config["description"].format(year=year)
                            elif pattern_name.startswith("s3_list_objects"):
                                # Bucket-based object listing
                                bucket = match.group(1)
                                print(f"🪣 Extracted bucket: '{bucket}'")
                                command = pattern_config["command_template"].format(bucket=bucket)
                                description = pattern_config["description"].format(bucket=bucket)
                            elif pattern_name.startswith("lambda_list_filtered"):
                                # Lambda year filtering
                                year = match.group(1)
                                next_year = str(int(year) + 1)
                                command = pattern_config["command_template"].format(year=year, next_year=next_year)
                                description = pattern_config["description"].format(year=year)
                            else:
                                continue  # Pattern didn't match expected format
                        else:
                            continue  # Pattern didn't capture required groups
                    else:
                        command = pattern_config["command"]
                        description = pattern_config["description"]
                    
                    # Add region for applicable services
                    command = self._ensure_region(command)
                    
                    return {
                        "success": True,
                        "command": command,
                        "description": description,
                        "service": self._extract_service(command),
                        "pattern_name": pattern_name,
                        "method": "pattern_matching"
                    }
        
        return {"success": False}
    
    def _extract_service(self, command: str) -> str:
        """Extract AWS service from command"""
        parts = command.split()
        if len(parts) >= 2:
            return parts[1]  # aws [service] ...
        return "aws"
    
    def _validate_llm_response(self, user_query: str, llm_result: Dict[str, Any]) -> bool:
        """Validate that LLM response actually matches the user query"""
        if not llm_result.get("success"):
            return False
        
        command = llm_result.get("command", "").lower()
        query_lower = user_query.lower()
        
        # Check if the command service matches the query intent
        if "bucket" in query_lower or "s3" in query_lower:
            return "s3" in command
        elif "instance" in query_lower or "ec2" in query_lower or "server" in query_lower:
            return "ec2" in command
        elif "function" in query_lower or "lambda" in query_lower:
            return "lambda" in command
        elif "database" in query_lower or "rds" in query_lower:
            return "rds" in command
        elif "user" in query_lower or "iam" in query_lower:
            return "iam" in command
        
        return True  # If we can't determine, assume it's valid
    
    def _generate_fallback_response(self, user_query: str) -> Dict[str, Any]:
        """Generate helpful fallback response when everything else fails"""
        query_lower = user_query.lower()
        
        suggestions = []
        if "bucket" in query_lower or "s3" in query_lower:
            suggestions = [
                "list my S3 buckets",
                "show S3 buckets created in 2024",
                "list recent S3 buckets"
            ]
        elif "instance" in query_lower or "ec2" in query_lower:
            suggestions = [
                "list my EC2 instances", 
                "show running EC2 instances",
                "list stopped EC2 instances"
            ]
        elif "function" in query_lower or "lambda" in query_lower:
            suggestions = [
                "list my Lambda functions",
                "show Lambda functions created in 2024",
                "list Python Lambda functions"
            ]
        else:
            suggestions = [
                "list my S3 buckets",
                "show my EC2 instances", 
                "list my Lambda functions"
            ]
        
        return {
            "success": False,
            "error": f"I couldn't understand '{user_query}'. The AI model seems to be having issues.",
            "suggestion": f"Try one of these instead: {', '.join(suggestions)}"
        }
    
    def _select_model(self, query: str) -> str:
        """Select appropriate Nova model (keeping for future use)"""
        return self.nova_micro_model  # Always use micro since patterns handle complexity
    
    async def _call_nova_llm(self, user_query: str, model_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call Nova LLM (keeping but simplified since patterns are primary)"""
        prompt = f"""Convert this AWS request to a safe CLI command: "{user_query}"

Return JSON only:
{{{{
    "success": true,
    "command": "aws service action --parameters",
    "description": "what this does"
}}}}"""
        
        try:
            request_body = {
                "schemaVersion": "messages-v1",
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": 500, "temperature": 0.1}
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            llm_response = response_body['output']['message']['content'][0]['text']
            
            return self._parse_llm_response(llm_response)
            
        except Exception as e:
            raise Exception(f"Nova LLM call failed: {str(e)}")
    
    def _parse_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse LLM response"""
        try:
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"success": False, "error": "No valid JSON found"}
        except Exception as e:
            return {"success": False, "error": f"Parse error: {str(e)}"}
    
    def _validate_command(self, command_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated command for safety"""
        if not command_result.get("success"):
            return command_result
        
        command = command_result.get("command", "").strip()
        
        # Safety check
        dangerous_words = ['delete', 'terminate', 'remove', 'destroy', 'create', 'modify', 'update']
        if any(word in command.lower() for word in dangerous_words):
            return {
                "success": False,
                "error": "Command blocked for safety",
                "suggestion": "Only read-only operations are allowed"
            }
        
        # Ensure region
        command = self._ensure_region(command)
        command_result["command"] = command
        
        return command_result
    
    def _ensure_region(self, command: str) -> str:
        """Add region if needed"""
        if '--region' not in command:
            regional_services = ['ec2', 'rds', 'lambda', 'ecs']
            parts = command.split()
            if len(parts) >= 2 and parts[1] in regional_services:
                # Insert region after service
                insert_pos = 3 if len(parts) >= 3 else len(parts)
                parts.insert(insert_pos, '--region')
                parts.insert(insert_pos + 1, os.getenv('AWS_REGION', 'us-east-1'))
                command = ' '.join(parts)
        return command