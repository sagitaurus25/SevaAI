import json
import boto3
import re
from typing import Dict, Any

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
s3_client = boto3.client('s3')
ec2_client = boto3.client('ec2')

def lambda_handler(event, context):
    """
    Main Lambda handler for AWS Agent
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
        user_request = body.get('request', '')
        
        if not user_request:
            return create_response(400, {'error': 'No request provided'})
        
        # Step 1: Analyze the request and determine AWS actions
        analysis = analyze_request(user_request)
        
        # Step 2: Execute the AWS actions
        result = execute_aws_actions(analysis)
        
        return create_response(200, {
            'request': user_request,
            'analysis': analysis,
            'result': result
        })
        
    except Exception as e:
        return create_response(500, {'error': str(e)})

def analyze_request(user_request: str) -> Dict[str, Any]:
    """
    Use Bedrock to analyze the user request and convert to AWS actions
    """
    prompt = f"""
    You are an AWS automation expert. Analyze this user request and convert it to specific AWS API actions.
    
    User Request: "{user_request}"
    
    Please respond with a JSON object containing:
    {{
        "intent": "brief description of what user wants",
        "aws_service": "primary AWS service needed (s3, ec2, etc)",
        "actions": [
            {{
                "service": "aws_service_name",
                "operation": "specific_operation",
                "parameters": {{"key": "value"}}
            }}
        ],
        "safety_check": "any warnings or confirmations needed"
    }}
    
    Focus on these common operations:
    - S3: list buckets, list objects, copy objects, create folders
    - EC2: list instances, describe instances, start/stop instances
    
    Only suggest safe, read-only operations unless explicitly requested otherwise.
    """
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 1000,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            })
        )
        
        response_body = json.loads(response['body'].read())
        analysis_text = response_body['content'][0]['text']
        
        # Extract JSON from the response
        json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            return {'error': 'Could not parse analysis', 'raw_response': analysis_text}
            
    except Exception as e:
        return {'error': f'Analysis failed: {str(e)}'}

def execute_aws_actions(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the AWS actions based on the analysis
    """
    if 'error' in analysis:
        return analysis
    
    results = []
    
    for action in analysis.get('actions', []):
        try:
            service = action.get('service', '').lower()
            operation = action.get('operation', '')
            parameters = action.get('parameters', {})
            
            if service == 's3':
                result = execute_s3_action(operation, parameters)
            elif service == 'ec2':
                result = execute_ec2_action(operation, parameters)
            else:
                result = {'error': f'Service {service} not supported yet'}
            
            results.append({
                'action': action,
                'result': result
            })
            
        except Exception as e:
            results.append({
                'action': action,
                'error': str(e)
            })
    
    return {'actions_executed': results}

def execute_s3_action(operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute S3 operations
    """
    try:
        if operation == 'list_buckets':
            response = s3_client.list_buckets()
            return {'buckets': [bucket['Name'] for bucket in response['Buckets']]}
        
        elif operation == 'list_objects':
            bucket_name = parameters.get('bucket_name')
            prefix = parameters.get('prefix', '')
            
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=100
            )
            
            objects = []
            for obj in response.get('Contents', []):
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
            
            return {'objects': objects, 'count': len(objects)}
        
        elif operation == 'copy_objects':
            source_bucket = parameters.get('source_bucket')
            target_bucket = parameters.get('target_bucket', source_bucket)
            source_prefix = parameters.get('source_prefix', '')
            target_prefix = parameters.get('target_prefix', '')
            file_pattern = parameters.get('file_pattern', '')
            
            # List objects matching pattern
            response = s3_client.list_objects_v2(
                Bucket=source_bucket,
                Prefix=source_prefix
            )
            
            copied_files = []
            for obj in response.get('Contents', []):
                if file_pattern and file_pattern.lower() not in obj['Key'].lower():
                    continue
                
                # Copy object
                source_key = obj['Key']
                target_key = f"{target_prefix}/{source_key.split('/')[-1]}"
                
                s3_client.copy_object(
                    CopySource={'Bucket': source_bucket, 'Key': source_key},
                    Bucket=target_bucket,
                    Key=target_key
                )
                
                copied_files.append({
                    'from': source_key,
                    'to': target_key
                })
            
            return {'copied_files': copied_files, 'count': len(copied_files)}
        
        else:
            return {'error': f'S3 operation {operation} not supported'}
            
    except Exception as e:
        return {'error': f'S3 operation failed: {str(e)}'}

def execute_ec2_action(operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute EC2 operations
    """
    try:
        if operation == 'list_instances':
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
            
            return {'instances': instances, 'count': len(instances)}
        
        else:
            return {'error': f'EC2 operation {operation} not supported'}
            
    except Exception as e:
        return {'error': f'EC2 operation failed: {str(e)}'}

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create properly formatted API Gateway response
    """
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