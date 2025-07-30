"""
VPC Service Agent
"""
from .base_agent import BaseAgent
from typing import Dict, List, Any

class VPCAgent(BaseAgent):
    def get_service_name(self) -> str:
        return "vpc"
    
    def get_capabilities(self) -> List[str]:
        return [
            "list_vpcs",
            "list_subnets",
            "list_route_tables",
            "list_internet_gateways",
            "describe_vpc"
        ]
    
    def can_handle(self, command: str) -> bool:
        vpc_keywords = ["vpc", "subnet", "network", "route", "gateway"]
        return any(keyword in command.lower() for keyword in vpc_keywords)
    
    def execute(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        command_lower = command.lower()
        
        try:
            if "list" in command_lower and "vpc" in command_lower:
                return self._list_vpcs()
            elif "list" in command_lower and "subnet" in command_lower:
                return self._list_subnets()
            elif "route" in command_lower:
                return self._list_route_tables()
            elif "gateway" in command_lower:
                return self._list_internet_gateways()
            else:
                return {"error": f"VPC command not recognized: {command}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _list_vpcs(self) -> Dict[str, Any]:
        ec2 = self.session.client('ec2')
        response = ec2.describe_vpcs()
        
        vpcs = []
        for vpc in response['Vpcs']:
            name = "Unnamed"
            if 'Tags' in vpc:
                for tag in vpc['Tags']:
                    if tag['Key'] == 'Name':
                        name = tag['Value']
            
            vpcs.append({
                "id": vpc['VpcId'],
                "name": name,
                "cidr": vpc['CidrBlock'],
                "state": vpc['State'],
                "is_default": vpc['IsDefault']
            })
        
        return {
            "service": "vpc",
            "operation": "list_vpcs",
            "result": vpcs,
            "count": len(vpcs)
        }
    
    def _list_subnets(self) -> Dict[str, Any]:
        ec2 = self.session.client('ec2')
        response = ec2.describe_subnets()
        
        subnets = []
        for subnet in response['Subnets']:
            name = "Unnamed"
            if 'Tags' in subnet:
                for tag in subnet['Tags']:
                    if tag['Key'] == 'Name':
                        name = tag['Value']
            
            subnets.append({
                "id": subnet['SubnetId'],
                "name": name,
                "vpc_id": subnet['VpcId'],
                "cidr": subnet['CidrBlock'],
                "az": subnet['AvailabilityZone'],
                "available_ips": subnet['AvailableIpAddressCount']
            })
        
        return {
            "service": "vpc",
            "operation": "list_subnets",
            "result": subnets,
            "count": len(subnets)
        }
    
    def _list_route_tables(self) -> Dict[str, Any]:
        ec2 = self.session.client('ec2')
        response = ec2.describe_route_tables()
        
        route_tables = []
        for rt in response['RouteTables']:
            name = "Unnamed"
            if 'Tags' in rt:
                for tag in rt['Tags']:
                    if tag['Key'] == 'Name':
                        name = tag['Value']
            
            route_tables.append({
                "id": rt['RouteTableId'],
                "name": name,
                "vpc_id": rt['VpcId'],
                "routes_count": len(rt['Routes'])
            })
        
        return {
            "service": "vpc",
            "operation": "list_route_tables",
            "result": route_tables,
            "count": len(route_tables)
        }
    
    def _list_internet_gateways(self) -> Dict[str, Any]:
        ec2 = self.session.client('ec2')
        response = ec2.describe_internet_gateways()
        
        gateways = []
        for igw in response['InternetGateways']:
            name = "Unnamed"
            if 'Tags' in igw:
                for tag in igw['Tags']:
                    if tag['Key'] == 'Name':
                        name = tag['Value']
            
            attachments = [att['VpcId'] for att in igw.get('Attachments', [])]
            
            gateways.append({
                "id": igw['InternetGatewayId'],
                "name": name,
                "attached_vpcs": attachments
            })
        
        return {
            "service": "vpc",
            "operation": "list_internet_gateways",
            "result": gateways,
            "count": len(gateways)
        }