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