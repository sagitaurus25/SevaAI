import json
import boto3
from typing import Dict, Any

lambda_client = boto3.client('lambda')
bedrock_client = boto3.client('bedrock-runtime')

def lambda_handler(event, context):
    """Universal AWS Router - Service-specific help priority"""
    
    if event.get('httpMethod') == 'OPTIONS':
        return create_response(200, {})
    
    try:
        body = json.loads(event.get('body', '{}'))
        user_request = body.get('request', '')
        
        if not user_request:
            return create_response(400, {'error': 'No request provided'})
        
        request_lower = user_request.lower()
        
        # Check for service-specific help first (higher priority)
        if 'help' in request_lower:
            if 'iam' in request_lower:
                result = handle_service_help('iam')
                return create_response(200, {
                    'request': user_request,
                    'service': 'help-iam',
                    'result': result
                })
            elif 's3' in request_lower:
                result = handle_service_help('s3')
                return create_response(200, {
                    'request': user_request,
                    'service': 'help-s3',
                    'result': result
                })
            elif 'ec2' in request_lower:
                result = handle_service_help('ec2')
                return create_response(200, {
                    'request': user_request,
                    'service': 'help-ec2',
                    'result': result
                })
            elif 'lambda' in request_lower:
                result = handle_service_help('lambda')
                return create_response(200, {
                    'request': user_request,
                    'service': 'help-lambda',
                    'result': result
                })
            elif 'cloudwatch' in request_lower:
                result = handle_service_help('cloudwatch')
                return create_response(200, {
                    'request': user_request,
                    'service': 'help-cloudwatch',
                    'result': result
                })
            else:
                # General help
                result = handle_general_help()
                return create_response(200, {
                    'request': user_request,
                    'service': 'help',
                    'result': result
                })
        
        # Keyword backup for S3 requests
        s3_keywords = ['bucket', 's3', 'upload', 'objects', 'move']
        if any(keyword in request_lower for keyword in s3_keywords):
            result = route_to_service('s3', user_request, body)
            return create_response(200, {
                'request': user_request,
                'service': 's3',
                'result': result,
                'method': 'keyword_backup'
            })
        
        # Keyword backup for EC2 requests
        ec2_keywords = ['instance', 'ec2', 'start', 'stop', 'reboot']
        if any(keyword in request_lower for keyword in ec2_keywords):
            result = route_to_service('ec2', user_request, body)
            return create_response(200, {
                'request': user_request,
                'service': 'ec2',
                'result': result,
                'method': 'keyword_backup'
            })
        
        # Keyword backup for Lambda requests
        lambda_keywords = ['lambda', 'function']
        if any(keyword in request_lower for keyword in lambda_keywords):
            result = route_to_service('lambda', user_request, body)
            return create_response(200, {
                'request': user_request,
                'service': 'lambda',
                'result': result,
                'method': 'keyword_backup'
            })
        
        # Keyword backup for IAM requests
        iam_keywords = ['iam', 'user', 'role', 'policy']
        if any(keyword in request_lower for keyword in iam_keywords):
            result = route_to_service('iam', user_request, body)
            return create_response(200, {
                'request': user_request,
                'service': 'iam',
                'result': result,
                'method': 'keyword_backup'
            })
        
        # Keyword backup for CloudWatch requests
        cloudwatch_keywords = ['cloudwatch', 'metrics', 'alarm', 'monitoring']
        if any(keyword in request_lower for keyword in cloudwatch_keywords):
            result = route_to_service('cloudwatch', user_request, body)
            return create_response(200, {
                'request': user_request,
                'service': 'cloudwatch',
                'result': result,
                'method': 'keyword_backup'
            })
        
        # Fallback
        result = handle_universal_aws_request(user_request)
        return create_response(200, {
            'request': user_request,
            'service': 'aws-universal',
            'result': result
        })
        
    except Exception as e:
        return create_response(500, {'error': str(e)})

