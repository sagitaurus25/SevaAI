import json
import boto3
import base64
from typing import Dict, Any

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """S3 Service Lambda - Handles all S3 operations including upload"""
    try:
        request = event.get('request', '').lower()
        
        if 'list' in request and 'bucket' in request:
            return list_buckets()
        elif 'objects' in request or 'files' in request:
            bucket_name = extract_bucket_name(request)
            return list_objects(bucket_name)
        elif 'move' in request:
            return move_object(request)
        elif 'upload' in request:
            return handle_file_upload(event)
        else:
            return {
                'error': 'S3 operation not recognized',
                'supported_operations': [
                    'List all buckets',
                    'List objects in bucket-name',
                    'Move object from bucket1 to bucket2',
                    'Upload file to bucket-name'
                ]
            }
            
    except Exception as e:
        return {'error': f'S3 service error: {str(e)}'}

def handle_file_upload(event):
    """Handle file upload to S3"""
    try:
        file_data = event.get('file_data')
        file_name = event.get('file_name')
        request = event.get('request', '').lower()
        
        if not file_data or not file_name:
            return {'error': 'No file data provided'}
        
        # Extract bucket name from request
        words = request.split()
        bucket_name = None
        
        # Look for "to bucket-name" or "to bucket bucket-name" pattern
        if 'to' in words:
            to_index = words.index('to')
            if to_index + 1 < len(words):
                next_word = words[to_index + 1]
                if next_word == 'bucket' and to_index + 2 < len(words):
                    bucket_name = words[to_index + 2]
                else:
                    bucket_name = next_word
        
        if not bucket_name:
            return {'error': 'Please specify bucket name: "upload file.txt to my-bucket"'}
        
        # Decode base64 file data
        file_content = base64.b64decode(file_data)
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=file_content
        )
        
        return {
            'message': f'✅ Successfully uploaded {file_name} to {bucket_name}',
            'file_name': file_name,
            'bucket': bucket_name,
            'size': len(file_content)
        }
        
    except Exception as e:
        return {'error': f'Upload failed: {str(e)}'}

def move_object(request):
    """Move object between buckets"""
    try:
        words = request.split()
        from_idx = next((i for i, word in enumerate(words) if word == 'from'), None)
        to_idx = next((i for i, word in enumerate(words) if word == 'to'), None)
        
        if not from_idx or not to_idx:
            return {'error': 'Could not parse source and destination buckets'}
        
        source_bucket = words[from_idx + 1] if from_idx + 1 < len(words) else None
        dest_bucket = words[to_idx + 1] if to_idx + 1 < len(words) else None
        
        if not source_bucket or not dest_bucket:
            return {'error': 'Source and destination buckets required'}
        
        response = s3_client.list_objects_v2(Bucket=source_bucket, MaxKeys=1)
        if not response.get('Contents'):
            return {'error': f'No objects found in {source_bucket}'}
        
        object_key = response['Contents'][0]['Key']
        
        copy_source = {'Bucket': source_bucket, 'Key': object_key}
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=dest_bucket,
            Key=object_key
        )
        
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
        
        return {
            'buckets': bucket_names,
            'count': len(bucket_names)
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

def extract_bucket_name(request):
    """Extract bucket name from natural language request"""
    words = request.split()
    
    # Look for "in bucket-name" pattern
    if 'in' in words:
        in_index = words.index('in')
        if in_index + 1 < len(words):
            return words[in_index + 1]
    
    # Look for "bucket bucket-name" pattern
    for i, word in enumerate(words):
        if word == 'bucket' and i + 1 < len(words):
            next_word = words[i + 1]
            if next_word != 'called':
                return next_word
    
    # Look for words with dashes (common bucket naming)
    for word in words:
        if '-' in word and len(word) > 5:
            return word
    
    # Look for alphanumeric words that could be bucket names
    for word in words:
        if len(word) > 8 and word.isalnum():
            return word
    
    return None