import boto3

try:
    session = boto3.Session(region_name='us-east-1')
    sts = session.client('sts')
    identity = sts.get_caller_identity()
    print("✅ AWS credentials working!")
    print(f"Account: {identity['Account']}")
    print(f"User: {identity['Arn']}")
except Exception as e:
    print(f"❌ AWS credential error: {e}")
    print(f"Error type: {type(e)}")