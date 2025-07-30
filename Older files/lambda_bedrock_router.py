import json
import boto3
from typing import Dict, Any

lambda_client = boto3.client('lambda')
bedrock_client = boto3.client('bedrock-runtime')

def lambda_handler(event, context):
    """Bedrock-powered Router - Uses AI to understand and route requests"""
    
    if event.get('httpMethod') == 'OPTIONS':
        return create_response(200, {})
    
    try:
        body = json.loads(event.get('body', '{}'))
        user_request = body.get('request', '')
        
        if not user_request:
            return create_response(400, {'error': 'No request provided'})
        
        # Use Bedrock to understand the request
        service_info = analyze_with_bedrock(user_request)
        
        if not service_info or service_info.get('service') == 'unknown':
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
        
        # Route to appropriate service
        result = route_to_service(service_info['service'], user_request, service_info)
        
        return create_response(200, {
            'request': user_request,
            'service': service_info['service'],
            'result': result
        })
        
    except Exception as e:
        return create_response(500, {'error': str(e)})

def analyze_with_bedrock(user_request):
    """Use Bedrock to analyze user intent"""
    try:
        prompt = f"""Analyze this AWS request and return JSON:
Request: "{user_request}"

Return format:
{{
    "service": "s3|ec2|lambda|iam|cloudwatch|unknown",
    "action": "list|create|delete|start|stop|move|show",
    "confidence": "high|medium|low"
}}

Examples:
- "list buckets" -> {{"service": "s3", "action": "list", "confidence": "high"}}
- "show instances" -> {{"service": "ec2", "action": "list", "confidence": "high"}}
- "lambda metrics" -> {{"service": "cloudwatch", "action": "show", "confidence": "high"}}"""

        response = bedrock_client.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        result = json.loads(response['body'].read())
        return json.loads(result['content'][0]['text'])
        
    except Exception:
        return {'service': 'unknown', 'action': 'unknown', 'confidence': 'low'}

def route_to_service(service: str, request: str, service_info: Dict) -> Dict[str, Any]:
    """Route to appropriate service Lambda"""
    
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
        payload = {
            'request': request,
            'service': service,
            'bedrock_analysis': service_info
        }
        
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