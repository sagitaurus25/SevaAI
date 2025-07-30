import json
import boto3
from typing import Dict, Any

iam_client = boto3.client('iam')

def lambda_handler(event, context):
    """IAM Service Lambda - Handles all IAM operations"""
    try:
        request = event.get('request', '').lower()
        operation = event.get('operation', '')
        parameters = event.get('parameters', {})
        
        if ('user' in request and ('list' in request or 'show' in request)) or ('iam' in request and 'user' in request):
            return list_users()
        elif 'permission' in request or 'policy' in request or 'role' in request:
            return handle_permissions_query(request)
        else:
            return {
                'error': 'IAM operation not recognized',
                'supported_operations': [
                    'List IAM users',
                    'Show IAM users',
                    'IAM permissions',
                    'IAM policies',
                    'IAM roles'
                ]
            }
            
    except Exception as e:
        return {'error': f'IAM service error: {str(e)}'}

def handle_permissions_query(request):
    """Handle IAM permissions/policies/roles queries"""
    try:
        if 'permission' in request:
            # Count policies as a proxy for permissions
            response = iam_client.list_policies(Scope='Local')
            policies = response['Policies']
            return {
                'message': f'Found {len(policies)} custom IAM policies',
                'count': len(policies),
                'policies': [p['PolicyName'] for p in policies[:10]]
            }
        elif 'role' in request:
            response = iam_client.list_roles()
            roles = [role['RoleName'] for role in response['Roles']]
            return {
                'roles': roles,
                'count': len(roles)
            }
        elif 'policy' in request:
            response = iam_client.list_policies(Scope='All')
            policies = [policy['PolicyName'] for policy in response['Policies'][:20]]
            return {
                'policies': policies,
                'count': len(policies)
            }
    except Exception as e:
        return {'error': f'Failed to get IAM info: {str(e)}'}

def list_users():
    """List all IAM users"""
    try:
        response = iam_client.list_users()
        user_names = [user['UserName'] for user in response['Users']]
        
        return {
            'users': user_names,
            'count': len(user_names)
        }
    except Exception as e:
        return {'error': f'Failed to list IAM users: {str(e)}'}