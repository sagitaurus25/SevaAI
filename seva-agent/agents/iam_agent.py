"""
IAM Service Agent
"""
from .base_agent import BaseAgent
from typing import Dict, List, Any
import json

class IAMAgent(BaseAgent):
    def get_service_name(self) -> str:
        return "iam"
    
    def get_capabilities(self) -> List[str]:
        return [
            "list_users",
            "list_roles", 
            "list_policies",
            "get_user_policies",
            "get_role_policies",
            "attach_policy",
            "create_policy",
            "grant_s3_permissions"
        ]
    
    def can_handle(self, command: str) -> bool:
        iam_keywords = ["iam", "user", "role", "policy", "permission", "access", "grant", "attach", "create"]
        return any(keyword in command.lower() for keyword in iam_keywords)
    
    def execute(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        command_lower = command.lower()
        
        try:
            if "list" in command_lower and "user" in command_lower:
                return self._list_users()
            elif "list" in command_lower and "role" in command_lower:
                return self._list_roles()
            elif "list" in command_lower and ("policy" in command_lower or "policies" in command_lower):
                return self._list_policies()
            elif "list" in command_lower and "iam" in command_lower:
                # Handle "list my iam" - default to users
                return self._list_users()
            elif "my" in command_lower and "iam" in command_lower:
                # Handle "list my iam" or "show my iam"
                return self._list_users()
            elif "grant" in command_lower and "s3" in command_lower:
                return self._grant_s3_permissions()
            elif "create" in command_lower and "policy" in command_lower:
                return self._create_s3_policy()
            elif "attach" in command_lower and "policy" in command_lower:
                return self._attach_policy_to_user()
            else:
                return {"error": f"IAM command not recognized: {command}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _list_users(self) -> Dict[str, Any]:
        iam = self.session.client('iam')
        response = iam.list_users()
        
        users = []
        for user in response['Users']:
            users.append({
                "name": user['UserName'],
                "id": user['UserId'],
                "arn": user['Arn'],
                "created": user['CreateDate'].isoformat()
            })
        
        return {
            "service": "iam",
            "operation": "list_users",
            "result": users,
            "count": len(users)
        }
    
    def _list_roles(self) -> Dict[str, Any]:
        iam = self.session.client('iam')
        response = iam.list_roles()
        
        roles = []
        for role in response['Roles']:
            roles.append({
                "name": role['RoleName'],
                "arn": role['Arn'],
                "created": role['CreateDate'].isoformat(),
                "description": role.get('Description', 'N/A')
            })
        
        return {
            "service": "iam",
            "operation": "list_roles",
            "result": roles,
            "count": len(roles)
        }
    
    def _list_policies(self) -> Dict[str, Any]:
        iam = self.session.client('iam')
        response = iam.list_policies(Scope='Local')  # Only customer managed policies
        
        policies = []
        for policy in response['Policies']:
            policies.append({
                "name": policy['PolicyName'],
                "arn": policy['Arn'],
                "created": policy['CreateDate'].isoformat(),
                "description": policy.get('Description', 'N/A')
            })
        
        return {
            "service": "iam",
            "operation": "list_policies",
            "result": policies,
            "count": len(policies)
        }
    
    def _grant_s3_permissions(self) -> Dict[str, Any]:
        try:
            # Get current user
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            user_arn = identity['Arn']
            
            if ':user/' in user_arn:
                username = user_arn.split(':user/')[1]
            elif ':root' in user_arn:
                # Root user - already has full permissions
                return {
                    "service": "iam",
                    "operation": "grant_s3_permissions",
                    "result": "Root user already has full S3 permissions - no action needed"
                }
            else:
                return {"error": f"Cannot determine user type from ARN: {user_arn}"}
            
            # Create S3 full access policy
            policy_doc = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:*"
                        ],
                        "Resource": "*"
                    }
                ]
            }
            
            iam = self.session.client('iam')
            
            # Create policy
            policy_name = f"S3FullAccess-{username}"
            try:
                policy_response = iam.create_policy(
                    PolicyName=policy_name,
                    PolicyDocument=json.dumps(policy_doc),
                    Description="Full S3 access for analytics"
                )
                policy_arn = policy_response['Policy']['Arn']
            except Exception as e:
                if "already exists" in str(e):
                    # Policy exists, get its ARN
                    account_id = identity['Account']
                    policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
                else:
                    return {"error": f"Failed to create policy: {str(e)}"}
            
            # Attach policy to user
            try:
                iam.attach_user_policy(
                    UserName=username,
                    PolicyArn=policy_arn
                )
            except Exception as e:
                if "already attached" not in str(e):
                    return {"error": f"Failed to attach policy: {str(e)}"}
            
            return {
                "service": "iam",
                "operation": "grant_s3_permissions",
                "result": f"S3 permissions granted to user {username}",
                "policy_arn": policy_arn
            }
            
        except Exception as e:
            return {"error": f"Failed to grant S3 permissions: {str(e)}"}
    
    def _create_s3_policy(self) -> Dict[str, Any]:
        try:
            policy_doc = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:ListBucket",
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject",
                            "s3:GetBucketLocation"
                        ],
                        "Resource": "*"
                    }
                ]
            }
            
            iam = self.session.client('iam')
            policy_name = "S3AnalyticsPolicy"
            
            response = iam.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_doc),
                Description="S3 permissions for analytics operations"
            )
            
            return {
                "service": "iam",
                "operation": "create_policy",
                "result": f"Policy {policy_name} created",
                "policy_arn": response['Policy']['Arn']
            }
            
        except Exception as e:
            return {"error": f"Failed to create policy: {str(e)}"}
    
    def _attach_policy_to_user(self) -> Dict[str, Any]:
        try:
            # Get current user
            sts = self.session.client('sts')
            identity = sts.get_caller_identity()
            user_arn = identity['Arn']
            
            if ':user/' in user_arn:
                username = user_arn.split(':user/')[1]
            elif ':root' in user_arn:
                return {
                    "service": "iam",
                    "operation": "attach_policy",
                    "result": "Root user already has all permissions"
                }
            else:
                return {"error": "Cannot determine username"}
            
            # Attach S3 full access policy
            iam = self.session.client('iam')
            policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
            
            iam.attach_user_policy(
                UserName=username,
                PolicyArn=policy_arn
            )
            
            return {
                "service": "iam",
                "operation": "attach_policy",
                "result": f"AmazonS3FullAccess attached to {username}"
            }
            
        except Exception as e:
            return {"error": f"Failed to attach policy: {str(e)}"}