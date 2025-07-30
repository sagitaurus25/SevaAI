import json
import boto3
from typing import Dict, Any

lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    """Universal AWS Router - Handles any AWS service automatically"""
    
    if event.get('httpMethod') == 'OPTIONS':
        return create_response(200, {})
    
    try:
        body = json.loads(event.get('body', '{}'))
        user_request = body.get('request', '')
        
        if not user_request:
            return create_response(400, {'error': 'No request provided'})
        
        # Try to handle with existing services first
        service = determine_service(user_request)
        
        if service != 'unknown':
            result = route_to_service(service, user_request, body)
            return create_response(200, {
                'request': user_request,
                'service': service,
                'result': result
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

def determine_service(request: str) -> str:
    """Quick check for existing services"""
    request_lower = request.lower()
    
    # Existing services with dedicated handlers
    if any(word in request_lower for word in ['bucket', 's3', 'upload']):
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

def handle_universal_aws_request(user_request):
    """Handle any AWS service request universally"""
    try:
        # Extract potential AWS service names
        aws_services = [
            'apigateway', 'rds', 'dynamodb', 'sns', 'sqs', 'elasticache', 
            'elasticsearch', 'kinesis', 'redshift', 'route53', 'cloudfront',
            'elb', 'autoscaling', 'efs', 'fsx', 'backup', 'config'
        ]
        
        request_lower = user_request.lower()
        detected_service = None
        
        # Check for service names in request
        for service in aws_services:
            if service in request_lower or service.replace('-', '') in request_lower:
                detected_service = service
                break
        
        # Check for common service aliases
        service_aliases = {
            'api': 'apigateway',
            'gateway': 'apigateway', 
            'database': 'rds',
            'db': 'rds',
            'table': 'dynamodb',
            'queue': 'sqs',
            'topic': 'sns',
            'cache': 'elasticache',
            'search': 'elasticsearch',
            'stream': 'kinesis',
            'dns': 'route53',
            'cdn': 'cloudfront',
            'load balancer': 'elb',
            'balancer': 'elb'
        }
        
        if not detected_service:
            for alias, service in service_aliases.items():
                if alias in request_lower:
                    detected_service = service
                    break
        
        if detected_service:
            return get_service_info(detected_service, user_request)
        else:
            return {
                'message': f'I understand you\'re asking about: "{user_request}"',
                'suggestion': 'I can help with AWS services like API Gateway, RDS, DynamoDB, SNS, SQS, and more. Try being more specific about the service.',
                'examples': [
                    'List API Gateway APIs',
                    'Show RDS databases', 
                    'List DynamoDB tables',
                    'Show SQS queues'
                ]
            }
            
    except Exception as e:
        return {'error': f'Universal handler error: {str(e)}'}

def get_service_info(service_name, user_request):
    """Get basic info about any AWS service"""
    try:
        # Use boto3 to dynamically create client
        client = boto3.client(service_name.replace('-', ''))
        
        # Common list operations for different services
        list_operations = {
            'apigateway': ('get_rest_apis', 'items', 'name'),
            'rds': ('describe_db_instances', 'DBInstances', 'DBInstanceIdentifier'),
            'dynamodb': ('list_tables', 'TableNames', None),
            'sns': ('list_topics', 'Topics', 'TopicArn'),
            'sqs': ('list_queues', 'QueueUrls', None),
            'elasticache': ('describe_cache_clusters', 'CacheClusters', 'CacheClusterId'),
            'kinesis': ('list_streams', 'StreamNames', None),
            'route53': ('list_hosted_zones', 'HostedZones', 'Name'),
            'cloudfront': ('list_distributions', 'DistributionList.Items', 'Id'),
            'elb': ('describe_load_balancers', 'LoadBalancers', 'LoadBalancerName')
        }
        
        if service_name in list_operations:
            operation, key_path, name_field = list_operations[service_name]
            
            # Call the AWS API
            response = getattr(client, operation)()
            
            # Extract data based on key path
            data = response
            for key in key_path.split('.'):
                data = data.get(key, [])
            
            # Format results
            if name_field:
                items = [item.get(name_field, str(item)) for item in data]
            else:
                items = data if isinstance(data, list) else [str(data)]
            
            return {
                'service': service_name.upper(),
                'items': items[:10],  # Limit to 10 items
                'count': len(items),
                'message': f'Found {len(items)} {service_name} resources'
            }
        else:
            return {
                'service': service_name.upper(),
                'message': f'{service_name.upper()} service detected but no handler available yet',
                'suggestion': 'This service is supported by AWS but needs a custom handler'
            }
            
    except Exception as e:
        return {
            'service': service_name.upper(),
            'error': f'Could not access {service_name}: {str(e)}',
            'suggestion': 'Make sure you have permissions for this service'
        }

def route_to_service(service: str, request: str, body: Dict = None) -> Dict[str, Any]:
    """Route to existing service handlers"""
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