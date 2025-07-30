import boto3
import json
import os
import re
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass

@dataclass
class IntentMatch:
    service: str
    action: str
    resource_type: str
    confidence: float
    parameters: Dict[str, Any]
    description: str

class LLMCommandGenerator:
    def __init__(self):
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        # Define service keywords and their variations
        self.service_keywords = {
            's3': {'s3', 'bucket', 'object', 'file', 'storage'},  # Reduced to core keywords
            'ec2': {'ec2', 'instance', 'server', 'vm', 'compute'},
            'lambda': {'lambda', 'function', 'serverless'},
            'rds': {'rds', 'database', 'db'},
            'iam': {'iam', 'user', 'role', 'policy'},
            'ecs': {'ecs', 'container', 'task', 'cluster'},
            'cloudformation': {'cloudformation', 'cfn', 'stack', 'template'}
        }                  
        
        # Define action keywords
        self.action_keywords = {
            'list': {'list', 'show', 'display', 'get', 'find', 'retrieve', 'view'},
            'describe': {'describe', 'detail', 'details', 'info', 'information', 'status'},
            'create': {'create', 'make', 'build', 'launch', 'start', 'new'},
            'delete': {'delete', 'remove', 'destroy', 'terminate', 'kill'},
            'update': {'update', 'modify', 'change', 'edit', 'alter'},
            'stop': {'stop', 'halt', 'pause'},
            'start': {'start', 'begin', 'run', 'launch'}
        }
        
        
        # Define resource type keywords
        self.resource_keywords = {
            's3': {
                's3', 'bucket', 'buckets', 'storage', 'object', 'objects', 
                'file', 'files', 'content', 'contents', 'data', 'item', 'items'
            },
            'ec2': {
                'instances': {'instance', 'instances', 'server', 'servers', 'vm', 'vms'},
                'volumes': {'volume', 'volumes', 'disk', 'disks'},
                'security_groups': {'security group', 'security groups', 'sg'},
                'key_pairs': {'key pair', 'key pairs', 'keypair', 'keypairs'}
            },
            'lambda': {
                'functions': {'function', 'functions', 'lambda', 'lambdas'}
            },
            'rds': {
                'instances': {'instance', 'instances', 'database', 'databases', 'db'}
            },
            'iam': {
                'users': {'user', 'users'},
                'roles': {'role', 'roles'},
                'policies': {'policy', 'policies'}
            }
        }
        
        # Define filter keywords
        self.filter_keywords = {
            'state': {'running', 'stopped', 'terminated', 'pending', 'stopping'},
            'time': {'created', 'modified', 'updated', 'from', 'since', 'until', 'in', 'during'},
            'size': {'large', 'small', 'micro', 'nano', 'medium'},
            'runtime': {'python', 'nodejs', 'java', 'go', 'ruby', 'dotnet'}
        }
        
        # Command templates
        self.command_templates = {
            ('s3', 'list', 'buckets'): {
                'base': 'aws s3 ls',
                'with_filters': {
                    'time': 'aws s3api list-buckets --query "Buckets[?CreationDate >= `{start_date}` && CreationDate < `{end_date}`].[Name,CreationDate]" --output table'
                },
                'description': 'Lists S3 buckets'
            },
            ('s3', 'list', 'objects'): {
                'base': 'aws s3 ls s3://{bucket}/',
                'with_recursive': 'aws s3 ls s3://{bucket}/ --recursive',
                'description': 'Lists objects in S3 bucket'
            },
            ('ec2', 'list', 'instances'): {
                'base': 'aws ec2 describe-instances --query "Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,Placement.AvailabilityZone]" --output table',
                'with_filters': {
                    'state': 'aws ec2 describe-instances --filters Name=instance-state-name,Values={state} --query "Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,Placement.AvailabilityZone]" --output table'
                },
                'description': 'Lists EC2 instances'
            },
            ('lambda', 'list', 'functions'): {
                'base': 'aws lambda list-functions --query "Functions[*].[FunctionName,Runtime,LastModified]" --output table',
                'with_filters': {
                    'runtime': 'aws lambda list-functions --query "Functions[?starts_with(Runtime, `{runtime}`)].[FunctionName,Runtime,LastModified]" --output table',
                    'time': 'aws lambda list-functions --query "Functions[?LastModified >= `{start_date}` && LastModified < `{end_date}`].[FunctionName,Runtime,LastModified]" --output table'
                },
                'description': 'Lists Lambda functions'
            },
            ('rds', 'list', 'instances'): {
                'base': 'aws rds describe-db-instances --query "DBInstances[*].[DBInstanceIdentifier,DBInstanceStatus,Engine,DBInstanceClass]" --output table',
                'description': 'Lists RDS database instances'
            },
            ('iam', 'list', 'users'): {
                'base': 'aws iam list-users --query "Users[*].[UserName,CreateDate]" --output table',
                'description': 'Lists IAM users'
            }
        }
    
    async def generate_aws_command(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate AWS CLI command using intelligent intent analysis"""
        try:
            print(f"🧠 Analyzing intent for: '{user_query}'")
            
            # Parse the user query algorithmically
            intent = self._analyze_intent(user_query)
            
            if intent.confidence < 0.4:
                print(f"❌ Low confidence ({intent.confidence:.2f}), falling back to suggestions")
                return self._generate_fallback_response(user_query)
            
            print(f"✅ Intent identified: {intent.service}.{intent.action}.{intent.resource_type} (confidence: {intent.confidence:.2f})")
            print(f"📋 Parameters: {intent.parameters}")
            
            # Generate command based on intent
            command_result = self._generate_command_from_intent(intent)
            
            if command_result["success"]:
                command_result["confidence"] = intent.confidence
                command_result["method"] = "algorithmic_intent_analysis"
                
            return command_result
            
        except Exception as e:
            print(f"❌ Error in generate_aws_command: {e}")
            return {
                "success": False,
                "error": f"Failed to generate command: {str(e)}",
                "suggestion": "Try a more specific request"
            }
    
    def _analyze_intent(self, user_query: str) -> IntentMatch:
        """Algorithmically analyze user intent from the query"""
        query_lower = user_query.lower().strip()
        words = set(re.findall(r'\b\w+\b', query_lower))
        
        print(f"🔍 Words found: {words}")
        
        # Extract service
        service_scores = {}
        for service, keywords in self.service_keywords.items():
            score = len(words.intersection(keywords)) / len(keywords)
            if score > 0:
                service_scores[service] = score
                print(f"📊 {service}: {score:.2f} (matched: {words.intersection(keywords)})")
        
        # FIX: Check if service_scores is empty before calling max
        if service_scores:
            best_service = max(service_scores.items(), key=lambda x: x[1])
        else:
            best_service = ('unknown', 0.0)
        
        print(f"🎯 Best service: {best_service[0]} (score: {best_service[1]:.2f})")
        
        # Extract action
        action_scores = {}
        for action, keywords in self.action_keywords.items():
            score = len(words.intersection(keywords))
            if score > 0:
                action_scores[action] = score
        
        # FIX: Check if action_scores is empty before calling max
        if action_scores:
            best_action = max(action_scores.items(), key=lambda x: x[1])
        else:
            best_action = ('list', 0)  # Default to 'list' action
        
        # Extract resource type
        resource_type = 'unknown'
        if best_service[0] in self.resource_keywords:
            resource_scores = {}
            for resource, keywords in self.resource_keywords[best_service[0]].items():
                score = len(words.intersection(keywords))
                if score > 0:
                    resource_scores[resource] = score
            
            if resource_scores:
                resource_type = max(resource_scores.items(), key=lambda x: x[1])[0]
        
        # Extract parameters
        parameters = self._extract_parameters(query_lower, words, best_service[0])
        
        # Calculate confidence
        confidence = self._calculate_confidence(best_service[1], best_action[1], parameters)
        
        return IntentMatch(
            service=best_service[0],
            action=best_action[0],
            resource_type=resource_type,
            confidence=confidence,
            parameters=parameters,
            description=f"{best_action[0]} {best_service[0]} {resource_type}"
        )
    
    def _extract_parameters(self, query: str, words: Set[str], service: str) -> Dict[str, Any]:
        """Extract parameters like bucket names, years, states, etc."""
        parameters = {}
        
        # Extract bucket names (for S3)
        if service == 's3':
            # Look for bucket name patterns
            bucket_patterns = [
                r'\bin\s+([a-zA-Z0-9\-\.]+)',
                r'bucket\s+([a-zA-Z0-9\-\.]+)',
                r'([a-zA-Z0-9\-\.]+)\s+bucket',
                r"'([a-zA-Z0-9\-\.]+)'",
                r'"([a-zA-Z0-9\-\.]+)"'
            ]
            for pattern in bucket_patterns:
                match = re.search(pattern, query)
                if match:
                    parameters['bucket'] = match.group(1)
                    break
        
        # Extract years
        year_match = re.search(r'\b(20\d{2})\b', query)
        if year_match:
            parameters['year'] = year_match.group(1)
            parameters['start_date'] = f"{parameters['year']}-01-01"
            parameters['end_date'] = f"{int(parameters['year']) + 1}-01-01"
        
        # Extract states
        for state in self.filter_keywords['state']:
            if state in words:
                parameters['state'] = state
                break
        
        # Extract runtime
        for runtime in self.filter_keywords['runtime']:
            if runtime in words:
                parameters['runtime'] = runtime
                break
        
        # Detect recursive intent
        if any(word in words for word in {'all', 'recursive', 'everything', 'recursively'}):
            parameters['recursive'] = True
        
        return parameters
    
    def _calculate_confidence(self, service_score: float, action_score: float, parameters: Dict[str, Any]) -> float:
        """Calculate confidence based on matches"""
        base_confidence = (service_score + (action_score * 0.1)) * 0.7
        
        # Boost confidence if we found specific parameters
        if parameters.get('bucket'):
            base_confidence += 0.2
        if parameters.get('year'):
            base_confidence += 0.1
        if parameters.get('state'):
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _generate_command_from_intent(self, intent: IntentMatch) -> Dict[str, Any]:
        """Generate AWS CLI command from structured intent"""
        command_key = (intent.service, intent.action, intent.resource_type)
        
        if command_key not in self.command_templates:
            return {
                "success": False,
                "error": f"No command template for {intent.service} {intent.action} {intent.resource_type}",
                "suggestion": f"Try a different request for {intent.service}"
            }
        
        template = self.command_templates[command_key]
        
        # Choose appropriate command variant
        if intent.parameters.get('recursive') and 'with_recursive' in template:
            command = template['with_recursive'].format(**intent.parameters)
        elif 'with_filters' in template and self._has_applicable_filters(intent.parameters, template['with_filters']):
            # Find the best matching filter
            for filter_type, filter_template in template['with_filters'].items():
                if filter_type in intent.parameters or any(key.startswith(filter_type) for key in intent.parameters):
                    command = filter_template.format(**intent.parameters)
                    break
            else:
                command = template['base'].format(**intent.parameters)
        else:
            command = template['base'].format(**intent.parameters)
        
        # Add region if needed
        command = self._ensure_region(command)
        
        # Generate description
        description = template['description']
        if intent.parameters.get('bucket'):
            description += f" in bucket '{intent.parameters['bucket']}'"
        if intent.parameters.get('year'):
            description += f" from {intent.parameters['year']}"
        if intent.parameters.get('state'):
            description += f" in {intent.parameters['state']} state"
        
        return {
            "success": True,
            "command": command,
            "description": description,
            "service": intent.service,
            "intent": {
                "service": intent.service,
                "action": intent.action,
                "resource": intent.resource_type,
                "parameters": intent.parameters
            }
        }
    
    def _has_applicable_filters(self, parameters: Dict[str, Any], filters: Dict[str, str]) -> bool:
        """Check if we have parameters that match available filters"""
        for filter_type in filters.keys():
            if filter_type in parameters or any(key.startswith(filter_type) for key in parameters):
                return True
        return False
    
    def _ensure_region(self, command: str) -> str:
        """Add region parameter if needed"""
        if '--region' not in command:
            regional_services = ['ec2', 'rds', 'lambda', 'ecs']
            parts = command.split()
            if len(parts) >= 2 and parts[1] in regional_services:
                insert_pos = 3 if len(parts) >= 3 else len(parts)
                parts.insert(insert_pos, '--region')
                parts.insert(insert_pos + 1, os.getenv('AWS_REGION', 'us-east-1'))
                command = ' '.join(parts)
        return command
    
    def _generate_fallback_response(self, user_query: str) -> Dict[str, Any]:
        """Generate helpful fallback when intent analysis fails"""
        query_lower = user_query.lower()
        
        suggestions = []
        if any(word in query_lower for word in ['bucket', 's3']):
            suggestions = [
                "list my S3 buckets",
                "list objects in my-bucket-name",
                "show S3 buckets created in 2024"
            ]
        elif any(word in query_lower for word in ['instance', 'ec2', 'server']):
            suggestions = [
                "list my EC2 instances",
                "show running EC2 instances",
                "list stopped instances"
            ]
        elif any(word in query_lower for word in ['function', 'lambda']):
            suggestions = [
                "list my Lambda functions",
                "show Python Lambda functions",
                "list functions created in 2024"
            ]
        else:
            suggestions = [
                "list my S3 buckets",
                "show my EC2 instances",
                "list my Lambda functions"
            ]
        
        return {
            "success": False,
            "error": f"I couldn't understand '{user_query}' with enough confidence",
            "suggestion": f"Try one of these: {', '.join(suggestions)}"
        }