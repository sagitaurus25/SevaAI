import boto3
import json
import os
import time
from datetime import datetime, timedelta

# Initialize AWS clients
s3 = boto3.client('s3')
logs = boto3.client('logs')
dynamodb = boto3.resource('dynamodb')

# Constants
EXECUTION_TABLE = 'S3WorkflowExecutions'

# Common utility functions
def update_execution_step_status(execution_id, step_id, status, details=None):
    """Update the status of a workflow step in DynamoDB"""
    table = dynamodb.Table(EXECUTION_TABLE)
    update_expression = "SET steps.#step_id = :step_status"
    expression_attr_names = {"#step_id": step_id}
    expression_attr_values = {":step_status": {"status": status, "timestamp": datetime.now().isoformat()}}
    
    if details:
        expression_attr_values[":step_status"]["details"] = details
    
    table.update_item(
        Key={"execution_id": execution_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attr_names,
        ExpressionAttributeValues=expression_attr_values
    )

# Inventory Report Workflow Functions
def check_bucket_exists(event, context):
    """Check if source and destination buckets exist"""
    execution_id = event['execution_id']
    parameters = event['parameters']
    source_bucket = parameters.get('bucket')
    dest_bucket = parameters.get('destination_bucket')
    
    try:
        # Update step status to IN_PROGRESS
        update_execution_step_status(execution_id, "check_buckets", "IN_PROGRESS")
        
        result = {"source_exists": False, "destination_exists": False}
        
        # Check source bucket
        try:
            s3.head_bucket(Bucket=source_bucket)
            result["source_exists"] = True
        except Exception as e:
            result["source_error"] = str(e)
        
        # Check destination bucket
        try:
            s3.head_bucket(Bucket=dest_bucket)
            result["destination_exists"] = True
        except Exception as e:
            result["destination_error"] = str(e)
        
        # Update step status based on result
        if result["source_exists"] and result["destination_exists"]:
            update_execution_step_status(execution_id, "check_buckets", "SUCCEEDED", result)
        else:
            update_execution_step_status(execution_id, "check_buckets", "FAILED", result)
            raise Exception(f"Bucket check failed: {json.dumps(result)}")
        
        return {
            "execution_id": execution_id,
            "step_id": "check_buckets",
            "status": "SUCCEEDED",
            "result": result
        }
    except Exception as e:
        update_execution_step_status(execution_id, "check_buckets", "FAILED", {"error": str(e)})
        raise

def configure_s3_inventory(event, context):
    """Configure S3 inventory for a bucket"""
    execution_id = event['execution_id']
    parameters = event['parameters']
    source_bucket = parameters.get('bucket')
    dest_bucket = parameters.get('destination_bucket')
    format = parameters.get('format', 'CSV')
    frequency = parameters.get('frequency', 'Weekly')
    
    try:
        # Update step status to IN_PROGRESS
        update_execution_step_status(execution_id, "configure_inventory", "IN_PROGRESS")
        
        # Create inventory configuration
        inventory_id = f"Inventory-{source_bucket}-{int(time.time())}"
        
        s3.put_bucket_inventory_configuration(
            Bucket=source_bucket,
            Id=inventory_id,
            InventoryConfiguration={
                'Destination': {
                    'S3BucketDestination': {
                        'Bucket': f"arn:aws:s3:::{dest_bucket}",
                        'Format': format,
                        'Prefix': f"inventory/{source_bucket}"
                    }
                },
                'IsEnabled': True,
                'Id': inventory_id,
                'IncludedObjectVersions': 'Current',
                'Schedule': {
                    'Frequency': frequency
                },
                'OptionalFields': [
                    'Size', 'LastModifiedDate', 'StorageClass', 'ETag', 'IsMultipartUploaded'
                ]
            }
        )
        
        result = {
            "inventory_id": inventory_id,
            "source_bucket": source_bucket,
            "destination_bucket": dest_bucket,
            "format": format,
            "frequency": frequency
        }
        
        update_execution_step_status(execution_id, "configure_inventory", "SUCCEEDED", result)
        
        return {
            "execution_id": execution_id,
            "step_id": "configure_inventory",
            "status": "SUCCEEDED",
            "result": result
        }
    except Exception as e:
        update_execution_step_status(execution_id, "configure_inventory", "FAILED", {"error": str(e)})
        raise

def verify_inventory_config(event, context):
    """Verify inventory configuration is active"""
    execution_id = event['execution_id']
    parameters = event['parameters']
    source_bucket = parameters.get('bucket')
    inventory_id = event.get('configure_inventory_result', {}).get('result', {}).get('inventory_id')
    
    if not inventory_id:
        inventory_id = f"Inventory-{source_bucket}-*"  # Fallback pattern
    
    try:
        # Update step status to IN_PROGRESS
        update_execution_step_status(execution_id, "verify_configuration", "IN_PROGRESS")
        
        # Get inventory configurations
        response = s3.list_bucket_inventory_configurations(Bucket=source_bucket)
        
        inventory_configs = response.get('InventoryConfigurationList', [])
        matching_configs = [
            config for config in inventory_configs 
            if config['Id'] == inventory_id or (inventory_id.endswith('*') and config['Id'].startswith(inventory_id[:-1]))
        ]
        
        if matching_configs:
            config = matching_configs[0]
            result = {
                "inventory_id": config['Id'],
                "is_enabled": config['IsEnabled'],
                "destination": config['Destination']['S3BucketDestination']['Bucket'],
                "frequency": config['Schedule']['Frequency']
            }
            update_execution_step_status(execution_id, "verify_configuration", "SUCCEEDED", result)
        else:
            result = {"error": f"No matching inventory configuration found for ID: {inventory_id}"}
            update_execution_step_status(execution_id, "verify_configuration", "FAILED", result)
            raise Exception(f"Verification failed: {json.dumps(result)}")
        
        return {
            "execution_id": execution_id,
            "step_id": "verify_configuration",
            "status": "SUCCEEDED",
            "result": result
        }
    except Exception as e:
        update_execution_step_status(execution_id, "verify_configuration", "FAILED", {"error": str(e)})
        raise

# Log Analysis Workflow Functions
def query_cloudwatch_logs(event, context):
    """Query CloudWatch logs for error entries"""
    execution_id = event['execution_id']
    parameters = event['parameters']
    log_group = parameters.get('log_group')
    time_range = parameters.get('time_range', '1d')
    
    try:
        # Update step status to IN_PROGRESS
        update_execution_step_status(execution_id, "query_logs", "IN_PROGRESS")
        
        # Parse time range
        end_time = datetime.now()
        if time_range.endswith('d'):
            days = int(time_range[:-1])
            start_time = end_time - timedelta(days=days)
        elif time_range.endswith('h'):
            hours = int(time_range[:-1])
            start_time = end_time - timedelta(hours=hours)
        else:
            start_time = end_time - timedelta(days=1)  # Default to 1 day
        
        # Convert to milliseconds since epoch
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)
        
        # Start query
        query = "fields @timestamp, @message | filter @message like /(?i)(error|exception|fail|timeout)/ | sort @timestamp desc"
        response = logs.start_query(
            logGroupName=log_group,
            startTime=start_time_ms,
            endTime=end_time_ms,
            queryString=query
        )
        
        query_id = response['queryId']
        
        # Wait for query to complete
        status = 'Running'
        results = None
        
        while status == 'Running':
            time.sleep(1)
            response = logs.get_query_results(queryId=query_id)
            status = response['status']
            if status == 'Complete':
                results = response['results']
        
        if status == 'Complete':
            # Process results
            error_entries = []
            for result in results:
                entry = {}
                for field in result:
                    entry[field['field']] = field['value']
                error_entries.append(entry)
            
            result = {
                "query_id": query_id,
                "log_group": log_group,
                "time_range": time_range,
                "error_count": len(error_entries),
                "error_entries": error_entries[:100]  # Limit to first 100 entries
            }
            
            update_execution_step_status(execution_id, "query_logs", "SUCCEEDED", result)
        else:
            result = {"error": f"Query failed with status: {status}"}
            update_execution_step_status(execution_id, "query_logs", "FAILED", result)
            raise Exception(f"Query failed: {json.dumps(result)}")
        
        return {
            "execution_id": execution_id,
            "step_id": "query_logs",
            "status": "SUCCEEDED",
            "result": result
        }
    except Exception as e:
        update_execution_step_status(execution_id, "query_logs", "FAILED", {"error": str(e)})
        raise

