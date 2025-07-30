import os
import re
from typing import Dict, Any

class LLMCommandGenerator:
    def __init__(self):
        print("✅ Simple working command generator initialized")
    
    async def generate_aws_command(self, user_query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Simple but effective command generation"""
        try:
            query = user_query.lower().strip()
            print(f"🔍 Processing: '{query}'")
            
            # S3 Object Operations - HIGHEST PRIORITY
            bucket_match = self._extract_bucket_name(query)
            if bucket_match and any(word in query for word in ['object', 'objects', 'file', 'files', 'content']):
                bucket = bucket_match
                if any(word in query for word in ['all', 'recursive', 'everything']):
                    return {
                        "success": True,
                        "command": f"aws s3 ls s3://{bucket}/ --recursive",
                        "description": f"Lists all objects recursively in S3 bucket '{bucket}'"
                    }
                else:
                    return {
                        "success": True,
                        "command": f"aws s3 ls s3://{bucket}/",
                        "description": f"Lists objects in S3 bucket '{bucket}'"
                    }
            
            # S3 Bucket Operations
            elif any(word in query for word in ['bucket', 'buckets', 's3']):
                # Year filtering
                year_match = re.search(r'\b(20\d{2})\b', query)
                if year_match:
                    year = year_match.group(1)
                    next_year = str(int(year) + 1)
                    return {
                        "success": True,
                        "command": f"aws s3api list-buckets --query 'Buckets[?CreationDate >= `{year}-01-01` && CreationDate < `{next_year}-01-01`].[Name,CreationDate]' --output table",
                        "description": f"Lists S3 buckets created in {year}"
                    }
                else:
                    return {
                        "success": True,
                        "command": "aws s3 ls",
                        "description": "Lists all S3 buckets in your account"
                    }
            
            # EC2 Operations
            elif any(word in query for word in ['instance', 'instances', 'ec2', 'server', 'servers', 'vm']):
                base_cmd = "aws ec2 describe-instances --region us-east-1"
                
                if any(word in query for word in ['running', 'active']):
                    return {
                        "success": True,
                        "command": f"{base_cmd} --filters Name=instance-state-name,Values=running --query 'Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,Placement.AvailabilityZone]' --output table",
                        "description": "Lists running EC2 instances"
                    }
                elif any(word in query for word in ['stopped', 'inactive']):
                    return {
                        "success": True,
                        "command": f"{base_cmd} --filters Name=instance-state-name,Values=stopped --query 'Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,Placement.AvailabilityZone]' --output table",
                        "description": "Lists stopped EC2 instances"
                    }
                else:
                    return {
                        "success": True,
                        "command": f"{base_cmd} --query 'Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,Placement.AvailabilityZone]' --output table",
                        "description": "Lists all EC2 instances"
                    }
            
            # Lambda Operations
            elif any(word in query for word in ['function', 'functions', 'lambda']):
                base_cmd = "aws lambda list-functions --region us-east-1"
                
                # Runtime filtering
                if any(word in query for word in ['python']):
                    return {
                        "success": True,
                        "command": f"{base_cmd} --query 'Functions[?starts_with(Runtime, `python`)].[FunctionName,Runtime,LastModified]' --output table",
                        "description": "Lists Python Lambda functions"
                    }
                # Year filtering
                elif re.search(r'\b(20\d{2})\b', query):
                    year = re.search(r'\b(20\d{2})\b', query).group(1)
                    next_year = str(int(year) + 1)
                    return {
                        "success": True,
                        "command": f"{base_cmd} --query 'Functions[?LastModified >= `{year}-01-01` && LastModified < `{next_year}-01-01`].[FunctionName,Runtime,LastModified]' --output table",
                        "description": f"Lists Lambda functions last modified in {year}"
                    }
                else:
                    return {
                        "success": True,
                        "command": f"{base_cmd} --query 'Functions[*].[FunctionName,Runtime,LastModified]' --output table",
                        "description": "Lists all Lambda functions"
                    }
            
            # RDS Operations
            elif any(word in query for word in ['database', 'databases', 'rds', 'db']):
                return {
                    "success": True,
                    "command": "aws rds describe-db-instances --region us-east-1 --query 'DBInstances[*].[DBInstanceIdentifier,DBInstanceStatus,Engine,DBInstanceClass]' --output table",
                    "description": "Lists RDS database instances"
                }
            
            # IAM Operations
            elif any(word in query for word in ['user', 'users', 'iam']):
                return {
                    "success": True,
                    "command": "aws iam list-users --query 'Users[*].[UserName,CreateDate]' --output table",
                    "description": "Lists IAM users"
                }
            
            # CloudFormation Operations
            elif any(word in query for word in ['stack', 'stacks', 'cloudformation', 'cfn']):
                return {
                    "success": True,
                    "command": "aws cloudformation list-stacks --region us-east-1 --query 'StackSummaries[?StackStatus != `DELETE_COMPLETE`].[StackName,StackStatus,CreationTime]' --output table",
                    "description": "Lists CloudFormation stacks"
                }
            
            # Default fallback
            else:
                return {
                    "success": False,
                    "error": f"I don't understand '{user_query}'",
                    "suggestion": "Try: 'list my S3 buckets', 'show EC2 instances', 'list objects in bucket-name', or 'list Lambda functions'"
                }
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return {
                "success": False,
                "error": f"Error processing query: {str(e)}",
                "suggestion": "Try a simpler request"
            }
    
    def _extract_bucket_name(self, query: str) -> str:
        """Extract bucket name from query using multiple patterns"""
        patterns = [
            r'\bin\s+([a-zA-Z0-9\-\.]+)',           # "in bucket-name"
            r'([a-zA-Z0-9\-\.]+)\s+bucket',         # "bucket-name bucket"
            r'bucket\s+([a-zA-Z0-9\-\.]+)',         # "bucket bucket-name"
            r"'([a-zA-Z0-9\-\.]+)'",                # 'bucket-name'
            r'"([a-zA-Z0-9\-\.]+)"',                # "bucket-name"
            r'objects.*?([a-zA-Z0-9\-\.]{3,})',     # "objects something bucket-name"
            r'files.*?([a-zA-Z0-9\-\.]{3,})',       # "files something bucket-name"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                candidate = match.group(1)
                # Validate it looks like a bucket name (has numbers/letters, maybe dashes)
                if re.match(r'^[a-zA-Z0-9\-\.]+$', candidate) and len(candidate) >= 3:
                    # Skip common words that aren't bucket names
                    skip_words = {'the', 'and', 'for', 'all', 'my', 'your', 'his', 'her', 'its', 'our', 'their'}
                    if candidate.lower() not in skip_words:
                        print(f"🪣 Extracted bucket name: '{candidate}'")
                        return candidate
        
        return None