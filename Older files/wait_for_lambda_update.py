import boto3
import time

def wait_for_lambda_update():
    """Wait for any pending Lambda updates to complete"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Waiting for Lambda function update to complete: {FUNCTION_NAME}")
    
    lambda_client = boto3.client('lambda')
    
    # Check function state
    last_state = None
    attempts = 0
    max_attempts = 30  # Wait up to 5 minutes (30 * 10 seconds)
    
    while attempts < max_attempts:
        try:
            # Get function state
            response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
            state = response['Configuration']['State']
            last_update_status = response['Configuration'].get('LastUpdateStatus', 'Unknown')
            
            if state != last_state or attempts % 6 == 0:  # Print every minute or on state change
                print(f"Current state: {state}, Last update status: {last_update_status}")
                last_state = state
            
            if state == 'Active' and last_update_status != 'InProgress':
                print(f"✅ Lambda function is now active and ready!")
                return True
                
            # Wait before checking again
            time.sleep(10)
            attempts += 1
            
        except Exception as e:
            print(f"Error checking Lambda state: {str(e)}")
            time.sleep(10)
            attempts += 1
    
    print("❌ Timed out waiting for Lambda function to become active")
    return False

if __name__ == "__main__":
    wait_for_lambda_update()