def handle_service_help(service):
    """Handle service-specific help requests"""
    service_help = {
        'iam': {
            'service': 'IAM (Identity and Access Management)',
            'capabilities': [
                '👥 List all IAM users',
                '🔐 Show IAM roles',
                '📋 List IAM policies',
                '🔑 Display user permissions',
                '👤 Show user details and access keys'
            ],
            'examples': [
                'List IAM users',
                'Show IAM roles',
                'List IAM policies',
                'Show user permissions'
            ]
        },
        's3': {
            'service': 'S3 (Simple Storage Service)',
            'capabilities': [
                '📦 List all S3 buckets',
                '📁 List objects in any bucket',
                '📤 Upload files to buckets',
                '🔄 Move objects between buckets',
                '💾 Show bucket contents with file counts'
            ],
            'examples': [
                'List my S3 buckets',
                'Show objects in my-bucket',
                'Upload file.txt to my-bucket',
                'Move object source-bucket/file.pdf to dest-bucket'
            ]
        },
        'ec2': {
            'service': 'EC2 (Elastic Compute Cloud)',
            'capabilities': [
                '🖥️ List all EC2 instances',
                '▶️ Start stopped instances',
                '⏹️ Stop running instances',
                '🔄 Reboot instances',
                '📊 Show instance status and details'
            ],
            'examples': [
                'List EC2 instances',
                'Start instance i-1234567890abcdef0',
                'Stop instance i-1234567890abcdef0',
                'Reboot my instances'
            ]
        },
        'lambda': {
            'service': 'Lambda (Serverless Functions)',
            'capabilities': [
                '⚡ List all Lambda functions',
                '📋 Show function details and configurations',
                '🔍 View function runtime information',
                '📊 Display function statistics'
            ],
            'examples': [
                'List Lambda functions',
                'Show my Lambda functions',
                'Lambda function details'
            ]
        },
        'cloudwatch': {
            'service': 'CloudWatch (Monitoring)',
            'capabilities': [
                '📊 Show CloudWatch alarms',
                '📈 Display metrics and statistics',
                '🔔 List alarm states',
                '📉 Monitor resource usage'
            ],
            'examples': [
                'Show CloudWatch alarms',
                'CloudWatch metrics',
                'How many times my Lambda ran today'
            ]
        }
    }
    
    info = service_help.get(service, {})
    return {
        'message': f"Here's what I can help you with for {info.get('service', service.upper())}:",
        'capabilities': info.get('capabilities', []),
        'examples': info.get('examples', []),
        'service_name': info.get('service', service.upper())
    }

def handle_general_help():
    """Handle general help requests"""
    return {
        'message': '🤖 I can help you manage these AWS services:',
        'services': {
            'S3': 'Storage - List buckets, upload files, manage objects',
            'EC2': 'Compute - Manage instances, start/stop/reboot',
            'Lambda': 'Serverless - List and monitor functions',
            'IAM': 'Security - Manage users, roles, permissions',
            'CloudWatch': 'Monitoring - View alarms and metrics'
        },
        'tip': 'Ask "How can you help me with IAM?" for specific capabilities!'
    }

def handle_universal_aws_request(user_request):
    """Handle unrecognized requests"""
    return {
        'message': f'I understand you\'re asking about: "{user_request}"',
        'suggestion': 'I can help with AWS services like S3, EC2, Lambda, IAM, and CloudWatch.',
        'examples': [
            'List my S3 buckets',
            'Show EC2 instances',
            'What services can you help me with?'
        ]
    }

def route_to_service(service: str, request: str, body: Dict = None, parsed_intent: Dict = None) -> Dict[str, Any]:
    """Route to service handlers"""
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
        
        if parsed_intent and parsed_intent.get('parameters'):
            payload['ai_parameters'] = parsed_intent['parameters']
        
        if body:
            if body.get('file_data'):
                payload['file_data'] = body['file_data']
            if body.get('file_name'):
                payload['file_name'] = body['file_name']
            if body.get('file_type'):
                payload['file_type'] = body['file_type']
        
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