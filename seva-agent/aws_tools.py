"""
AWS Service Tools for the Data Analyst Agent
"""
import boto3
import json
from typing import Dict, List, Any, Optional

class AWSTools:
    """Tools for interacting with AWS services"""
    
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, region_name=None):
        """Initialize with AWS credentials"""
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name or "us-east-1"
        
        # Session for creating service clients
        self.session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=self.region_name
        )
    
    def list_s3_buckets(self) -> str:
        """List all S3 buckets in the account"""
        try:
            s3 = self.session.client('s3')
            response = s3.list_buckets()
            buckets = [bucket['Name'] for bucket in response['Buckets']]
            return json.dumps({"buckets": buckets})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def list_s3_objects(self, bucket_name: str, prefix: str = "") -> str:
        """List objects in an S3 bucket with optional prefix"""
        try:
            s3 = self.session.client('s3')
            response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            
            if 'Contents' in response:
                objects = [
                    {
                        "key": obj['Key'],
                        "size": obj['Size'],
                        "last_modified": obj['LastModified'].isoformat()
                    }
                    for obj in response['Contents']
                ]
                return json.dumps({"objects": objects})
            else:
                return json.dumps({"objects": []})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def list_ec2_instances(self) -> str:
        """List EC2 instances in the account"""
        try:
            ec2 = self.session.client('ec2')
            response = ec2.describe_instances()
            
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    name = "Unnamed"
                    if 'Tags' in instance:
                        for tag in instance['Tags']:
                            if tag['Key'] == 'Name':
                                name = tag['Value']
                    
                    instances.append({
                        "id": instance['InstanceId'],
                        "name": name,
                        "type": instance['InstanceType'],
                        "state": instance['State']['Name'],
                        "public_ip": instance.get('PublicIpAddress', 'None')
                    })
            
            return json.dumps({"instances": instances})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def list_lambda_functions(self) -> str:
        """List Lambda functions in the account"""
        try:
            lambda_client = self.session.client('lambda')
            response = lambda_client.list_functions()
            
            functions = [
                {
                    "name": function['FunctionName'],
                    "runtime": function['Runtime'],
                    "memory": function['MemorySize'],
                    "timeout": function['Timeout']
                }
                for function in response['Functions']
            ]
            
            return json.dumps({"functions": functions})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def list_iam_users(self) -> str:
        """List IAM users in the account"""
        try:
            iam = self.session.client('iam')
            response = iam.list_users()
            
            users = [
                {
                    "name": user['UserName'],
                    "id": user['UserId'],
                    "arn": user['Arn'],
                    "created": user['CreateDate'].isoformat()
                }
                for user in response['Users']
            ]
            
            return json.dumps({"users": users})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def describe_rds_instances(self) -> str:
        """Describe RDS database instances"""
        try:
            rds = self.session.client('rds')
            response = rds.describe_db_instances()
            
            instances = [
                {
                    "identifier": instance['DBInstanceIdentifier'],
                    "engine": instance['Engine'],
                    "status": instance['DBInstanceStatus'],
                    "size": instance['DBInstanceClass']
                }
                for instance in response['DBInstances']
            ]
            
            return json.dumps({"db_instances": instances})
        except Exception as e:
            return json.dumps({"error": str(e)})