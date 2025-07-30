import json
import boto3
import os
import re
from botocore.exceptions import ClientError

# Initialize S3 client
s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')

def lambda_handler(event, context):
    """Main Lambda handler for S3 service operations"""
    
    action = event.get('action')
    parameters = event.get('parameters', {})
    session_id = event.get('session_id')
    
    # Route to the appropriate function based on the action
    if action == 'list_buckets':
        return list_buckets()
    elif action == 'list_objects':
        return list_objects(parameters)
    elif action == 'create_bucket':
        return create_bucket(parameters)
    elif action == 'delete_bucket':
        return delete_bucket(parameters)
    elif action == 'upload_object':
        return upload_object(parameters)
    elif action == 'download_object':
        return download_object(parameters)
    elif action == 'delete_object':
        return delete_object(parameters)
    elif action == 'copy_object':
        return copy_object(parameters)
    elif action == 'list_all_files':
        return list_all_files(parameters)
    else:
        return {
            'success': False,
            'message': f"Unsupported S3 action: {action}"
        }

def list_buckets():
    """List all S3 buckets"""
    try:
        response = s3_client.list_buckets()
        
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        
        if not buckets:
            return {
                'success': True,
                'message': "You don't have any S3 buckets.",
                'data': []
            }
        
        message = f"Found {len(buckets)} bucket(s):\n"
        message += "\n".join([f"- {bucket}" for bucket in buckets])
        
        return {
            'success': True,
            'message': message,
            'data': buckets,
            'cli_command': 'aws s3 ls'
        }
    except Exception as e:
        return {
            'success': False,
            'message': f"Error listing buckets: {str(e)}"
        }

def list_objects(parameters):
    """List objects in an S3 bucket"""
    bucket_name = parameters.get('bucket_name')
    prefix = parameters.get('prefix', '')
    
    if not bucket_name:
        return {
            'success': False,
            'message': "Bucket name is required."
        }
    
    try:
        # Check if bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
        
        # List objects
        if prefix:
            response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        else:
            response = s3_client.list_objects_v2(Bucket=bucket_name)
        
        objects = []
        if 'Contents' in response:
            objects = [obj['Key'] for obj in response['Contents']]
        
        if not objects:
            message = f"No objects found in bucket '{bucket_name}'"
            if prefix:
                message += f" with prefix '{prefix}'"
            
            return {
                'success': True,
                'message': message,
                'data': []
            }
        
        message = f"Found {len(objects)} object(s) in bucket '{bucket_name}'"
        if prefix:
            message += f" with prefix '{prefix}'"
        message += ":\n"
        
        # Limit the number of objects shown in the message
        max_display = 20
        displayed_objects = objects[:max_display]
        message += "\n".join([f"- {obj}" for obj in displayed_objects])
        
        if len(objects) > max_display:
            message += f"\n... and {len(objects) - max_display} more"
        
        cli_command = f"aws s3 ls s3://{bucket_name}/"
        if prefix:
            cli_command += prefix
        
        return {
            'success': True,
            'message': message,
            'data': objects,
            'cli_command': cli_command
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            return {
                'success': False,
                'message': f"Bucket '{bucket_name}' does not exist."
            }
        else:
            return {
                'success': False,
                'message': f"Error listing objects: {str(e)}"
            }
    except Exception as e:
        return {
            'success': False,
            'message': f"Error listing objects: {str(e)}"
        }

def create_bucket(parameters):
    """Create a new S3 bucket"""
    bucket_name = parameters.get('bucket_name')
    region = parameters.get('region', 'us-east-1')
    
    if not bucket_name:
        return {
            'success': False,
            'message': "Bucket name is required."
        }
    
    # Validate bucket name
    if not re.match(r'^[a-z0-9.-]{3,63}$', bucket_name):
        return {
            'success': False,
            'message': "Invalid bucket name. Bucket names must be between 3 and 63 characters long and can only contain lowercase letters, numbers, periods, and hyphens."
        }
    
    try:
        # Check if bucket already exists
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            return {
                'success': False,
                'message': f"Bucket '{bucket_name}' already exists."
            }
        except ClientError:
            # Bucket doesn't exist, proceed with creation
            pass
        
        # Create the bucket
        if region == 'us-east-1':
            response = s3_client.create_bucket(Bucket=bucket_name)
        else:
            location = {'LocationConstraint': region}
            response = s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration=location
            )
        
        return {
            'success': True,
            'message': f"Successfully created bucket '{bucket_name}' in region '{region}'.",
            'data': {
                'bucket_name': bucket_name,
                'region': region
            },
            'cli_command': f"aws s3 mb s3://{bucket_name} --region {region}"
        }
    except ClientError as e:
        return {
            'success': False,
            'message': f"Error creating bucket: {str(e)}"
        }
    except Exception as e:
        return {
            'success': False,
            'message': f"Error creating bucket: {str(e)}"
        }