def analyze_error_patterns(event, context):
    """Group errors by type and frequency"""
    execution_id = event['execution_id']
    query_result = event.get('query_logs_result', {}).get('result', {})
    error_entries = query_result.get('error_entries', [])
    
    try:
        # Update step status to IN_PROGRESS
        update_execution_step_status(execution_id, "analyze_errors", "IN_PROGRESS")
        
        # Group errors by pattern
        error_patterns = {}
        for entry in error_entries:
            message = entry.get('@message', '')
            
            # Extract error type (simple approach - could be enhanced with regex patterns)
            error_type = "Unknown"
            if "Exception:" in message:
                error_type = message.split("Exception:")[0].strip().split()[-1] + "Exception"
            elif "Error:" in message:
                error_type = message.split("Error:")[0].strip().split()[-1] + "Error"
            elif "failed" in message.lower():
                error_type = "FailureError"
            elif "timeout" in message.lower():
                error_type = "TimeoutError"
            
            if error_type not in error_patterns:
                error_patterns[error_type] = {
                    "count": 0,
                    "examples": []
                }
            
            error_patterns[error_type]["count"] += 1
            if len(error_patterns[error_type]["examples"]) < 3:  # Store up to 3 examples
                error_patterns[error_type]["examples"].append(message)
        
        # Sort by frequency
        sorted_patterns = sorted(
            [{"type": k, **v} for k, v in error_patterns.items()],
            key=lambda x: x["count"],
            reverse=True
        )
        
        result = {
            "total_errors": len(error_entries),
            "unique_patterns": len(error_patterns),
            "patterns": sorted_patterns
        }
        
        update_execution_step_status(execution_id, "analyze_errors", "SUCCEEDED", result)
        
        return {
            "execution_id": execution_id,
            "step_id": "analyze_errors",
            "status": "SUCCEEDED",
            "result": result
        }
    except Exception as e:
        update_execution_step_status(execution_id, "analyze_errors", "FAILED", {"error": str(e)})
        raise

