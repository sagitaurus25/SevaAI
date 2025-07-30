import requests
import json
import argparse
import sys

# API Gateway endpoint - update this with your actual endpoint
API_ENDPOINT = 'https://your-api-gateway-url.amazonaws.com/prod/s3agent'

def test_api(message):
    """Test the S3 agent API with a message"""
    try:
        print(f"Sending message: '{message}'")
        print("-" * 50)
        
        response = requests.post(
            API_ENDPOINT,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            json={
                'message': message,
                'session_id': 'test-session'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("\nAPI Response:")
            print("-" * 50)
            print(f"Status: ✅ {response.status_code}")
            
            if 'response' in data:
                print(f"\nResponse: {data['response']}")
            else:
                print(f"\nUnexpected response format: {json.dumps(data, indent=2)}")
                
            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Error testing API: {str(e)}")
        return False

def interactive_mode():
    """Interactive mode for testing the API"""
    print("S3 Agent API Tester")
    print("Type 'exit' to quit")
    
    while True:
        message = input("\nEnter a message: ")
        
        if message.lower() == 'exit':
            break
            
        test_api(message)

def main():
    parser = argparse.ArgumentParser(description='Test the S3 agent API')
    parser.add_argument('--message', '-m', help='Message to send to the API')
    parser.add_argument('--endpoint', '-e', help='API Gateway endpoint URL')
    
    args = parser.parse_args()
    
    global API_ENDPOINT
    if args.endpoint:
        API_ENDPOINT = args.endpoint
    
    if API_ENDPOINT == 'https://your-api-gateway-url.amazonaws.com/prod/s3agent':
        print("❌ Error: Please update the API_ENDPOINT in the script with your actual API Gateway URL")
        print("Usage: python test_s3_agent_api.py --endpoint https://your-api-gateway-url.amazonaws.com/prod/s3agent")
        sys.exit(1)
    
    if args.message:
        test_api(args.message)
    else:
        interactive_mode()

if __name__ == "__main__":
    main()