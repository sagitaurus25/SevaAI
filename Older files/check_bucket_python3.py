#!/usr/bin/env python3

import boto3
import sys

def check_bucket_exists(bucket_name):
    """Check if a bucket exists and is accessible"""
    
    print(f"Checking if bucket '{bucket_name}' exists and is accessible...")
    
    try:
        # Create S3 client
        s3 = boto3.client('s3')
        
        # Try to head the bucket (check if it exists)
        try:
            s3.head_bucket(Bucket=bucket_name)
            print(f"✅ Bucket '{bucket_name}' exists and is accessible")
            
            # Try to list objects
            try:
                response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
                if 'Contents' in response:
                    print(f"✅ Successfully listed objects in bucket '{bucket_name}'")
                else:
                    print(f"✅ Bucket '{bucket_name}' is empty")
                return True
            except Exception as e:
                print(f"❌ Error listing objects in bucket '{bucket_name}': {str(e)}")
                return False
                
        except s3.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"❌ Bucket '{bucket_name}' does not exist")
            elif error_code == '403':
                print(f"❌ Access denied to bucket '{bucket_name}' (bucket exists but you don't have permission)")
            else:
                print(f"❌ Error checking bucket '{bucket_name}': {error_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        bucket_name = sys.argv[1]
        check_bucket_exists(bucket_name)
    else:
        print("Please provide a bucket name as an argument")
        print("Example: python3 check_bucket_python3.py my-bucket-name")