def generate_error_report(event, context):
    """Generate summary statistics and insights"""
    execution_id = event['execution_id']
    parameters = event['parameters']
    query_result = event.get('query_logs_result', {}).get('result', {})
    analysis_result = event.get('analyze_errors_result', {}).get('result', {})
    error_threshold = int(parameters.get('error_threshold', 5))
    
    try:
        # Update step status to IN_PROGRESS
        update_execution_step_status(execution_id, "generate_report", "IN_PROGRESS")
        
        # Generate insights
        insights = []
        total_errors = analysis_result.get('total_errors', 0)
        patterns = analysis_result.get('patterns', [])
        
        if total_errors == 0:
            insights.append("No errors found in the specified time range.")
        else:
            # Add insights based on error patterns
            if patterns:
                top_error = patterns[0]
                insights.append(f"Most common error: {top_error['type']} ({top_error['count']} occurrences)")
                
                # Check for errors above threshold
                critical_errors = [p for p in patterns if p['count'] > error_threshold]
                if critical_errors:
                    insights.append(f"Found {len(critical_errors)} error types above threshold ({error_threshold}):")
                    for err in critical_errors:
                        insights.append(f"- {err['type']}: {err['count']} occurrences")
                
                # Suggest actions
                if "TimeoutError" in [p['type'] for p in patterns]:
                    insights.append("Action: Consider increasing timeout settings or optimizing slow operations.")
                
                if "MemoryError" in [p['type'] for p in patterns]:
                    insights.append("Action: Consider increasing memory allocation for affected functions.")
        
        # Generate report
        report = {
            "summary": {
                "log_group": query_result.get('log_group'),
                "time_range": query_result.get('time_range'),
                "total_errors": total_errors,
                "unique_patterns": analysis_result.get('unique_patterns', 0)
            },
            "insights": insights,
            "error_patterns": patterns,
            "generated_at": datetime.now().isoformat()
        }
        
        # Store report in S3 (optional)
        # report_bucket = os.environ.get('REPORT_BUCKET')
        # if report_bucket:
        #     report_key = f"error-reports/{execution_id}.json"
        #     s3.put_object(
        #         Bucket=report_bucket,
        #         Key=report_key,
        #         Body=json.dumps(report),
        #         ContentType='application/json'
        #     )
        #     report["report_location"] = f"s3://{report_bucket}/{report_key}"
        
        update_execution_step_status(execution_id, "generate_report", "SUCCEEDED", report)
        
        return {
            "execution_id": execution_id,
            "step_id": "generate_report",
            "status": "SUCCEEDED",
            "result": report
        }
    except Exception as e:
        update_execution_step_status(execution_id, "generate_report", "FAILED", {"error": str(e)})
        raise

