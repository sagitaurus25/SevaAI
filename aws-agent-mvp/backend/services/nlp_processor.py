import boto3
import json
import os
from typing import Dict, Any, List
import re

class NLPProcessor:
    def __init__(self):
        # Initialize without Bedrock for testing - we'll add it later
        self.use_bedrock = os.getenv('USE_BEDROCK', 'false').lower() == 'true'
        
        if self.use_bedrock:
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
            self.model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
        
        # Define intent patterns for simple matching
        self.intent_patterns = {
            "list_resources": [
                r"list.*buckets?",
                r"show.*buckets?",
                r"get.*buckets?",
                r"list.*files?",
                r"show.*files?",
                r"list.*instances?",
                r"show.*instances?",
                r"list.*functions?",
                r"show.*functions?",
                r"list.*lambda",
                r"show.*lambda"
            ],
            "get_status": [
                r"status.*",
                r"health.*",
                r"running.*",
                r"state.*"
            ],
            "create_resource": [
                r"create.*",
                r"make.*",
                r"new.*",
                r"launch.*"
            ],
            "delete_resource": [
                r"delete.*",
                r"remove.*",
                r"destroy.*",
                r"terminate.*"
            ]
        }
    
    async def classify_intent(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Classify user intent and extract parameters"""
        try:
            # Use pattern matching for now (we'll enhance with Bedrock later)
            result = self._pattern_match_intent(message)
            return result
            
        except Exception as e:
            print(f"Error in intent classification: {e}")
            return {
                "intent": "unclear",
                "confidence": 0.0,
                "parameters": {},
                "needs_clarification": True,
                "clarification_question": "I'm not sure what you'd like me to do. Could you please rephrase your request?"
            }
    
    def _pattern_match_intent(self, message: str) -> Dict[str, Any]:
        """Pattern-based intent matching"""
        message_lower = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    parameters = self._extract_parameters(message, intent)
                    needs_clarification = self._check_needs_clarification(intent, parameters)
                    
                    return {
                        "intent": intent,
                        "confidence": 0.8,
                        "parameters": parameters,
                        "needs_clarification": needs_clarification,
                        "clarification_question": self._generate_clarification_question(intent, parameters) if needs_clarification else None
                    }
        
        return {
            "intent": "unclear", 
            "confidence": 0.0, 
            "parameters": {}, 
            "needs_clarification": True,
            "clarification_question": "I didn't understand that. Try asking me to 'list my buckets' or 'show my EC2 instances'."
        }
    
    def _extract_parameters(self, message: str, intent: str) -> Dict[str, Any]:
        """Extract parameters from message"""
        parameters = {}
        message_lower = message.lower()
        
        # Extract AWS service type
        aws_services = ["s3", "ec2", "lambda", "ecs", "iam", "cloudformation", "rds"]
        for service in aws_services:
            if service in message_lower:
                parameters["service"] = service
                break
        
        # Extract resource types
        if intent == "list_resources":
            if "bucket" in message_lower:
                parameters["resource_type"] = "buckets"
            elif "file" in message_lower:
                parameters["resource_type"] = "files"
            elif "instance" in message_lower:
                parameters["resource_type"] = "instances"
            elif "function" in message_lower or "lambda" in message_lower:
                parameters["resource_type"] = "functions"
        
        # Extract bucket names
        bucket_match = re.search(r'bucket[:\s]+([a-zA-Z0-9\-\.]+)', message)
        if bucket_match:
            parameters["bucket_name"] = bucket_match.group(1)
        
        return parameters
    
    def _check_needs_clarification(self, intent: str, parameters: Dict[str, Any]) -> bool:
        """Check if clarification is needed"""
        if intent == "list_resources":
            resource_type = parameters.get("resource_type")
            if resource_type == "files" and not parameters.get("bucket_name"):
                return True
        return False
    
    def _generate_clarification_question(self, intent: str, parameters: Dict[str, Any]) -> str:
        """Generate clarification question"""
        if intent == "list_resources" and parameters.get("resource_type") == "files":
            return "Which S3 bucket would you like me to list files from?"
        return "Could you provide more details about what you'd like me to do?"
    
    async def generate_clarification_question(self, intent_result: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate clarification question"""
        if intent_result.get("clarification_question"):
            return intent_result["clarification_question"]
        return "Could you provide more specific details?"
    
    async def generate_response(self, execution_result: Dict[str, Any], intent_result: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate human-readable response"""
        if execution_result.get("success"):
            result_data = execution_result.get("data", "")
            command = execution_result.get("command", "")
            
            # Simple response generation for now
            if "No buckets found" in result_data or not result_data.strip():
                return "I didn't find any results. This could mean you have no resources of that type, or there might be a permissions issue."
            
            return f"Here's what I found:\n\n{result_data}\n\nCommand executed: `{command}`"
        else:
            error_msg = execution_result.get("error", "Unknown error")
            return f"I encountered an error: {error_msg}"