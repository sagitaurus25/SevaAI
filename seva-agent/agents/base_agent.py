"""
Base Agent class for all AWS service agents
"""
import boto3
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class BaseAgent(ABC):
    def __init__(self, session: boto3.Session):
        self.session = session
        self.service_name = self.get_service_name()
        
    @abstractmethod
    def get_service_name(self) -> str:
        """Return the AWS service name this agent handles"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of operations this agent can perform"""
        pass
    
    @abstractmethod
    def can_handle(self, command: str) -> bool:
        """Check if this agent can handle the given command"""
        pass
    
    @abstractmethod
    def execute(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the command and return results"""
        pass
    
    def get_dependencies(self, command: str) -> List[str]:
        """Return list of services this command depends on"""
        return []