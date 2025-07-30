import json
import boto3
from typing import Dict, Any

lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    """Lambda Service Lambda - Handles all Lambda operations"""
    try:
        request = event.get('request', '').lower()
        operation = event.get('operation', '')
        parameters = event.get('parameters', {})
        
        if 'list' in request or 'show' in request or 'lambda' in request or 'function' in request:
            return list_functions()
        elif 'ran' in request or 'invocation' in request or 'execution' in request:
            return get_function_metrics()
        else:
            return {
                'error': 'Lambda operation not recognized',
                'supported_operations': [
                    'List all Lambda functions',
                    'Show my Lambda functions',
                    'Lambda functions',
                    'Show functions'
                ]
            }
            
    except Exception as e:
        return {'error': f'Lambda service error: {str(e)}'}

def list_functions():
    """List all Lambda functions"""
    try:
        response = lambda_client.list_functions()
        function_names = [func['FunctionName'] for func in response['Functions']]
        
        return {
            'functions': function_names,
            'count': len(function_names)
        }
    except Exception as e:
        return {'error': f'Failed to list Lambda functions: {str(e)}'}