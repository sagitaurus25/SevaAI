"""
CloudWatch Service Agent
"""
from .base_agent import BaseAgent
from typing import Dict, List, Any
from datetime import datetime, timedelta

class CloudWatchAgent(BaseAgent):
    def get_service_name(self) -> str:
        return "cloudwatch"
    
    def get_capabilities(self) -> List[str]:
        return [
            "list_alarms",
            "get_metrics",
            "describe_alarms",
            "get_logs"
        ]
    
    def can_handle(self, command: str) -> bool:
        cw_keywords = ["cloudwatch", "alarm", "metric", "monitor", "log"]
        return any(keyword in command.lower() for keyword in cw_keywords)
    
    def execute(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        command_lower = command.lower()
        
        try:
            if "list" in command_lower and "alarm" in command_lower:
                return self._list_alarms()
            elif "metric" in command_lower:
                return self._get_metrics()
            elif "log" in command_lower:
                return self._get_log_groups()
            else:
                return {"error": f"CloudWatch command not recognized: {command}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _list_alarms(self) -> Dict[str, Any]:
        cloudwatch = self.session.client('cloudwatch')
        response = cloudwatch.describe_alarms()
        
        alarms = []
        for alarm in response['MetricAlarms']:
            alarms.append({
                "name": alarm['AlarmName'],
                "state": alarm['StateValue'],
                "reason": alarm['StateReason'],
                "metric": alarm['MetricName'],
                "namespace": alarm['Namespace']
            })
        
        return {
            "service": "cloudwatch",
            "operation": "list_alarms",
            "result": alarms,
            "count": len(alarms)
        }
    
    def _get_metrics(self) -> Dict[str, Any]:
        cloudwatch = self.session.client('cloudwatch')
        
        # Get some common metrics
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        try:
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            datapoints = []
            for dp in response['Datapoints']:
                datapoints.append({
                    "timestamp": dp['Timestamp'].isoformat(),
                    "value": dp['Average']
                })
            
            return {
                "service": "cloudwatch",
                "operation": "get_metrics",
                "metric": "EC2 CPU Utilization",
                "result": datapoints,
                "count": len(datapoints)
            }
            
        except Exception as e:
            return {
                "service": "cloudwatch", 
                "operation": "get_metrics",
                "result": "No EC2 metrics available"
            }
    
    def _get_log_groups(self) -> Dict[str, Any]:
        logs = self.session.client('logs')
        response = logs.describe_log_groups(limit=10)
        
        log_groups = []
        for group in response['logGroups']:
            log_groups.append({
                "name": group['logGroupName'],
                "created": group['creationTime'],
                "retention": group.get('retentionInDays', 'Never expire')
            })
        
        return {
            "service": "cloudwatch",
            "operation": "get_log_groups",
            "result": log_groups,
            "count": len(log_groups)
        }