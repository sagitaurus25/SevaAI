import boto3
import os

# Print environment
print("Environment variables:")
for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION', 'AWS_PROFILE']:
    print(f"{key}: {os.environ.get(key, 'Not set')}")

# Test boto3
try:
    session = boto3.Session()
    creds = session.get_credentials()
    print(f"\nCredentials found: {creds is not None}")
    if creds:
        print(f"Access key: {creds.access_key[:10]}...")
    
    sts = session.client('sts')
    identity = sts.get_caller_identity()
    print(f"Success! Account: {identity['Account']}")
    
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")