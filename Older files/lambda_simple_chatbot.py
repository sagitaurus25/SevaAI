import json
import boto3
from typing import Dict, Any

lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    """Simple Chatbot Router - Enhanced keyword matching"""
    
    if event.get('httpMethod') == 'OPTIONS':
        return create_response(200, {})
    
    try:
        body = json.loads(event.get('body', '{}'))
        user_request = body.get('request', '')
        
        if not user_request:
            return create_response(400, {'error': 'No request provided'})
        
        # Determine service using enhanced matching
        service = determine_service(user_request)
        
        if service == 'unknown':
            return create_response(200, {
                'request': user_request,
                'response': "I can help you with AWS services like S3, EC2, Lambda, IAM, and CloudWatch. What would you like to do?",
                'suggestions': [
                    'List my S3 buckets',
                    'Show EC2 instances', 
                    'Check Lambda functions',
                    'List IAM users'
                ]
            })
        
        # Route to service
        result = route_to_service(service, user_request)
        
        return create_response(200, {
            'request': user_request,
            'service': service,
            'result': result
        })
        
    except Exception as e:
        return create_response(500, {'error': str(e)})

def determine_service(request: str) -> str:
    """Enhanced service detection"""
    request_lower = request.lower()
    
    # CloudWatch/Metrics (highest priority)
    if any(word in request_lower for word in ['ran', 'invocation', 'metrics', 'usage', 'cpu', 'alarm', 'cloudwatch']):
        return 'cloudwatch'
    
    # S3 indicators
    if any(word in request_lower for word in ['bucket', 's3', 'object', 'upload', 'download', 'storage', 'file']):
        return 's3'
    
    # EC2 indicators  
    if any(word in request_lower for word in ['instance', 'ec2', 'server', 'vm', 'security group', 'key pair', 'vpc']):
        return 'ec2'
    
    # Lambda indicators
    if any(word in request_lower for word in ['lambda', 'function']):
        return 'lambda'
    
    # IAM indicators
    if any(word in request_lower for word in ['iam', 'user', 'role', 'policy']):
        return 'iam'
    
    return 'unknown'

def route_to_service(service: str, request: str) -> Dict[str, Any]:
    """Route to service Lambda"""
    
    function_map = {
        's3': 'aws-agent-s3-service',
        'ec2': 'aws-agent-ec2-service', 
        'lambda': 'aws-agent-lambda-service',
        'iam': 'aws-agent-iam-service',
        'cloudwatch': 'aws-agent-cloudwatch-service'
    }
    
    function_name = function_map.get(service)
    if not function_name:
        return {'error': f'Service {service} not supported'}
    
    try:
        payload = {'request': request, 'service': service}
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        return json.loads(response['Payload'].read())
        
    except Exception as e:
        return {'error': f'Failed to invoke {service}: {str(e)}'}

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body, indent=2)
    }