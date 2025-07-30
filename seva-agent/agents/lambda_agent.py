"""
Lambda Service Agent
"""
from .base_agent import BaseAgent
from typing import Dict, List, Any

class LambdaAgent(BaseAgent):
    def get_service_name(self) -> str:
        return "lambda"
    
    def get_capabilities(self) -> List[str]:
        return [
            "list_functions",
            "invoke_function",
            "get_function_logs",
            "create_function",
            "delete_function"
        ]
    
    def can_handle(self, command: str) -> bool:
        lambda_keywords = ["lambda", "function", "serverless"]
        return any(keyword in command.lower() for keyword in lambda_keywords)
    
    def execute(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        command_lower = command.lower()
        
        try:
            if "list" in command_lower and "function" in command_lower:
                return self._list_functions()
            elif "invoke" in command_lower and "function" in command_lower:
                function_name = self._extract_function_name(command)
                return self._invoke_function(function_name)
            elif "logs" in command_lower or "log" in command_lower:
                function_name = self._extract_function_name(command)
                return self._get_function_logs(function_name)
            else:
                return {"error": f"Lambda command not recognized: {command}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_function_name(self, command: str) -> str:
        words = command.split()
        for i, word in enumerate(words):
            if "function" in word.lower() and i + 1 < len(words):
                return words[i + 1]
        return None
    
    def _list_functions(self) -> Dict[str, Any]:
        lambda_client = self.session.client('lambda')
        response = lambda_client.list_functions()
        
        functions = []
        for func in response['Functions']:
            functions.append({
                "name": func['FunctionName'],
                "runtime": func['Runtime'],
                "memory": func['MemorySize'],
                "timeout": func['Timeout'],
                "last_modified": func['LastModified']
            })
        
        return {
            "service": "lambda",
            "operation": "list_functions",
            "result": functions,
            "count": len(functions)
        }
    
    def _invoke_function(self, function_name: str) -> Dict[str, Any]:
        if not function_name:
            return {"error": "Function name required"}
            
        lambda_client = self.session.client('lambda')
        response = lambda_client.invoke(FunctionName=function_name)
        
        return {
            "service": "lambda",
            "operation": "invoke_function",
            "function": function_name,
            "result": "invoked successfully"
        }
    
    def _get_function_logs(self, function_name: str) -> Dict[str, Any]:
        if not function_name:
            return {"error": "Function name required"}
            
        logs_client = self.session.client('logs')
        log_group = f"/aws/lambda/{function_name}"
        
        try:
            response = logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=1
            )
            
            if response['logStreams']:
                stream_name = response['logStreams'][0]['logStreamName']
                events = logs_client.get_log_events(
                    logGroupName=log_group,
                    logStreamName=stream_name,
                    limit=10
                )
                
                logs = [event['message'] for event in events['events']]
                
                return {
                    "service": "lambda",
                    "operation": "get_function_logs",
                    "function": function_name,
                    "result": logs,
                    "count": len(logs)
                }
            else:
                return {
                    "service": "lambda",
                    "operation": "get_function_logs",
                    "function": function_name,
                    "result": "No logs found"
                }
                
        except Exception as e:
            return {"error": f"Could not get logs: {str(e)}"}