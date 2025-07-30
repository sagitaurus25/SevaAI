import boto3
import time
from datetime import datetime, timedelta

def check_lambda_logs(function_name, minutes=10):
    """Check CloudWatch logs for a Lambda function"""
    
    print(f"Checking logs for Lambda function: {function_name}")
    print(f"Looking at logs from the last {minutes} minutes")
    print("-" * 80)
    
    try:
        # Create CloudWatch Logs client
        logs_client = boto3.client('logs')
        
        # Get the log group name for the Lambda function
        log_group_name = f"/aws/lambda/{function_name}"
        
        # Calculate the start time (minutes ago)
        start_time = int((datetime.now() - timedelta(minutes=minutes)).timestamp() * 1000)
        end_time = int(datetime.now().timestamp() * 1000)
        
        # Get log streams
        response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if not response.get('logStreams'):
            print(f"No log streams found for {log_group_name}")
            return
        
        # Get logs from each stream
        for stream in response['logStreams']:
            stream_name = stream['logStreamName']
            print(f"\nLog Stream: {stream_name}")
            print("-" * 80)
            
            try:
                log_events = logs_client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=stream_name,
                    startTime=start_time,
                    endTime=end_time,
                    limit=100
                )
                
                for event in log_events['events']:
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    message = event['message']
                    print(f"{timestamp}: {message}")
                
                if not log_events['events']:
                    print("No log events found in this stream for the specified time period")
            
            except Exception as e:
                print(f"Error getting logs for stream {stream_name}: {str(e)}")
        
    except Exception as e:
        print(f"Error checking logs: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Check CloudWatch logs for a Lambda function')
    parser.add_argument('--function', '-f', default='SevaAI-S3Agent', help='Lambda function name')
    parser.add_argument('--minutes', '-m', type=int, default=10, help='Minutes to look back')
    
    args = parser.parse_args()
    
    check_lambda_logs(args.function, args.minutes)