import json
import boto3
from typing import Dict, Any

# Initialize AWS clients
s3_client = boto3.client('s3')
ec2_client = boto3.client('ec2')

def lambda_handler(event, context):
    """
    Main Lambda handler for AWS Agent - Simple version without Bedrock
    """
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
        user_request = body.get('request', '').lower()
        
        if not user_request:
            return create_response(400, {'error': 'No request provided'})
        
        # Simple pattern matching instead of Bedrock
        if 's3' in user_request and 'bucket' in user_request:
            if 'list' in user_request:
                result = list_s3_buckets()
            else:
                result = {'error': 'S3 operation not recognized. Try: "List all my S3 buckets"'}
        elif 'ec2' in user_request and 'instance' in user_request:
            result = list_ec2_instances()
        else:
            result = {
                'error': 'Request not understood. Try: "List all my S3 buckets" or "List all my EC2 instances"',
                'supported_requests': [
                    'List all my S3 buckets',
                    'List all my EC2 instances'
                ]
            }
        
        return create_response(200, {
            'request': user_request,
            'result': result
        })
        
    except Exception as e:
        return create_response(500, {'error': str(e)})

def list_s3_buckets() -> Dict[str, Any]:
    """List all S3 buckets"""
    try:
        response = s3_client.list_buckets()
        buckets = []
        for bucket in response['Buckets']:
            buckets.append({
                'name': bucket['Name'],
                'creation_date': bucket['CreationDate'].isoformat()
            })
        return {
            'buckets': buckets,
            'count': len(buckets)
        }
    except Exception as e:
        return {'error': f'Failed to list S3 buckets: {str(e)}'}

def list_ec2_instances() -> Dict[str, Any]:
    """List all EC2 instances"""
    try:
        response = ec2_client.describe_instances()
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append({
                    'instance_id': instance['InstanceId'],
                    'state': instance['State']['Name'],
                    'instance_type': instance['InstanceType'],
                    'launch_time': instance['LaunchTime'].isoformat()
                })
        return {
            'instances': instances,
            'count': len(instances)
        }
    except Exception as e:
        return {'error': f'Failed to list EC2 instances: {str(e)}'}

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