import boto3
import json
import uuid

def invoke_lambda(function_name, message):
    """Directly invoke a Lambda function"""
    
    print(f"Invoking Lambda function: {function_name}")
    print(f"Message: {message}")
    print("-" * 80)
    
    try:
        # Create Lambda client
        lambda_client = boto3.client('lambda')
        
        # Prepare the payload
        payload = {
            'body': json.dumps({
                'message': message,
                'session_id': str(uuid.uuid4())
            })
        }
        
        # Invoke the Lambda function
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        # Read the response
        response_payload = json.loads(response['Payload'].read().decode('utf-8'))
        
        print("\nLambda Response:")
        print("-" * 80)
        print(f"Status Code: {response['StatusCode']}")
        
        if 'FunctionError' in response:
            print(f"Error: {response['FunctionError']}")
            print(f"Error Message: {response_payload.get('errorMessage', 'Unknown error')}")
        else:
            print(f"Response: {json.dumps(response_payload, indent=2)}")
        
        return response_payload
        
    except Exception as e:
        print(f"Error invoking Lambda: {str(e)}")
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test a Lambda function directly')
    parser.add_argument('--function', '-f', default='SevaAI-S3Agent', help='Lambda function name')
    parser.add_argument('--message', '-m', default='list buckets', help='Message to send')
    
    args = parser.parse_args()
    
    invoke_lambda(args.function, args.message)