import json
import boto3
from typing import Dict, Any

lambda_client = boto3.client('lambda')
bedrock_client = boto3.client('bedrock-runtime')

def lambda_handler(event, context):
    """Universal AWS Router with Nova Micro NLP - Handles any AWS service automatically"""
    
    if event.get('httpMethod') == 'OPTIONS':
        return create_response(200, {})
    
    try:
        body = json.loads(event.get('body', '{}'))
        user_request = body.get('request', '')
        
        if not user_request:
            return create_response(400, {'error': 'No request provided'})
        
        # Use Nova Micro to parse the request intelligently
        parsed_intent = parse_with_nova(user_request)
        
        if parsed_intent.get('error'):
            # Fallback to original logic if Nova fails
            return handle_fallback(user_request, body)
        
        # Route based on Nova's understanding
        service = parsed_intent.get('service', 'unknown')
        
        if service != 'unknown':
            result = route_to_service(service, user_request, body, parsed_intent)
            return create_response(200, {
                'request': user_request,
                'service': service,
                'result': result,
                'ai_parsed': True
            })
        
        # If no specific service, try universal AWS handler
        result = handle_universal_aws_request(user_request)
        
        return create_response(200, {
            'request': user_request,
            'service': 'aws-universal',
            'result': result
        })
        
    except Exception as e:
        return create_response(500, {'error': str(e)})

def parse_with_nova(user_request):
    """Use Nova Micro to parse user request into structured intent"""
    try:
        prompt = f"""Parse this AWS request into JSON format:
"{user_request}"

Return only JSON with these fields:
{{
  "service": "s3|ec2|lambda|iam|cloudwatch|unknown",
  "action": "list|upload|start|stop|show|move|explain",
  "parameters": {{"bucket": "name", "instance": "id", "file": "name"}},
  "confidence": 0.9
}}

Examples:
"Upload file.txt to my-bucket" → {{"service": "s3", "action": "upload", "parameters": {{"bucket": "my-bucket", "file": "file.txt"}}}}
"What are my EC2 instances" → {{"service": "ec2", "action": "list", "parameters": {{}}}}
"Tell me about CloudWatch" → {{"service": "cloudwatch", "action": "explain", "parameters": {{}}}}"""

        response = bedrock_client.invoke_model(
            modelId='amazon.nova-micro-v1:0',
            body=json.dumps({
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 200,
                'temperature': 0.1
            })
        )
        
        result = json.loads(response['body'].read())
        content = result['output']['message']['content'][0]['text']
        
        # Extract JSON from response
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        
        return {'error': 'Could not parse Nova response'}
        
    except Exception as e:
        return {'error': f'Nova parsing failed: {str(e)}'}

def handle_fallback(user_request, body):
    """Fallback to original keyword-based logic"""
    service = determine_service_fallback(user_request)
    
    if service != 'unknown':
        result = route_to_service(service, user_request, body)
        return create_response(200, {
            'request': user_request,
            'service': service,
            'result': result,
            'ai_parsed': False
        })
    
    result = handle_universal_aws_request(user_request)
    return create_response(200, {
        'request': user_request,
        'service': 'aws-universal',
        'result': result
    })

def determine_service_fallback(request: str) -> str:
    """Original keyword-based service detection"""
    request_lower = request.lower()
    
    if any(word in request_lower for word in ['bucket', 's3', 'upload', 'objects', 'move']):
        return 's3'
    if any(word in request_lower for word in ['instance', 'ec2']):
        return 'ec2'
    if any(word in request_lower for word in ['lambda', 'function']):
        return 'lambda'
    if any(word in request_lower for word in ['iam', 'user', 'role']):
        return 'iam'
    if any(word in request_lower for word in ['alarm', 'cloudwatch', 'metrics']):
        return 'cloudwatch'
    
    return 'unknown'

def handle_help_request(user_request):
    """Handle help requests for specific services"""
    request_lower = user_request.lower()
    
    service_help = {
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
        }
    }
    
    # Check which service the user is asking about
    for service_key, service_info in service_help.items():
        if service_key in request_lower or service_info['service'].lower() in request_lower:
            return {
                'message': f"Here's what I can help you with for {service_info['service']}:",
                'capabilities': service_info['capabilities'],
                'examples': service_info['examples'],
                'service_name': service_info['service']
            }
    
    return {
        'message': 'I can help you manage these AWS services:',
        'services': {
            'S3': 'Storage - List buckets, upload files, manage objects',
            'EC2': 'Compute - Manage instances, start/stop/reboot',
            'Lambda': 'Serverless - List and monitor functions',
            'IAM': 'Security - Manage users, roles, permissions',
            'CloudWatch': 'Monitoring - View alarms and metrics'
        },
        'tip': 'Ask "How can you help me with S3?" for specific capabilities!'
    }

def handle_universal_aws_request(user_request):
    """Handle any AWS service request universally"""
    try:
        # Check for help requests first
        if 'how can you help' in user_request.lower() or 'what can you do' in user_request.lower():
            return handle_help_request(user_request)
        
        return {
            'message': f'I understand you\'re asking about: "{user_request}"',
            'suggestion': 'I can help with AWS services like S3, EC2, Lambda, IAM, and CloudWatch.',
            'examples': [
                'List my S3 buckets',
                'Show EC2 instances', 
                'Upload file to bucket',
                'How can you help me with S3?'
            ]
        }
            
    except Exception as e:
        return {'error': f'Universal handler error: {str(e)}'}

def route_to_service(service: str, request: str, body: Dict = None, parsed_intent: Dict = None) -> Dict[str, Any]:
    """Route to existing service handlers with AI-parsed parameters"""
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
        
        # Add AI-parsed parameters if available
        if parsed_intent and parsed_intent.get('parameters'):
            payload['ai_parameters'] = parsed_intent['parameters']
        
        # Add file data if present
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