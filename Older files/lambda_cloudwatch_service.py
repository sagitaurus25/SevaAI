import json
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any

cloudwatch_client = boto3.client('cloudwatch')
lambda_client = boto3.client('lambda')
s3_client = boto3.client('s3')
ec2_client = boto3.client('ec2')

def lambda_handler(event, context):
    """CloudWatch Metrics Service - Handles metrics queries for all AWS services"""
    try:
        request = event.get('request', '').lower()
        
        if 'lambda' in request and ('ran' in request or 'invocation' in request):
            return get_lambda_metrics()
        elif 's3' in request and ('request' in request or 'usage' in request):
            return get_s3_metrics()
        elif 'ec2' in request and ('cpu' in request or 'usage' in request):
            return get_ec2_metrics()
        elif 'alarm' in request:
            return get_cloudwatch_alarms()
        else:
            return {
                'error': 'CloudWatch operation not recognized',
                'supported_operations': [
                    'How many times my Lambda functions ran today',
                    'Show S3 request metrics',
                    'Show EC2 CPU usage',
                    'Show CloudWatch alarms'
                ]
            }
            
    except Exception as e:
        return {'error': f'CloudWatch service error: {str(e)}'}

def get_lambda_metrics():
    """Get Lambda function execution metrics for today"""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        # Get all Lambda functions
        response = lambda_client.list_functions()
        functions = response['Functions']
        
        total_invocations = 0
        function_stats = []
        
        for func in functions:
            function_name = func['FunctionName']
            
            try:
                metrics_response = cloudwatch_client.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Invocations',
                    Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,
                    Statistics=['Sum']
                )
                
                invocations = 0
                if metrics_response['Datapoints']:
                    invocations = int(metrics_response['Datapoints'][0]['Sum'])
                
                if invocations > 0:
                    function_stats.append(f"{function_name}: {invocations}")
                    total_invocations += invocations
                    
            except Exception:
                continue
        
        return {
            'total_invocations': total_invocations,
            'function_stats': function_stats,
            'message': f'Total Lambda invocations today: {total_invocations}'
        }
        
    except Exception as e:
        return {'error': f'Failed to get Lambda metrics: {str(e)}'}

def get_s3_metrics():
    """Get S3 request metrics"""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        metrics_response = cloudwatch_client.get_metric_statistics(
            Namespace='AWS/S3',
            MetricName='AllRequests',
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,
            Statistics=['Sum']
        )
        
        total_requests = 0
        if metrics_response['Datapoints']:
            total_requests = int(metrics_response['Datapoints'][0]['Sum'])
        
        return {
            'total_requests': total_requests,
            'message': f'Total S3 requests today: {total_requests}'
        }
        
    except Exception as e:
        return {'error': f'Failed to get S3 metrics: {str(e)}'}

def get_ec2_metrics():
    """Get EC2 CPU usage metrics"""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        # Get running instances
        response = ec2_client.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        instance_stats = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                
                try:
                    metrics_response = cloudwatch_client.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName='CPUUtilization',
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,
                        Statistics=['Average']
                    )
                    
                    cpu_avg = 0
                    if metrics_response['Datapoints']:
                        cpu_avg = round(metrics_response['Datapoints'][0]['Average'], 1)
                    
                    instance_stats.append(f"{instance_id}: {cpu_avg}%")
                    
                except Exception:
                    continue
        
        return {
            'instance_stats': instance_stats,
            'message': f'EC2 CPU usage (last hour): {len(instance_stats)} instances'
        }
        
    except Exception as e:
        return {'error': f'Failed to get EC2 metrics: {str(e)}'}