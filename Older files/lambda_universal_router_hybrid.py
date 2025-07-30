import json
import boto3
from typing import Dict, Any

lambda_client = boto3.client('lambda')
bedrock_client = boto3.client('bedrock-runtime')

def lambda_handler(event, context):
    """Universal AWS Router - Hybrid approach with keyword backup for help"""
    
    if event.get('httpMethod') == 'OPTIONS':
        return create_response(200, {})
    
    try:
        body = json.loads(event.get('body', '{}'))
        user_request = body.get('request', '')
        
        if not user_request:
            return create_response(400, {'error': 'No request provided'})
        
        # Quick keyword check for help requests (backup)
        help_keywords = ['help', 'services', 'what can you do', 'what do you support', 'capabilities']
        if any(keyword in user_request.lower() for keyword in help_keywords):
            result = handle_help_request(user_request)
            return create_response(200, {
                'request': user_request,
                'service': 'help',
                'result': result,
                'ai_parsed': False,
                'method': 'keyword_backup'
            })
        
        # Send to Nova for everything else
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
            'result': result,
            'ai_parsed': True
        })
        
    except Exception as e:
        return create_response(500, {'error': str(e)})

def parse_with_nova(user_request):
    """Use Nova Micro for non-help requests"""
    try:
        prompt = f"""Parse this AWS request into JSON:
"{user_request}"

Return JSON:
{{
  "service": "s3|ec2|lambda|iam|cloudwatch|unknown",
  "action": "list|upload|start|stop|show|move|explain",
  "parameters": {{"bucket": "name", "instance": "id"}}
}}

Examples:
"Upload file.txt to my-bucket" → {{"service": "s3", "action": "upload", "parameters": {{"bucket": "my-bucket"}}}}
"What are my EC2 instances" → {{"service": "ec2", "action": "list", "parameters": {{}}}}"""

        response = bedrock_client.invoke_model(
            modelId='amazon.nova-micro-v1:0',
            body=json.dumps({
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 150,
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
    """Handle help requests with keyword backup"""
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
        'tip': 'Ask "How can you help me with S3?" for specific capabilities!'
    }

def handle_fallback(user_request, body):
    """Fallback when Nova fails"""
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
        },
        'ai_parsed': False
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