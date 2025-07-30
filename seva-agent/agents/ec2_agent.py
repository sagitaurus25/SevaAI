"""
EC2 Service Agent
"""
from .base_agent import BaseAgent
from typing import Dict, List, Any

class EC2Agent(BaseAgent):
    def get_service_name(self) -> str:
        return "ec2"
    
    def get_capabilities(self) -> List[str]:
        return [
            "list_instances",
            "start_instance",
            "stop_instance",
            "describe_instance",
            "list_security_groups"
        ]
    
    def can_handle(self, command: str) -> bool:
        ec2_keywords = ["ec2", "instance", "server", "vm", "security group"]
        return any(keyword in command.lower() for keyword in ec2_keywords)
    
    def execute(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        command_lower = command.lower()
        
        try:
            if "list" in command_lower and "instance" in command_lower:
                return self._list_instances()
            elif "start" in command_lower and "instance" in command_lower:
                instance_id = self._extract_instance_id(command)
                return self._start_instance(instance_id)
            elif "stop" in command_lower and "instance" in command_lower:
                instance_id = self._extract_instance_id(command)
                return self._stop_instance(instance_id)
            elif "security" in command_lower and "group" in command_lower:
                return self._list_security_groups()
            else:
                return {"error": f"EC2 command not recognized: {command}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_instance_id(self, command: str) -> str:
        words = command.split()
        for word in words:
            if word.startswith("i-"):
                return word
        return None
    
    def _list_instances(self) -> Dict[str, Any]:
        ec2 = self.session.client('ec2')
        response = ec2.describe_instances()
        
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                name = "Unnamed"
                if 'Tags' in instance:
                    for tag in instance['Tags']:
                        if tag['Key'] == 'Name':
                            name = tag['Value']
                
                instances.append({
                    "id": instance['InstanceId'],
                    "name": name,
                    "type": instance['InstanceType'],
                    "state": instance['State']['Name'],
                    "public_ip": instance.get('PublicIpAddress'),
                    "private_ip": instance.get('PrivateIpAddress')
                })
        
        return {
            "service": "ec2",
            "operation": "list_instances",
            "result": instances,
            "count": len(instances)
        }
    
    def _start_instance(self, instance_id: str) -> Dict[str, Any]:
        ec2 = self.session.client('ec2')
        response = ec2.start_instances(InstanceIds=[instance_id])
        
        return {
            "service": "ec2",
            "operation": "start_instance",
            "instance_id": instance_id,
            "result": "started"
        }
    
    def _stop_instance(self, instance_id: str) -> Dict[str, Any]:
        ec2 = self.session.client('ec2')
        response = ec2.stop_instances(InstanceIds=[instance_id])
        
        return {
            "service": "ec2",
            "operation": "stop_instance",
            "instance_id": instance_id,
            "result": "stopped"
        }
    
    def _list_security_groups(self) -> Dict[str, Any]:
        ec2 = self.session.client('ec2')
        response = ec2.describe_security_groups()
        
        groups = []
        for group in response['SecurityGroups']:
            groups.append({
                "id": group['GroupId'],
                "name": group['GroupName'],
                "description": group['Description'],
                "vpc_id": group.get('VpcId')
            })
        
        return {
            "service": "ec2",
            "operation": "list_security_groups",
            "result": groups,
            "count": len(groups)
        }