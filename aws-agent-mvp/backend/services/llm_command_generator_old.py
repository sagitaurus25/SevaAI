import boto3
import json
import os
import re
from typing import Dict, Any, List, Optional

class LLMCommandGenerator:
    def __init__(self):
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        # Use correct Nova model IDs
        self.nova_micro_model = 'us.amazon.nova-micro-v1:0'
        self.nova_pro_model = 'us.amazon.nova-pro-v1:0'
        
        # Safety patterns - commands we definitely allow
        self.safe_command_patterns = [
            r'^aws s3 ls',
            r'^aws ec2 describe-',
            r'^aws lambda list-',
            r'^aws lambda get-',
            r'^aws iam list-',
            r'^aws cloudformation list-',
            r'^aws cloudformation describe-',
            r'^aws rds describe-',
            r'^aws ecs list-',
            r'^aws ecs describe-'
        ]
        
        # Dangerous patterns - commands we block
        self.dangerous_patterns = [
            r'remove',
            r'destroy',
            r'put-',
            r'create-',
            r'modify-',
            r'update-',
            r'attach-',
            r'detach-'
        ]
    
    async def generate_aws_command(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate AWS CLI command from natural language using Nova LLM"""
        try:
            # Determine complexity to choose appropriate model
            model_id = self._select_model(user_query)
            
            # Generate the command
            command_result = await self._call_nova_llm(user_query, model_id, context)
            
            # Validate and sanitize the command
            validated_result = self._validate_command(command_result)
            
            return validated_result
            
        except Exception as e:
            print(f"Error in generate_aws_command: {e}")
            return {
                "success": False,
                "error": f"Failed to generate command: {str(e)}",
                "fallback_suggestion": "Try a simpler request like 'list my S3 buckets'"
            }
    
    def _select_model(self, query: str) -> str:
        """Select appropriate Nova model based on query complexity"""
        complex_indicators = [
            'filter', 'where', 'only', 'except', 'between',
            'before', 'after', 'greater', 'less', 'count',
            'sum', 'average', 'group by', 'sort by',
            'created in', 'modified in', 'updated in',
            'from', 'since', 'until', 'during'
        ]
        
        query_lower = query.lower()
        print(f" Query: '{query_lower}'")
        for indicator in complex_indicators:
            if indicator in query_lower:
                print(f"Complex query detected: '{indicator}' -> using Nova Pro") 
                return self.nova_pro_model

            print(f" No Complex indicators found -> Using Nova Micro")
            return self.nova_micro_model
    
    async def _call_nova_llm(self, user_query: str, model_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call Nova LLM to generate AWS CLI command using correct API format"""
        
        # Build context-aware prompt
        conversation_history = ""
        if context and context.get("conversation_history"):
            recent_history = context["conversation_history"][-3:]  # Last 3 exchanges
            conversation_history = "\n".join([
                f"{entry['role']}: {entry['content']}" 
                for entry in recent_history
            ])
        
        prompt = self._build_command_generation_prompt(user_query, conversation_history)
        
        try:
            # Use correct Nova API format based on official docs
            request_body = {
                "schemaVersion": "messages-v1",
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 1000,
                    "temperature": 0.1
                }
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            llm_response = response_body['output']['message']['content'][0]['text']
            # ADD DEBUG LOGGING HERE
            print(f"🤖 RAW LLM RESPONSE: {llm_response}")
            print(f"📏 RESPONSE LENGTH: {len(llm_response)}")
        
            parsed = self._parse_llm_response(llm_response)
            print(f"🔍 PARSED RESULT: {parsed}")
        
            return parsed
        
            
        except Exception as e:
            print(f"Nova LLM call error: {e}")
            raise Exception(f"Nova LLM call failed: {str(e)}")
    
    def _build_command_generation_prompt(self, user_query: str, conversation_history: str = "") -> str:
        """Build simple, clear prompt for AWS CLI command generation"""
    
        prompt = f"""You are an AWS CLI expert. Convert this natural language request into a safe AWS CLI command.

USER REQUEST: "{user_query}"

Generate ONLY a JSON response for this specific request:

{{{{
    "success": true,
    "command": "aws [service] [action] [parameters]",
    "description": "Brief description of what this command does"
}}}}

Rules:
1. Only generate read-only commands (list, describe, get)
2. Use proper AWS CLI syntax
3. Add --output table for formatting
4. For date filters, use proper query syntax

Examples:
- "list s3 buckets" → aws s3 ls
- "list s3 buckets created in 2024" → aws s3api list-buckets --query 'Buckets[?CreationDate >= `2024-01-01` && CreationDate < `2025-01-01`]' --output table
- "list lambda functions" → aws lambda list-functions --output table

Now generate the command for: "{user_query}"
"""
    
       
        return prompt
    
    def _parse_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse and extract JSON from LLM response"""
        try:
            # Extract JSON from response (handles cases where LLM adds extra text)
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed_response = json.loads(json_str)
                return parsed_response
            else:
                # If no JSON found, try to extract command directly
                lines = llm_response.strip().split('\n')
                for line in lines:
                    if line.strip().startswith('aws '):
                        return {
                            "success": True,
                            "command": line.strip(),
                            "description": "Command extracted from LLM response",
                            "service": "unknown",
                            "safety_level": "safe",
                            "estimated_cost": "free",
                            "expected_output": "Various results"
                        }
                
                return {
                    "success": False,
                    "error": "Could not parse valid AWS command from response",
                    "llm_response": llm_response
                }
                
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return {
                "success": False,
                "error": f"Invalid JSON in LLM response: {str(e)}",
                "llm_response": llm_response
            }
        except Exception as e:
            print(f"Parse error: {e}")
            return {
                "success": False,
                "error": f"Failed to parse response: {str(e)}",
                "llm_response": llm_response
            }
    
    def _validate_command(self, command_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated command for safety and correctness"""
        if not command_result.get("success"):
            return command_result
        
        command = command_result.get("command", "").strip()
        
        # Check if command is safe
        if not self._is_safe_command(command):
            return {
                "success": False,
                "error": "Generated command is not allowed for safety reasons",
                "dangerous_command": command,
                "suggestion": "Try a read-only operation like 'list' or 'describe'"
            }
        
        # Validate command structure
        if not command.startswith('aws '):
            return {
                "success": False,
                "error": "Invalid AWS CLI command format",
                "suggestion": "Commands must start with 'aws'"
            }
        
        # Add region if not specified (for applicable services)
        command = self._ensure_region(command)
        command_result["command"] = command
        
        return command_result
    
    def _is_safe_command(self, command: str) -> bool:
        """Check if command is safe to execute"""
        command_lower = command.lower()
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command_lower):
                return False
        
        # Check for safe patterns
        for pattern in self.safe_command_patterns:
            if re.match(pattern, command_lower):
                return True
        
        # Additional safety checks
        safe_actions = ['list', 'describe', 'get', 'show', 'ls']
        command_parts = command_lower.split()
        
        if len(command_parts) >= 3:
            service = command_parts[1]
            action = command_parts[2]
            
            # Allow if action starts with safe words
            return any(action.startswith(safe_action) for safe_action in safe_actions)
        
        return False
    
    def _ensure_region(self, command: str) -> str:
        """Add region parameter if not present and applicable"""
        if '--region' not in command:
            # Services that benefit from explicit region
            regional_services = ['ec2', 'rds', 'lambda', 'ecs']
            command_parts = command.split()
            
            if len(command_parts) >= 2 and command_parts[1] in regional_services:
                # Insert region after service and action
                insert_pos = 3 if len(command_parts) >= 3 else len(command_parts)
                command_parts.insert(insert_pos, '--region')
                command_parts.insert(insert_pos + 1, os.getenv('AWS_REGION', 'us-east-1'))
                command = ' '.join(command_parts)
        
        return command