def delete_bucket(parameters):
    """Delete an S3 bucket"""
    bucket_name = parameters.get('bucket_name')
    force = parameters.get('force', False)
    
    if not bucket_name:
        return {
            'success': False,
            'message': "Bucket name is required."
        }
    
    try:
        # Check if bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
        
        # Check if bucket is empty
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        
        if 'Contents' in response and not force:
            return {
                'success': False,
                'message': f"Bucket '{bucket_name}' is not empty. Use 'force: true' to delete all objects and the bucket."
            }
        
        # Delete all objects if force is true
        if force and 'Contents' in response:
            bucket = s3_resource.Bucket(bucket_name)
            bucket.objects.all().delete()
        
        # Delete the bucket
        s3_client.delete_bucket(Bucket=bucket_name)
        
        cli_command = f"aws s3 rb s3://{bucket_name}"
        if force:
            cli_command += " --force"
        
        return {
            'success': True,
            'message': f"Successfully deleted bucket '{bucket_name}'.",
            'cli_command': cli_command
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            return {
                'success': False,
                'message': f"Bucket '{bucket_name}' does not exist."
            }
        else:
            return {
                'success': False,
                'message': f"Error deleting bucket: {str(e)}"
            }
    except Exception as e:
        return {
            'success': False,
            'message': f"Error deleting bucket: {str(e)}"
        }

def upload_object(parameters):
    """Upload an object to S3"""
    bucket_name = parameters.get('bucket_name')
    object_key = parameters.get('object_key')
    file_path = parameters.get('file_path')
    content = parameters.get('content')
    
    if not bucket_name or not object_key:
        return {
            'success': False,
            'message': "Bucket name and object key are required."
        }
    
    if not file_path and not content:
        return {
            'success': False,
            'message': "Either file_path or content must be provided."
        }
    
    try:
        # Check if bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
        
        # Upload the object
        if file_path:
            s3_client.upload_file(file_path, bucket_name, object_key)
            cli_command = f"aws s3 cp {file_path} s3://{bucket_name}/{object_key}"
        else:
            s3_client.put_object(Bucket=bucket_name, Key=object_key, Body=content)
            cli_command = f"echo '{content}' | aws s3 cp - s3://{bucket_name}/{object_key}"
        
        return {
            'success': True,
            'message': f"Successfully uploaded object to s3://{bucket_name}/{object_key}",
            'data': {
                'bucket_name': bucket_name,
                'object_key': object_key
            },
            'cli_command': cli_command
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            return {
                'success': False,
                'message': f"Bucket '{bucket_name}' does not exist."
            }
        else:
            return {
                'success': False,
                'message': f"Error uploading object: {str(e)}"
            }
    except Exception as e:
        return {
            'success': False,
            'message': f"Error uploading object: {str(e)}"
        }

def download_object(parameters):
    """Generate a pre-signed URL to download an object from S3"""
    bucket_name = parameters.get('bucket_name')
    object_key = parameters.get('object_key')
    expiration = parameters.get('expiration', 3600)  # Default 1 hour
    
    if not bucket_name or not object_key:
        return {
            'success': False,
            'message': "Bucket name and object key are required."
        }
    
    try:
        # Check if object exists
        s3_client.head_object(Bucket=bucket_name, Key=object_key)
        
        # Generate pre-signed URL
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
        
        return {
            'success': True,
            'message': f"Download URL generated for s3://{bucket_name}/{object_key}. The URL will expire in {expiration} seconds.",
            'data': {
                'download_url': url,
                'expiration': expiration
            },
            'cli_command': f"aws s3 presign s3://{bucket_name}/{object_key} --expires-in {expiration}"
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            return {
                'success': False,
                'message': f"Bucket '{bucket_name}' does not exist."
            }
        elif e.response['Error']['Code'] == '404':
            return {
                'success': False,
                'message': f"Object '{object_key}' does not exist in bucket '{bucket_name}'."
            }
        else:
            return {
                'success': False,
                'message': f"Error generating download URL: {str(e)}"
            }
    except Exception as e:
        return {
            'success': False,
            'message': f"Error generating download URL: {str(e)}"
        }

def delete_object(parameters):
    """Delete an object from S3"""
    bucket_name = parameters.get('bucket_name')
    object_key = parameters.get('object_key')
    
    if not bucket_name or not object_key:
        return {
            'success': False,
            'message': "Bucket name and object key are required."
        }
    
    try:
        # Check if bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
        
        # Delete the object
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)
        
        return {
            'success': True,
            'message': f"Successfully deleted object s3://{bucket_name}/{object_key}",
            'cli_command': f"aws s3 rm s3://{bucket_name}/{object_key}"
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            return {
                'success': False,
                'message': f"Bucket '{bucket_name}' does not exist."
            }
        else:
            return {
                'success': False,
                'message': f"Error deleting object: {str(e)}"
            }
    except Exception as e:
        return {
            'success': False,
            'message': f"Error deleting object: {str(e)}"
        }

def copy_object(parameters):
    """Copy an object within S3"""
    source_bucket = parameters.get('source_bucket')
    source_key = parameters.get('source_key')
    dest_bucket = parameters.get('dest_bucket')
    dest_key = parameters.get('dest_key')
    
    if not source_bucket or not source_key or not dest_bucket or not dest_key:
        return {
            'success': False,
            'message': "Source bucket, source key, destination bucket, and destination key are all required."
        }
    
    try:
        # Check if source bucket and object exist
        s3_client.head_object(Bucket=source_bucket, Key=source_key)
        
        # Check if destination bucket exists
        s3_client.head_bucket(Bucket=dest_bucket)
        
        # Copy the object
        copy_source = {'Bucket': source_bucket, 'Key': source_key}
        s3_client.copy_object(CopySource=copy_source, Bucket=dest_bucket, Key=dest_key)
        
        return {
            'success': True,
            'message': f"Successfully copied s3://{source_bucket}/{source_key} to s3://{dest_bucket}/{dest_key}",
            'cli_command': f"aws s3 cp s3://{source_bucket}/{source_key} s3://{dest_bucket}/{dest_key}"
        }
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            return {
                'success': False,
                'message': f"One of the buckets does not exist."
            }
        elif error_code == '404':
            return {
                'success': False,
                'message': f"Object '{source_key}' does not exist in bucket '{source_bucket}'."
            }
        else:
            return {
                'success': False,
                'message': f"Error copying object: {str(e)}"
            }
    except Exception as e:
        return {
            'success': False,
            'message': f"Error copying object: {str(e)}"
        }

def list_all_files(parameters):
    """List all files across multiple buckets"""
    bucket_names = parameters.get('bucket_names', [])
    
    if not bucket_names:
        # If no buckets specified, list all buckets first
        buckets_result = list_buckets()
        if not buckets_result['success']:
            return buckets_result
        
        bucket_names = buckets_result['data']
    
    # Handle case where bucket_names is a comma-separated string
    if isinstance(bucket_names, str):
        bucket_names = [name.strip() for name in bucket_names.split(',')]
    
    all_files = {}
    success = True
    error_messages = []
    
    for bucket_name in bucket_names:
        result = list_objects({'bucket_name': bucket_name})
        
        if result['success']:
            all_files[bucket_name] = result.get('data', [])
        else:
            success = False
            error_messages.append(f"Error for bucket '{bucket_name}': {result['message']}")
    
    if not success:
        return {
            'success': False,
            'message': "Errors occurred while listing files:\n" + "\n".join(error_messages)
        }
    
    # Format the response message
    message = "Files across all buckets:\n"
    total_files = 0
    
    for bucket, files in all_files.items():
        message += f"\nBucket: {bucket} ({len(files)} files)\n"
        
        # Limit the number of files shown per bucket
        max_display = 10
        displayed_files = files[:max_display]
        
        for file in displayed_files:
            message += f"- {file}\n"
        
        if len(files) > max_display:
            message += f"... and {len(files) - max_display} more\n"
        
        total_files += len(files)
    
    message = f"Found {total_files} total files across {len(bucket_names)} bucket(s).\n" + message
    
    return {
        'success': True,
        'message': message,
        'data': all_files
    }