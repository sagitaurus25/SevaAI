import json
import boto3
from typing import Dict, Any

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """S3 Service Lambda - Handles all S3 operations"""
    try:
        request = event.get('request', '').lower()
        operation = event.get('operation', '')
        parameters = event.get('parameters', {})
        
        if 'list' in request and 'bucket' in request:
            return list_buckets()
        elif 'objects' in request or 'files' in request:
            bucket_name = parameters.get('bucket_name', extract_bucket_name(request))
            return list_objects(bucket_name, parameters.get('prefix', ''))
        elif 'create' in request and 'bucket' in request:
            bucket_name = parameters.get('bucket_name', extract_bucket_name(request))
            return create_bucket(bucket_name)
        elif 'delete' in request and 'bucket' in request:
            bucket_name = parameters.get('bucket_name', extract_bucket_name(request))
            return delete_bucket(bucket_name)
        elif 'upload' in request or 'copy' in request:
            return handle_file_operations(request, parameters)
        else:
            return {
                'error': 'S3 operation not recognized',
                'supported_operations': [
                    'List all buckets',
                    'List objects in bucket-name',
                    'Create bucket bucket-name',
                    'Delete bucket bucket-name',
                    'Upload file to bucket-name'
                ]
            }
            
    except Exception as e:
        return {'error': f'S3 service error: {str(e)}'}

def list_buckets():
    """List all S3 buckets"""
    try:
        response = s3_client.list_buckets()
        bucket_names = [bucket['Name'] for bucket in response['Buckets']]
        
        # Generate follow-up questions for each bucket
        follow_up_questions = []
        for bucket_name in bucket_names[:4]:  # Limit to first 4 buckets to avoid too many questions
            follow_up_questions.extend([
                f"Show objects in {bucket_name}",
                f"Delete bucket {bucket_name}"
            ])
        
        return {
            'buckets': bucket_names,
            'count': len(bucket_names),
            'follow_up_questions': follow_up_questions
        }
    except Exception as e:
        return {'error': f'Failed to list buckets: {str(e)}'}

def list_objects(bucket_name, prefix=''):
    """List objects in a bucket"""
    if not bucket_name:
        return {'error': 'Bucket name is required'}
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix,
            MaxKeys=50
        )
        
        object_names = [obj['Key'] for obj in response.get('Contents', [])]
        
        return {
            'bucket': bucket_name,
            'objects': object_names,
            'count': len(object_names)
        }
    except Exception as e:
        return {'error': f'Failed to list objects in {bucket_name}: {str(e)}'}

def create_bucket(bucket_name):
    """Create a new S3 bucket"""
    if not bucket_name:
        return {'error': 'Bucket name is required'}
    
    try:
        s3_client.create_bucket(Bucket=bucket_name)
        return {'message': f'Bucket {bucket_name} created successfully'}
    except Exception as e:
        return {'error': f'Failed to create bucket {bucket_name}: {str(e)}'}

def delete_bucket(bucket_name):
    """Delete an S3 bucket (must be empty)"""
    if not bucket_name:
        return {'error': 'Bucket name is required'}
    
    try:
        s3_client.delete_bucket(Bucket=bucket_name)
        return {'message': f'Bucket {bucket_name} deleted successfully'}
    except Exception as e:
        return {'error': f'Failed to delete bucket {bucket_name}: {str(e)}'}

def handle_file_operations(request, parameters):
    """Handle file upload/copy operations"""
    return {
        'operation': 'file_operations',
        'message': 'File operations not implemented yet',
        'request': request,
        'parameters': parameters
    }

def extract_bucket_name(request):
    """Extract bucket name from natural language request"""
    words = request.split()
    
    # Handle "Create a new bucket called bucket-name" pattern
    if 'called' in words:
        called_index = words.index('called')
        if called_index + 1 < len(words):
            return words[called_index + 1]
    
    # Handle "bucket bucket-name" pattern
    for i, word in enumerate(words):
        if word == 'bucket' and i + 1 < len(words):
            next_word = words[i + 1]
            if next_word != 'called':  # Skip if it's "bucket called"
                return next_word
    
    # Look for words with hyphens (likely bucket names)
    for word in words:
        if '-' in word and len(word) > 10:  # Bucket names are usually longer
            return word
    
    return None