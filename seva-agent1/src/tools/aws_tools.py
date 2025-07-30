import boto3
import subprocess
import json
from typing import Dict, Any, List

class AWSTools:
    def __init__(self):
        # Core services
        self.s3_client = boto3.client('s3')
        self.ec2_client = boto3.client('ec2')
        self.lambda_client = boto3.client('lambda')
        self.iam_client = boto3.client('iam')
        self.cloudwatch_client = boto3.client('cloudwatch')
        
        # Additional services
        self.rds_client = boto3.client('rds')
        self.dynamodb_client = boto3.client('dynamodb')
        self.cloudformation_client = boto3.client('cloudformation')
        self.route53_client = boto3.client('route53')
        self.sns_client = boto3.client('sns')
        self.sqs_client = boto3.client('sqs')
        self.ecs_client = boto3.client('ecs')
        self.eks_client = boto3.client('eks')
        self.apigateway_client = boto3.client('apigateway')
        self.secretsmanager_client = boto3.client('secretsmanager')
        self.ssm_client = boto3.client('ssm')
        self.elasticache_client = boto3.client('elasticache')
        self.elbv2_client = boto3.client('elbv2')
        self.autoscaling_client = boto3.client('autoscaling')
        self.cloudtrail_client = boto3.client('cloudtrail')
        self.organizations_client = boto3.client('organizations')
        self.cost_client = boto3.client('ce')
    
    def generate_s3_command(self, operation: str, bucket: str = None, key: str = None, **kwargs) -> str:
        """Generate AWS CLI commands for S3 operations"""
        if operation == "list_buckets":
            return "aws s3 ls"
        elif operation == "list_objects" and bucket:
            recursive = "--recursive" if kwargs.get('recursive') else ""
            return f"aws s3 ls s3://{bucket}/ {recursive}".strip()
        elif operation == "create_bucket" and bucket:
            region = kwargs.get('region', 'us-east-1')
            return f"aws s3 mb s3://{bucket} --region {region}"
        elif operation == "upload_file" and bucket and key:
            local_file = kwargs.get('local_file', key)
            return f"aws s3 cp {local_file} s3://{bucket}/{key}"
        elif operation == "download_file" and bucket and key:
            local_file = kwargs.get('local_file', key)
            return f"aws s3 cp s3://{bucket}/{key} {local_file}"
        else:
            return f"# Unsupported S3 operation: {operation}"
    
    def generate_ec2_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for EC2 operations"""
        region = kwargs.get('region', 'us-east-1')
        
        if operation == "list_instances":
            state_filter = f"--filters Name=instance-state-name,Values={kwargs['state']}" if kwargs.get('state') else ""
            return f"aws ec2 describe-instances --region {region} {state_filter} --query 'Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,PublicIpAddress]' --output table".strip()
        elif operation == "start_instance":
            instance_id = kwargs.get('instance_id')
            return f"aws ec2 start-instances --region {region} --instance-ids {instance_id}"
        elif operation == "stop_instance":
            instance_id = kwargs.get('instance_id')
            return f"aws ec2 stop-instances --region {region} --instance-ids {instance_id}"
        elif operation == "create_security_group":
            group_name = kwargs.get('group_name')
            description = kwargs.get('description', 'Created by SevaAI')
            return f"aws ec2 create-security-group --region {region} --group-name {group_name} --description '{description}'"
        else:
            return f"# Unsupported EC2 operation: {operation}"
    
    def generate_lambda_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for Lambda operations"""
        region = kwargs.get('region', 'us-east-1')
        
        if operation == "list_functions":
            runtime_filter = f"--query 'Functions[?starts_with(Runtime, `{kwargs['runtime']}`)]'" if kwargs.get('runtime') else ""
            return f"aws lambda list-functions --region {region} {runtime_filter} --query 'Functions[*].[FunctionName,Runtime,LastModified]' --output table".strip()
        elif operation == "invoke_function":
            function_name = kwargs.get('function_name')
            payload = kwargs.get('payload', '{}')
            return f"aws lambda invoke --region {region} --function-name {function_name} --payload '{payload}' response.json"
        elif operation == "update_function_code":
            function_name = kwargs.get('function_name')
            zip_file = kwargs.get('zip_file')
            return f"aws lambda update-function-code --region {region} --function-name {function_name} --zip-file fileb://{zip_file}"
        else:
            return f"# Unsupported Lambda operation: {operation}"
    
    def generate_iam_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for IAM operations"""
        if operation == "list_users":
            return "aws iam list-users --query 'Users[*].[UserName,CreateDate,Arn]' --output table"
        elif operation == "list_roles":
            return "aws iam list-roles --query 'Roles[*].[RoleName,CreateDate,Arn]' --output table"
        elif operation == "create_user":
            username = kwargs.get('username')
            return f"aws iam create-user --user-name {username}"
        elif operation == "attach_policy":
            username = kwargs.get('username')
            policy_arn = kwargs.get('policy_arn')
            return f"aws iam attach-user-policy --user-name {username} --policy-arn {policy_arn}"
        elif operation == "create_access_key":
            username = kwargs.get('username')
            return f"aws iam create-access-key --user-name {username}"
        else:
            return f"# Unsupported IAM operation: {operation}"
    
    def generate_rds_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for RDS operations"""
        region = kwargs.get('region', 'us-east-1')
        
        if operation == "list_instances":
            return f"aws rds describe-db-instances --region {region} --query 'DBInstances[*].[DBInstanceIdentifier,DBInstanceStatus,Engine,DBInstanceClass]' --output table"
        elif operation == "create_instance":
            db_name = kwargs.get('db_name')
            engine = kwargs.get('engine', 'mysql')
            instance_class = kwargs.get('instance_class', 'db.t3.micro')
            username = kwargs.get('username', 'admin')
            password = kwargs.get('password', 'changeme123')
            return f"aws rds create-db-instance --region {region} --db-instance-identifier {db_name} --db-instance-class {instance_class} --engine {engine} --master-username {username} --master-user-password {password} --allocated-storage 20"
        elif operation == "delete_instance":
            db_name = kwargs.get('db_name')
            skip_snapshot = "--skip-final-snapshot" if kwargs.get('skip_snapshot') else ""
            return f"aws rds delete-db-instance --region {region} --db-instance-identifier {db_name} {skip_snapshot}".strip()
        else:
            return f"# Unsupported RDS operation: {operation}"
    
    def generate_dynamodb_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for DynamoDB operations"""
        region = kwargs.get('region', 'us-east-1')
        
        if operation == "list_tables":
            return f"aws dynamodb list-tables --region {region}"
        elif operation == "create_table":
            table_name = kwargs.get('table_name')
            key_name = kwargs.get('key_name', 'id')
            key_type = kwargs.get('key_type', 'S')
            return f"aws dynamodb create-table --region {region} --table-name {table_name} --attribute-definitions AttributeName={key_name},AttributeType={key_type} --key-schema AttributeName={key_name},KeyType=HASH --billing-mode PAY_PER_REQUEST"
        elif operation == "delete_table":
            table_name = kwargs.get('table_name')
            return f"aws dynamodb delete-table --region {region} --table-name {table_name}"
        elif operation == "scan_table":
            table_name = kwargs.get('table_name')
            limit = f"--max-items {kwargs['limit']}" if kwargs.get('limit') else ""
            return f"aws dynamodb scan --region {region} --table-name {table_name} {limit}".strip()
        else:
            return f"# Unsupported DynamoDB operation: {operation}"
    
    def generate_cloudformation_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for CloudFormation operations"""
        region = kwargs.get('region', 'us-east-1')
        
        if operation == "list_stacks":
            return f"aws cloudformation list-stacks --region {region} --query 'StackSummaries[?StackStatus!=`DELETE_COMPLETE`].[StackName,StackStatus,CreationTime]' --output table"
        elif operation == "create_stack":
            stack_name = kwargs.get('stack_name')
            template_file = kwargs.get('template_file')
            return f"aws cloudformation create-stack --region {region} --stack-name {stack_name} --template-body file://{template_file}"
        elif operation == "delete_stack":
            stack_name = kwargs.get('stack_name')
            return f"aws cloudformation delete-stack --region {region} --stack-name {stack_name}"
        elif operation == "describe_stack":
            stack_name = kwargs.get('stack_name')
            return f"aws cloudformation describe-stacks --region {region} --stack-name {stack_name}"
        else:
            return f"# Unsupported CloudFormation operation: {operation}"
    
    def generate_vpc_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for VPC operations"""
        region = kwargs.get('region', 'us-east-1')
        
        if operation == "list_vpcs":
            return f"aws ec2 describe-vpcs --region {region} --query 'Vpcs[*].[VpcId,CidrBlock,State,IsDefault]' --output table"
        elif operation == "create_vpc":
            cidr_block = kwargs.get('cidr_block', '10.0.0.0/16')
            return f"aws ec2 create-vpc --region {region} --cidr-block {cidr_block}"
        elif operation == "list_subnets":
            vpc_id = kwargs.get('vpc_id')
            vpc_filter = f"--filters Name=vpc-id,Values={vpc_id}" if vpc_id else ""
            return f"aws ec2 describe-subnets --region {region} {vpc_filter} --query 'Subnets[*].[SubnetId,VpcId,CidrBlock,AvailabilityZone]' --output table".strip()
        elif operation == "create_subnet":
            vpc_id = kwargs.get('vpc_id')
            cidr_block = kwargs.get('cidr_block', '10.0.1.0/24')
            az = kwargs.get('availability_zone')
            az_param = f"--availability-zone {az}" if az else ""
            return f"aws ec2 create-subnet --region {region} --vpc-id {vpc_id} --cidr-block {cidr_block} {az_param}".strip()
        else:
            return f"# Unsupported VPC operation: {operation}"
    
    def generate_route53_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for Route53 operations"""
        if operation == "list_hosted_zones":
            return "aws route53 list-hosted-zones --query 'HostedZones[*].[Name,Id,ResourceRecordSetCount]' --output table"
        elif operation == "list_records":
            hosted_zone_id = kwargs.get('hosted_zone_id')
            return f"aws route53 list-resource-record-sets --hosted-zone-id {hosted_zone_id} --query 'ResourceRecordSets[*].[Name,Type,TTL]' --output table"
        elif operation == "create_record":
            hosted_zone_id = kwargs.get('hosted_zone_id')
            record_name = kwargs.get('record_name')
            record_type = kwargs.get('record_type', 'A')
            record_value = kwargs.get('record_value')
            ttl = kwargs.get('ttl', 300)
            change_batch = f'{{"Changes":[{{"Action":"CREATE","ResourceRecordSet":{{"Name":"{record_name}","Type":"{record_type}","TTL":{ttl},"ResourceRecords":[{{"Value":"{record_value}"}}]}}}}]}}'
            return f"aws route53 change-resource-record-sets --hosted-zone-id {hosted_zone_id} --change-batch '{change_batch}'"
        else:
            return f"# Unsupported Route53 operation: {operation}"
    
    def generate_sns_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for SNS operations"""
        region = kwargs.get('region', 'us-east-1')
        
        if operation == "list_topics":
            return f"aws sns list-topics --region {region}"
        elif operation == "create_topic":
            topic_name = kwargs.get('topic_name')
            return f"aws sns create-topic --region {region} --name {topic_name}"
        elif operation == "publish_message":
            topic_arn = kwargs.get('topic_arn')
            message = kwargs.get('message')
            subject = kwargs.get('subject', 'SNS Message')
            return f"aws sns publish --region {region} --topic-arn {topic_arn} --message '{message}' --subject '{subject}'"
        elif operation == "subscribe":
            topic_arn = kwargs.get('topic_arn')
            protocol = kwargs.get('protocol', 'email')
            endpoint = kwargs.get('endpoint')
            return f"aws sns subscribe --region {region} --topic-arn {topic_arn} --protocol {protocol} --notification-endpoint {endpoint}"
        else:
            return f"# Unsupported SNS operation: {operation}"
    
    def generate_sqs_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for SQS operations"""
        region = kwargs.get('region', 'us-east-1')
        
        if operation == "list_queues":
            return f"aws sqs list-queues --region {region}"
        elif operation == "create_queue":
            queue_name = kwargs.get('queue_name')
            return f"aws sqs create-queue --region {region} --queue-name {queue_name}"
        elif operation == "send_message":
            queue_url = kwargs.get('queue_url')
            message = kwargs.get('message')
            return f"aws sqs send-message --region {region} --queue-url {queue_url} --message-body '{message}'"
        elif operation == "receive_messages":
            queue_url = kwargs.get('queue_url')
            max_messages = kwargs.get('max_messages', 10)
            return f"aws sqs receive-message --region {region} --queue-url {queue_url} --max-number-of-messages {max_messages}"
        else:
            return f"# Unsupported SQS operation: {operation}"
    
    def generate_cloudwatch_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for CloudWatch operations"""
        region = kwargs.get('region', 'us-east-1')
        
        if operation == "list_metrics":
            namespace = kwargs.get('namespace')
            namespace_filter = f"--namespace {namespace}" if namespace else ""
            return f"aws cloudwatch list-metrics --region {region} {namespace_filter}".strip()
        elif operation == "get_metric_statistics":
            namespace = kwargs.get('namespace')
            metric_name = kwargs.get('metric_name')
            start_time = kwargs.get('start_time')
            end_time = kwargs.get('end_time')
            period = kwargs.get('period', 300)
            statistics = kwargs.get('statistics', 'Average')
            return f"aws cloudwatch get-metric-statistics --region {region} --namespace {namespace} --metric-name {metric_name} --start-time {start_time} --end-time {end_time} --period {period} --statistics {statistics}"
        elif operation == "list_alarms":
            return f"aws cloudwatch describe-alarms --region {region} --query 'MetricAlarms[*].[AlarmName,StateValue,MetricName]' --output table"
        elif operation == "create_alarm":
            alarm_name = kwargs.get('alarm_name')
            metric_name = kwargs.get('metric_name')
            namespace = kwargs.get('namespace')
            threshold = kwargs.get('threshold')
            comparison = kwargs.get('comparison', 'GreaterThanThreshold')
            return f"aws cloudwatch put-metric-alarm --region {region} --alarm-name {alarm_name} --metric-name {metric_name} --namespace {namespace} --statistic Average --period 300 --threshold {threshold} --comparison-operator {comparison} --evaluation-periods 2"
        else:
            return f"# Unsupported CloudWatch operation: {operation}"
    
    def generate_cost_command(self, operation: str, **kwargs) -> str:
        """Generate AWS CLI commands for Cost Explorer operations"""
        if operation == "get_cost_and_usage":
            start_date = kwargs.get('start_date')
            end_date = kwargs.get('end_date')
            granularity = kwargs.get('granularity', 'MONTHLY')
            metrics = kwargs.get('metrics', 'BlendedCost')
            return f"aws ce get-cost-and-usage --time-period Start={start_date},End={end_date} --granularity {granularity} --metrics {metrics}"
        elif operation == "get_dimension_values":
            dimension = kwargs.get('dimension', 'SERVICE')
            start_date = kwargs.get('start_date')
            end_date = kwargs.get('end_date')
            return f"aws ce get-dimension-values --time-period Start={start_date},End={end_date} --dimension {dimension}"
        else:
            return f"# Unsupported Cost Explorer operation: {operation}"
    
    def get_service_commands(self, service: str) -> Dict[str, List[str]]:
        """Get available commands for a specific AWS service"""
        commands = {
            's3': ['list_buckets', 'list_objects', 'create_bucket', 'upload_file', 'download_file'],
            'ec2': ['list_instances', 'start_instance', 'stop_instance', 'create_security_group'],
            'lambda': ['list_functions', 'invoke_function', 'update_function_code'],
            'iam': ['list_users', 'list_roles', 'create_user', 'attach_policy', 'create_access_key'],
            'rds': ['list_instances', 'create_instance', 'delete_instance'],
            'dynamodb': ['list_tables', 'create_table', 'delete_table', 'scan_table'],
            'cloudformation': ['list_stacks', 'create_stack', 'delete_stack', 'describe_stack'],
            'vpc': ['list_vpcs', 'create_vpc', 'list_subnets', 'create_subnet'],
            'route53': ['list_hosted_zones', 'list_records', 'create_record'],
            'sns': ['list_topics', 'create_topic', 'publish_message', 'subscribe'],
            'sqs': ['list_queues', 'create_queue', 'send_message', 'receive_messages'],
            'cloudwatch': ['list_metrics', 'get_metric_statistics', 'list_alarms', 'create_alarm'],
            'cost': ['get_cost_and_usage', 'get_dimension_values']
        }
        return commands.get(service.lower(), [])
    
    def get_all_services(self) -> List[str]:
        """Get list of all supported AWS services"""
        return ['s3', 'ec2', 'lambda', 'iam', 'rds', 'dynamodb', 'cloudformation', 'vpc', 'route53', 'sns', 'sqs', 'cloudwatch', 'cost']

# Global instance
aws_tools = AWSTools()