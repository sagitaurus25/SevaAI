import subprocess
import json
import os
import asyncio
from typing import Dict, Any
import shlex

class ExecutionEngine:
    def __init__(self):
        self.safe_commands = [
            "aws s3 ls",
            "aws ec2 describe-instances",
            "aws lambda list-functions",
            "aws iam list-users",
            "aws cloudformation list-stacks"
        ]
    
    async def execute_command(self, command_spec: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute AWS CLI command safely"""
        try:
            if not command_spec.get("success"):
                return {
                    "success": False,
                    "error": command_spec.get("error", "Command generation failed"),
                    "data": ""
                }
            
            command = command_spec.get("command", "")
            
            # Safety check
            if not self._is_safe_command(command):
                return {
                    "success": False,
                    "error": f"Command not allowed for safety reasons: {command}",
                    "data": ""
                }
            
            # Execute the command
            result = await self._execute_aws_cli(command)
            
            return {
                "success": result["success"],
                "data": result["output"],
                "error": result.get("error", ""),
                "command": command,
                "summary": f"Executed: {command}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution failed: {str(e)}",
                "data": "",
                "command": command_spec.get("command", "")
            }
    
    def _is_safe_command(self, command: str) -> bool:
        """Check if command is safe to execute"""
        # Only allow read-only operations for now
        safe_patterns = [
            "aws s3 ls",
            "aws ec2 describe-",
            "aws lambda list-",
            "aws iam list-",
            "aws cloudformation list-",
            "aws cloudformation describe-"
        ]
        
        command_lower = command.lower().strip()
        
        # Check against safe patterns
        for pattern in safe_patterns:
            if command_lower.startswith(pattern.lower()):
                return True
        
        return False
    
    async def _execute_aws_cli(self, command: str) -> Dict[str, Any]:
        """Execute AWS CLI command"""
        try:
            # Split command safely
            cmd_parts = shlex.split(command)
            
            # Run the command
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8').strip()
                if not output:
                    output = "Command executed successfully but returned no data."
                
                return {
                    "success": True,
                    "output": output
                }
            else:
                error_msg = stderr.decode('utf-8').strip()
                return {
                    "success": False,
                    "output": "",
                    "error": f"AWS CLI error: {error_msg}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Failed to execute command: {str(e)}"
            }