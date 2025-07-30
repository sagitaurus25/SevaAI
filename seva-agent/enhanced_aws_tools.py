"""
Enhanced AWS Service Tools for SevaAI Agent
Comprehensive coverage of AWS services including S3, EC2, Lambda, IAM, RDS, CloudWatch, VPC, and more
"""
import boto3
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class EnhancedAWSTools:
    """Enhanced tools for interacting with AWS services"""
    
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
    
    # ==================== S3 OPERATIONS ====================
    
    def list_s3_buckets(self) -> str:
        """List all S3 buckets in the account"""
        try:
            s3 = self.session.client('s3')
            response = s3.list_buckets()
            buckets = [bucket['Name'] for bucket in response['Buckets']]
            return json.dumps({"buckets": buckets})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def create_s3_bucket(self, bucket_name: str, region: str = None) -> str:
        """Create a new S3 bucket"""
        try:
            s3 = self.session.client('s3')
            if region and region != 'us-east-1':
                s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )
            else:
                s3.create_bucket(Bucket=bucket_name)
            return json.dumps({"success": f"Bucket {bucket_name} created successfully"})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def delete_s3_bucket(self, bucket_name: str) -> str:
        """Delete an S3 bucket (must be empty)"""
        try:
            s3 = self.session.client('s3')
            s3.delete_bucket(Bucket=bucket_name)
            return json.dumps({"success": f"Bucket {bucket_name} deleted successfully"})
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
    
    # ==================== EC2 OPERATIONS ====================
    
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
                        "public_ip": instance.get('PublicIpAddress', 'None'),
                        "private_ip": instance.get('PrivateIpAddress', 'None'),
                        "launch_time": instance['LaunchTime'].isoformat()
                    })
            
            return json.dumps({"instances": instances})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def start_ec2_instance(self, instance_id: str) -> str:
        """Start an EC2 instance"""
        try:
            ec2 = self.session.client('ec2')
            response = ec2.start_instances(InstanceIds=[instance_id])
            return json.dumps({"success": f"Instance {instance_id} start initiated"})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def stop_ec2_instance(self, instance_id: str) -> str:
        """Stop an EC2 instance"""
        try:
            ec2 = self.session.client('ec2')
            response = ec2.stop_instances(InstanceIds=[instance_id])
            return json.dumps({"success": f"Instance {instance_id} stop initiated"})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def list_security_groups(self) -> str:
        """List EC2 security groups"""
        try:
            ec2 = self.session.client('ec2')
            response = ec2.describe_security_groups()
            
            groups = [
                {
                    "id": sg['GroupId'],
                    "name": sg['GroupName'],
                    "description": sg['Description'],
                    "vpc_id": sg.get('VpcId', 'N/A')
                }
                for sg in response['SecurityGroups']
            ]
            
            return json.dumps({"security_groups": groups})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    # ==================== LAMBDA OPERATIONS ====================
    
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
                    "timeout": function['Timeout'],
                    "last_modified": function['LastModified']
                }
                for function in response['Functions']
            ]
            
            return json.dumps({"functions": functions})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def invoke_lambda_function(self, function_name: str, payload: dict = None) -> str:
        """Invoke a Lambda function"""
        try:
            lambda_client = self.session.client('lambda')
            response = lambda_client.invoke(
                FunctionName=function_name,
                Payload=json.dumps(payload or {})
            )
            
            result = json.loads(response['Payload'].read().decode('utf-8'))
            return json.dumps({"result": result})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def get_lambda_logs(self, function_name: str, hours: int = 1) -> str:
        """Get recent Lambda function logs"""
        try:
            logs_client = self.session.client('logs')
            log_group_name = f"/aws/lambda/{function_name}"
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            response = logs_client.filter_log_events(
                logGroupName=log_group_name,
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000)
            )
            
            events = [
                {
                    "timestamp": event['timestamp'],
                    "message": event['message']
                }
                for event in response['events']
            ]
            
            return json.dumps({"log_events": events})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    # ==================== IAM OPERATIONS ====================
    
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
    
    def list_iam_roles(self) -> str:
        """List IAM roles in the account"""
        try:
            iam = self.session.client('iam')
            response = iam.list_roles()
            
            roles = [
                {
                    "name": role['RoleName'],
                    "arn": role['Arn'],
                    "created": role['CreateDate'].isoformat(),
                    "description": role.get('Description', 'N/A')
                }
                for role in response['Roles']
            ]
            
            return json.dumps({"roles": roles})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def list_iam_policies(self, scope: str = "Local") -> str:
        """List IAM policies (Local or AWS managed)"""
        try:
            iam = self.session.client('iam')
            response = iam.list_policies(Scope=scope)
            
            policies = [
                {
                    "name": policy['PolicyName'],
                    "arn": policy['Arn'],
                    "created": policy['CreateDate'].isoformat(),
                    "description": policy.get('Description', 'N/A')
                }
                for policy in response['Policies']
            ]
            
            return json.dumps({"policies": policies})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    # ==================== RDS OPERATIONS ====================
    
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
                    "size": instance['DBInstanceClass'],
                    "storage": instance.get('AllocatedStorage', 'N/A'),
                    "endpoint": instance.get('Endpoint', {}).get('Address', 'N/A')
                }
                for instance in response['DBInstances']
            ]
            
            return json.dumps({"db_instances": instances})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def list_rds_snapshots(self) -> str:
        """List RDS snapshots"""
        try:
            rds = self.session.client('rds')
            response = rds.describe_db_snapshots(SnapshotType='manual')
            
            snapshots = [
                {
                    "identifier": snapshot['DBSnapshotIdentifier'],
                    "db_instance": snapshot['DBInstanceIdentifier'],
                    "status": snapshot['Status'],
                    "created": snapshot['SnapshotCreateTime'].isoformat()
                }
                for snapshot in response['DBSnapshots']
            ]
            
            return json.dumps({"snapshots": snapshots})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    # ==================== CLOUDWATCH OPERATIONS ====================
    
    def list_cloudwatch_alarms(self) -> str:
        """List CloudWatch alarms"""
        try:
            cloudwatch = self.session.client('cloudwatch')
            response = cloudwatch.describe_alarms()
            
            alarms = [
                {
                    "name": alarm['AlarmName'],
                    "state": alarm['StateValue'],
                    "reason": alarm['StateReason'],
                    "metric": alarm['MetricName'],
                    "namespace": alarm['Namespace']
                }
                for alarm in response['MetricAlarms']
            ]
            
            return json.dumps({"alarms": alarms})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def get_cloudwatch_metrics(self, namespace: str, metric_name: str, hours: int = 24) -> str:
        """Get CloudWatch metrics for a specific metric"""
        try:
            cloudwatch = self.session.client('cloudwatch')
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            response = cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour periods
                Statistics=['Average', 'Maximum', 'Minimum']
            )
            
            datapoints = [
                {
                    "timestamp": dp['Timestamp'].isoformat(),
                    "average": dp.get('Average', 0),
                    "maximum": dp.get('Maximum', 0),
                    "minimum": dp.get('Minimum', 0)
                }
                for dp in response['Datapoints']
            ]
            
            return json.dumps({"datapoints": datapoints})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    # ==================== VPC OPERATIONS ====================
    
    def list_vpcs(self) -> str:
        """List VPCs in the account"""
        try:
            ec2 = self.session.client('ec2')
            response = ec2.describe_vpcs()
            
            vpcs = [
                {
                    "id": vpc['VpcId'],
                    "cidr": vpc['CidrBlock'],
                    "state": vpc['State'],
                    "is_default": vpc['IsDefault']
                }
                for vpc in response['Vpcs']
            ]
            
            return json.dumps({"vpcs": vpcs})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def list_subnets(self, vpc_id: str = None) -> str:
        """List subnets, optionally filtered by VPC"""
        try:
            ec2 = self.session.client('ec2')
            
            if vpc_id:
                response = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
            else:
                response = ec2.describe_subnets()
            
            subnets = [
                {
                    "id": subnet['SubnetId'],
                    "vpc_id": subnet['VpcId'],
                    "cidr": subnet['CidrBlock'],
                    "availability_zone": subnet['AvailabilityZone'],
                    "available_ips": subnet['AvailableIpAddressCount']
                }
                for subnet in response['Subnets']
            ]
            
            return json.dumps({"subnets": subnets})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    # ==================== COST AND BILLING ====================
    
    def get_cost_and_usage(self, days: int = 30) -> str:
        """Get cost and usage data for the last N days"""
        try:
            ce = self.session.client('ce')
            
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            costs = []
            for result in response['ResultsByTime']:
                date = result['TimePeriod']['Start']
                for group in result['Groups']:
                    service = group['Keys'][0]
                    amount = float(group['Metrics']['BlendedCost']['Amount'])
                    if amount > 0:
                        costs.append({
                            "date": date,
                            "service": service,
                            "cost": amount
                        })
            
            return json.dumps({"cost_data": costs})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    # ==================== ROUTE 53 OPERATIONS ====================
    
    def list_hosted_zones(self) -> str:
        """List Route 53 hosted zones"""
        try:
            route53 = self.session.client('route53')
            response = route53.list_hosted_zones()
            
            zones = [
                {
                    "id": zone['Id'].split('/')[-1],
                    "name": zone['Name'],
                    "record_count": zone['ResourceRecordSetCount']
                }
                for zone in response['HostedZones']
            ]
            
            return json.dumps({"hosted_zones": zones})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    # ==================== CLOUDFORMATION OPERATIONS ====================
    
    def list_cloudformation_stacks(self) -> str:
        """List CloudFormation stacks"""
        try:
            cf = self.session.client('cloudformation')
            response = cf.describe_stacks()
            
            stacks = [
                {
                    "name": stack['StackName'],
                    "status": stack['StackStatus'],
                    "created": stack['CreationTime'].isoformat(),
                    "description": stack.get('Description', 'N/A')
                }
                for stack in response['Stacks']
            ]
            
            return json.dumps({"stacks": stacks})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    # ==================== UTILITY METHODS ====================
    
    def get_account_info(self) -> str:
        """Get AWS account information"""
        try:
            sts = self.session.client('sts')
            response = sts.get_caller_identity()
            
            return json.dumps({
                "account_id": response['Account'],
                "user_id": response['UserId'],
                "arn": response['Arn']
            })
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def list_regions(self) -> str:
        """List available AWS regions"""
        try:
            ec2 = self.session.client('ec2')
            response = ec2.describe_regions()
            
            regions = [region['RegionName'] for region in response['Regions']]
            return json.dumps({"regions": regions})
        except Exception as e:
            return json.dumps({"error": str(e)})