# Lifecycle Management Workflow Functions
def create_lifecycle_configuration(event, context):
    """Create lifecycle configuration with specified rules"""
    execution_id = event['execution_id']
    parameters = event['parameters']
    bucket = parameters.get('bucket')
    prefix = parameters.get('prefix', 'logs/')
    transition_days = int(parameters.get('transition_days', 30))
    expiration_days = int(parameters.get('expiration_days', 365))
    
    try:
        # Update step status to IN_PROGRESS
        update_execution_step_status(execution_id, "create_lifecycle_config", "IN_PROGRESS")
        
        # Create lifecycle configuration
        lifecycle_config = {
            'Rules': [
                {
                    'ID': f'TransitionToGlacier-{prefix.replace("/", "-")}',
                    'Filter': {
                        'Prefix': prefix
                    },
                    'Status': 'Enabled',
                    'Transitions': [
                        {
                            'Days': transition_days,
                            'StorageClass': 'GLACIER'
                        }
                    ],
                    'Expiration': {
                        'Days': expiration_days
                    }
                }
            ]
        }
        
        result = {
            "bucket": bucket,
            "prefix": prefix,
            "transition_days": transition_days,
            "expiration_days": expiration_days,
            "lifecycle_config": lifecycle_config
        }
        
        update_execution_step_status(execution_id, "create_lifecycle_config", "SUCCEEDED", result)
        
        return {
            "execution_id": execution_id,
            "step_id": "create_lifecycle_config",
            "status": "SUCCEEDED",
            "result": result
        }
    except Exception as e:
        update_execution_step_status(execution_id, "create_lifecycle_config", "FAILED", {"error": str(e)})
        raise

def apply_lifecycle_configuration(event, context):
    """Apply lifecycle configuration to bucket"""
    execution_id = event['execution_id']
    parameters = event['parameters']
    bucket = parameters.get('bucket')
    lifecycle_config = event.get('create_lifecycle_config_result', {}).get('result', {}).get('lifecycle_config')
    
    try:
        # Update step status to IN_PROGRESS
        update_execution_step_status(execution_id, "apply_lifecycle_config", "IN_PROGRESS")
        
        # Apply lifecycle configuration
        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket,
            LifecycleConfiguration=lifecycle_config
        )
        
        result = {
            "bucket": bucket,
            "status": "applied",
            "timestamp": datetime.now().isoformat()
        }
        
        update_execution_step_status(execution_id, "apply_lifecycle_config", "SUCCEEDED", result)
        
        return {
            "execution_id": execution_id,
            "step_id": "apply_lifecycle_config",
            "status": "SUCCEEDED",
            "result": result
        }
    except Exception as e:
        update_execution_step_status(execution_id, "apply_lifecycle_config", "FAILED", {"error": str(e)})
        raise

def verify_lifecycle_configuration(event, context):
    """Verify lifecycle configuration is active"""
    execution_id = event['execution_id']
    parameters = event['parameters']
    bucket = parameters.get('bucket')
    prefix = parameters.get('prefix', 'logs/')
    
    try:
        # Update step status to IN_PROGRESS
        update_execution_step_status(execution_id, "verify_lifecycle_config", "IN_PROGRESS")
        
        # Get lifecycle configuration
        response = s3.get_bucket_lifecycle_configuration(Bucket=bucket)
        
        # Check if our rule exists
        rules = response.get('Rules', [])
        matching_rules = [
            rule for rule in rules 
            if rule.get('Filter', {}).get('Prefix') == prefix and rule['Status'] == 'Enabled'
        ]
        
        if matching_rules:
            rule = matching_rules[0]
            result = {
                "bucket": bucket,
                "rule_id": rule['ID'],
                "prefix": prefix,
                "status": "active",
                "transitions": rule.get('Transitions', []),
                "expiration": rule.get('Expiration', {})
            }
            update_execution_step_status(execution_id, "verify_lifecycle_config", "SUCCEEDED", result)
        else:
            result = {"error": f"No matching lifecycle rule found for prefix: {prefix}"}
            update_execution_step_status(execution_id, "verify_lifecycle_config", "FAILED", result)
            raise Exception(f"Verification failed: {json.dumps(result)}")
        
        return {
            "execution_id": execution_id,
            "step_id": "verify_lifecycle_config",
            "status": "SUCCEEDED",
            "result": result
        }
    except Exception as e:
        update_execution_step_status(execution_id, "verify_lifecycle_config", "FAILED", {"error": str(e)})
        raise