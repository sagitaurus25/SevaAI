import json
import boto3
from typing import Dict, Any

lambda_client = boto3.client('lambda')
bedrock_client = boto3.client('bedrock-runtime')

def lambda_handler(event, context):
    """Universal AWS Router - Keyword backup for all major services"""
    
    if event.get('httpMethod') == 'OPTIONS':
        return create_response(200, {})
    
    try:
        body = json.loads(event.get('body', '{}'))
        user_request = body.get('request', '')
        
        if not user_request:
            return create_response(400, {'error': 'No request provided'})
        
        request_lower = user_request.lower()
        
        # Keyword backup for help requests
        help_keywords = ['help', 'services', 'what can you do', 'what do you support', 'capabilities']
        if any(keyword in request_lower for keyword in help_keywords):
            result = handle_help_request(user_request)
            return create_response(200, {
                'request': user_request,
                'service': 'help',
                'result': result,
                'method': 'keyword_backup'
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
        
        # Send to Nova only if no keywords match
        parsed_intent = parse_with_nova(user_request)
        
        if parsed_intent.get('error'):
            return handle_fallback(user_request, body)
        
        service = parsed_intent.get('service', 'unknown')
        
        if service != 'unknown':
            result = route_to_service(service, user_request, body, parsed_intent)
            return create_response(200, {
                'request': user_request,
                'service': service,
                'result': result,
                'ai_parsed': True
            })
        
        result = handle_universal_aws_request(user_request)
        return create_response(200, {
            'request': user_request,
            'service': 'aws-universal',
            'result': result
        })
        
    except Exception as e:
        return create_response(500, {'error': str(e)})

def parse_with_nova(user_request):
    """Use Nova Micro for unmatched requests"""
    try:
        prompt = f"""Parse this request into JSON:
"{user_request}"

Return JSON:
{{
  "service": "unknown",
  "action": "unknown"
}}"""

        response = bedrock_client.invoke_model(
            modelId='amazon.nova-micro-v1:0',
            body=json.dumps({
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 100,
                'temperature': 0.1
            })
        )
        
        result = json.loads(response['body'].read())
        content = result['output']['message']['content'][0]['text']
        
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        
        return {'error': 'Could not parse Nova response'}
        
    except Exception as e:
        return {'error': f'Nova parsing failed: {str(e)}'}

def handle_help_request(user_request):
    """Handle help requests"""
    return {
        'message': '🤖 I can help you manage these AWS services:',
        'services': {
            'S3': 'Storage - List buckets, upload files, manage objects',
            'EC2': 'Compute - Manage instances, start/stop/reboot',
            'Lambda': 'Serverless - List and monitor functions',
            'IAM': 'Security - Manage users, roles, permissions',
            'CloudWatch': 'Monitoring - View alarms and metrics'
        },
        'examples': [
            'List my S3 buckets',
            'Show EC2 instances',
            'Upload file to bucket',
            'What are my Lambda functions?'
        ],
        'tip': 'All requests are handled instantly with keyword detection!'
    }

def handle_fallback(user_request, body):
    """Fallback when everything fails"""
    return create_response(200, {
        'request': user_request,
        'service': 'fallback',
        'result': {
            'message': f'I understand you\'re asking about: "{user_request}"',
            'suggestion': 'I can help with AWS services like S3, EC2, Lambda, IAM, and CloudWatch.',
            'examples': [
                'List my S3 buckets',
                'Show EC2 instances',
                'What services can you help me with?'
            ]
        }
    })

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