#!/usr/bin/env python3

import boto3
import zipfile
import io
import re
from datetime import datetime

def deploy_organize_images_lambda():
    """Deploy a Lambda function to organize images by date"""
    
    # Lambda function name
    FUNCTION_NAME = 'S3ImageOrganizer'
    
    print(f"Deploying image organizer Lambda function: {FUNCTION_NAME}")
    
    # Create a zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the Lambda function code
        lambda_code = '''
import json
import boto3
import os
from datetime import datetime
import re

# Initialize S3 client
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    Lambda function to organize images in an S3 bucket by date
    1. Scan the S3 bucket for image files
    2. Extract creation dates from metadata
    3. Create a year/month folder structure
    4. Move files to the appropriate folders
    """
    try:
        # Get bucket name from event or use default
        bucket_name = event.get('bucket')
        if not bucket_name:
            return {
                'statusCode': 400,
                'body': json.dumps('Please provide a bucket name in the event')
            }
        
        # Check if bucket exists
        try:
            s3.head_bucket(Bucket=bucket_name)
        except Exception as e:
            return {
                'statusCode': 404,
                'body': json.dumps(f'Bucket {bucket_name} not found: {str(e)}')
            }
        
        # Get all objects in the bucket
        response = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' not in response:
            return {
                'statusCode': 200,
                'body': json.dumps(f'No objects found in bucket {bucket_name}')
            }
        
        # Track statistics
        stats = {
            'total_files': 0,
            'image_files': 0,
            'organized_files': 0,
            'skipped_files': 0,
            'errors': 0
        }
        
        # Process each object
        for obj in response['Contents']:
            key = obj['Key']
            stats['total_files'] += 1
            
            # Skip if already in a year/month folder structure
            if re.match(r'^[0-9]{4}/[0-9]{2}/', key):
                stats['skipped_files'] += 1
                continue
            
            # Check if it's an image file
            if not is_image_file(key):
                continue
                
            stats['image_files'] += 1
            
            try:
                # Get object metadata
                metadata = s3.head_object(Bucket=bucket_name, Key=key)
                
                # Extract date from metadata or filename or last modified
                date = extract_date(metadata, key)
                
                if date:
                    # Create new key with year/month structure
                    year_month = date.strftime('%Y/%m')
                    filename = os.path.basename(key)
                    new_key = f"{year_month}/{filename}"
                    
                    # Copy object to new location
                    s3.copy_object(
                        CopySource={'Bucket': bucket_name, 'Key': key},
                        Bucket=bucket_name,
                        Key=new_key
                    )
                    
                    # Delete original object
                    s3.delete_object(Bucket=bucket_name, Key=key)
                    
                    stats['organized_files'] += 1
                else:
                    stats['skipped_files'] += 1
            except Exception as e:
                print(f"Error processing {key}: {str(e)}")
                stats['errors'] += 1
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Image organization complete for bucket {bucket_name}',
                'stats': stats
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def is_image_file(key):
    """Check if the file is an image based on extension"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic']
    return any(key.lower().endswith(ext) for ext in image_extensions)

def extract_date(metadata, key):
    """Extract date from metadata, filename, or last modified date"""
    # Try to get date from metadata
    if 'Metadata' in metadata:
        # Check for EXIF date in metadata
        if 'exif-datetimeoriginal' in metadata['Metadata']:
            try:
                date_str = metadata['Metadata']['exif-datetimeoriginal']
                return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            except:
                pass
    
    # Try to extract date from filename (common patterns like IMG_20210315_123045.jpg)
    date_patterns = [
        r'([0-9]{4})[-_]?([0-9]{2})[-_]?([0-9]{2})',  # YYYY-MM-DD or YYYYMMDD
        r'([0-9]{2})[-_]?([0-9]{2})[-_]?([0-9]{4})'   # DD-MM-YYYY or DDMMYYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, key)
        if match:
            try:
                if len(match.group(1)) == 4:  # YYYY-MM-DD
                    year, month, day = match.group(1), match.group(2), match.group(3)
                else:  # DD-MM-YYYY
                    day, month, year = match.group(1), match.group(2), match.group(3)
                
                return datetime(int(year), int(month), 1)  # Just need year/month
            except:
                pass
    
    # Fall back to last modified date
    return datetime.fromtimestamp(metadata['LastModified'].timestamp())
'''
        
        # Write the Lambda function to a file
        zip_file.writestr('lambda_function.py', lambda_code)
    
    # Get the zip file content
    zip_buffer.seek(0)
    zip_content = zip_buffer.read()
    
    # Create or update the Lambda function
    try:
        lambda_client = boto3.client('lambda')
        
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=FUNCTION_NAME)
            
            # Update existing function
            response = lambda_client.update_function_code(
                FunctionName=FUNCTION_NAME,
                ZipFile=zip_content,
                Publish=True
            )
            print(f"✅ Lambda function updated: {FUNCTION_NAME}")
            
        except lambda_client.exceptions.ResourceNotFoundException:
            # Create new function
            response = lambda_client.create_function(
                FunctionName=FUNCTION_NAME,
                Runtime='python3.9',
                Role='arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-s3-full-access',  # Replace with your role ARN
                Handler='lambda_function.lambda_handler',
                Code={
                    'ZipFile': zip_content
                },
                Timeout=300,  # 5 minutes
                MemorySize=256,
                Publish=True,
                Description='Organizes images in S3 buckets by date'
            )
            print(f"✅ Lambda function created: {FUNCTION_NAME}")
        
        print(f"Version: {response.get('Version')}")
        
        # Create test event file
        test_event = {
            "bucket": "YOUR_BUCKET_NAME"  # Replace with your bucket name
        }
        
        with open('test_event.json', 'w') as f:
            json.dump(test_event, f, indent=2)
        
        print(f"✅ Test event created: test_event.json")
        print("To test the function, update the bucket name in test_event.json and run:")
        print(f"aws lambda invoke --function-name {FUNCTION_NAME} --payload file://test_event.json output.json")
        
        return True
        
    except Exception as e:
        print(f"❌ Error deploying Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    deploy_organize_images_lambda()