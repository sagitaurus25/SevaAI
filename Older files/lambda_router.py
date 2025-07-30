import json
import boto3
from typing import Dict, Any

lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    """Router Lambda - Routes requests to appropriate service Lambda"""
    
    # Handle CORS preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
            },
            'body': ''
        }
    
    try:
        # Parse the incoming request
        body = json.loads(event.get('body', '{}'))
        user_request = body.get('request', '')
        
        if not user_request:
            return create_response(400, {'error': 'No request provided'})
        
        # Determine which service to route to
        service = determine_service(user_request)
        
        if service == 'unknown':
            return create_response(200, {
                'request': user_request,
                'error': 'Could not determine AWS service from request',
                'supported_services': ['S3', 'EC2', 'Lambda'],
                'examples': {
                    'S3': ['List all my S3 buckets', 'Show objects in my-bucket'],
                    'EC2': ['List all EC2 instances', 'Start instance i-1234567890abcdef0'],
                    'Lambda': ['Show my Lambda functions', 'List all Lambda functions']
                }
            })
        
        # Route to appropriate service Lambda
        result = route_to_service(service, user_request)
        
        return create_response(200, {
            'request': user_request,
            'service': service,
            'result': result
        })
        
    except Exception as e:
        return create_response(500, {'error': str(e)})

def determine_service(request: str) -> str:
    """Determine which AWS service the request is for"""
    request_lower = request.lower()
    
    # Strong S3 indicators (high priority)
    if any(word in request_lower for word in ['bucket', 's3', 'object', 'upload', 'download']):
        return 's3'
    
    # Strong EC2 indicators (high priority)
    if any(word in request_lower for word in ['instance', 'ec2', 'server', 'vm']):
        return 'ec2'
    
    # Lambda indicators
    if any(word in request_lower for word in ['lambda', 'function']):
        return 'lambda'
    
    # Instance ID pattern
    if 'i-' in request_lower and len([w for w in request_lower.split() if w.startswith('i-')]) > 0:
        return 'ec2'
    
    # EC2-specific terms
    if any(word in request_lower for word in ['security group', 'key pair', 'start', 'stop', 'reboot']):
        return 'ec2'
    
    # S3-specific terms
    if any(word in request_lower for word in ['file', 'storage', 'create bucket', 'delete bucket']):
        return 's3'
    
    return 'unknown'

def route_to_service(service: str, request: str) -> Dict[str, Any]:
    """Route request to the appropriate service Lambda"""
    
    # Map service to Lambda function name
    function_map = {
        's3': 'aws-agent-s3-service',
        'ec2': 'aws-agent-ec2-service',
        'lambda': 'aws-agent-lambda-service'
    }
    
    function_name = function_map.get(service)
    if not function_name:
        return {'error': f'No Lambda function configured for service: {service}'}
    
    try:
        # Prepare payload for service Lambda
        payload = {
            'request': request,
            'service': service
        }
        
        # Invoke the service Lambda
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        # Check if the service Lambda returned an error
        if response.get('FunctionError'):
            return {
                'error': f'Service Lambda error: {response_payload}',
                'service': service,
                'function': function_name
            }
        
        return response_payload
        
    except Exception as e:
        return {
            'error': f'Failed to invoke {service} service: {str(e)}',
            'service': service,
            'function': function_name
        }

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create properly formatted API Gateway response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
        },
        'body': json.dumps(body, indent=2)
    }