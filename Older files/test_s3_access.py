import boto3
import sys

def test_s3_access():
    """Test if your AWS credentials have S3 access"""
    print("Testing S3 access with your local AWS credentials...")
    
    try:
        # Create S3 client
        s3 = boto3.client('s3')
        
        # Test listing buckets
        print("Trying to list S3 buckets...")
        response = s3.list_buckets()
        buckets = [b['Name'] for b in response.get('Buckets', [])]
        print(f"✅ Success! Found {len(buckets)} buckets:")
        for bucket in buckets:
            print(f"  - {bucket}")
            
        # If we have buckets, try to list objects in the first one
        if buckets:
            bucket_name = buckets[0]
            print(f"\nTrying to list objects in bucket '{bucket_name}'...")
            try:
                response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
                objects = [obj['Key'] for obj in response.get('Contents', [])]
                if objects:
                    print(f"✅ Success! Found {len(objects)} objects (showing up to 5):")
                    for obj in objects[:5]:
                        print(f"  - {obj}")
                else:
                    print(f"✅ Success! Bucket '{bucket_name}' is empty.")
            except Exception as e:
                print(f"❌ Error listing objects in bucket '{bucket_name}': {str(e)}")
        
        print("\n✅ Your AWS credentials have S3 access!")
        print("If your Lambda function is still getting Access Denied errors, the issue is with the Lambda's role permissions, not your credentials.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nYour local AWS credentials don't have S3 access.")
        print("Please check your AWS credentials configuration:")
        print("1. Make sure you have AWS CLI installed")
        print("2. Run 'aws configure' to set up your credentials")
        print("3. Make sure your IAM user/role has S3 permissions")
        
        return False
    
    return True

if __name__ == "__main__":
    test_s3_access()