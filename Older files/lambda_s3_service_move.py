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
        elif 'move' in request:
            return move_object(request)
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
                    'Move object from bucket1 to bucket2',
                    'Upload file to bucket-name'
                ]
            }
            
    except Exception as e:
        return {'error': f'S3 service error: {str(e)}'}

def move_object(request):
    """Move object between buckets"""
    try:
        # Parse source and destination from request
        words = request.split()
        
        # Find 'from' and 'to' keywords
        from_idx = next((i for i, word in enumerate(words) if word == 'from'), None)
        to_idx = next((i for i, word in enumerate(words) if word == 'to'), None)
        
        if not from_idx or not to_idx:
            return {'error': 'Could not parse source and destination buckets'}
        
        source_bucket = words[from_idx + 1] if from_idx + 1 < len(words) else None
        dest_bucket = words[to_idx + 1] if to_idx + 1 < len(words) else None
        
        if not source_bucket or not dest_bucket:
            return {'error': 'Source and destination buckets required'}
        
        # Get first object from source bucket to move
        response = s3_client.list_objects_v2(Bucket=source_bucket, MaxKeys=1)
        if not response.get('Contents'):
            return {'error': f'No objects found in {source_bucket}'}
        
        object_key = response['Contents'][0]['Key']
        
        # Copy object to destination
        copy_source = {'Bucket': source_bucket, 'Key': object_key}
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=dest_bucket,
            Key=object_key
        )
        
        # Delete from source
        s3_client.delete_object(Bucket=source_bucket, Key=object_key)
        
        return {
            'message': f'Moved {object_key} from {source_bucket} to {dest_bucket}',
            'object': object_key,
            'source': source_bucket,
            'destination': dest_bucket
        }
        
    except Exception as e:
        return {'error': f'Failed to move object: {str(e)}'}

def list_buckets():
    """List all S3 buckets"""
    try:
        response = s3_client.list_buckets()
        bucket_names = [bucket['Name'] for bucket in response['Buckets']]
        
        # Get object counts for each bucket and sort by count
        bucket_object_counts = []
        for bucket_name in bucket_names:
            try:
                objects_response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
                object_count = objects_response.get('KeyCount', 0)
                bucket_object_counts.append((bucket_name, object_count))
            except:
                bucket_object_counts.append((bucket_name, 0))
        
        # Sort buckets by object count (descending) and take top 4
        bucket_object_counts.sort(key=lambda x: x[1], reverse=True)
        top_buckets = bucket_object_counts[:4]
        
        # Generate follow-up questions for buckets with most objects
        follow_up_questions = []
        for bucket_name, count in top_buckets:
            if count > 0:
                follow_up_questions.append(f"Show objects in {bucket_name}")
            follow_up_questions.append(f"Delete bucket {bucket_name}")
        
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
    """Handle file upload operations"""
    return {
        'operation': 'file_operations',
        'message': 'File upload not implemented yet',
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