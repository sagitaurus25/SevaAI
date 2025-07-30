import json
import os
from typing import Dict, Any

class CommandGenerator:
    def __init__(self):
        # AWS CLI command templates
        self.command_templates = {
            "list_buckets": "aws s3 ls",
            "list_files": "aws s3 ls s3://{bucket_name}/",
            "list_instances": "aws ec2 describe-instances --region us-east-1 --output table --query Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,Placement.AvailabilityZone,Tags[?Key=='Name'].Value|[0]]",
            "list_functions": "aws lambda list-functions --query 'Functions[*].[FunctionName,Runtime,LastModified]' --output table"
        }
    
    async def generate_command(self, intent_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AWS CLI command based on intent and parameters"""
        try:
            intent = intent_result.get("intent")
            parameters = intent_result.get("parameters", {})
            
            if intent == "list_resources":
                return self._generate_list_command(parameters)
            
            return {
                "success": False,
                "error": f"Don't know how to handle intent: {intent}"
            }
            
        except Exception as e:
            print(f"Error generating command: {e}")
            return {
                "success": False,
                "error": f"Failed to generate command: {str(e)}"
            }
    
    def _generate_list_command(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate list commands"""
        resource_type = parameters.get("resource_type")
        
        if resource_type == "buckets":
            return {
                "success": True,
                "command": self.command_templates["list_buckets"],
                "type": "aws_cli",
                "description": "List all S3 buckets"
            }
        
        elif resource_type == "files":
            bucket_name = parameters.get("bucket_name")
            if bucket_name:
                return {
                    "success": True,
                    "command": self.command_templates["list_files"].format(bucket_name=bucket_name),
                    "type": "aws_cli",
                    "description": f"List files in bucket {bucket_name}"
                }
            else:
                return {
                    "success": False,
                    "error": "Bucket name is required to list files"
                }
        
        elif resource_type == "instances":
            return {
                "success": True,
                "command": self.command_templates["list_instances"],
                "type": "aws_cli",
                "description": "List EC2 instances"
            }
        
        elif resource_type == "functions":
            return {
                "success": True,
                "command": self.command_templates["list_functions"],
                "type": "aws_cli",
                "description": "List Lambda functions"
            }
        
        return {
            "success": False,
            "error": f"Unknown resource type: {resource_type}"
        }