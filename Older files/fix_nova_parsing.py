import json
import boto3
import re

def parse_with_nova(user_message):
    """Parse user message using Nova Micro model with improved error handling"""
    try:
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock-runtime')
        
        # Create prompt for Nova Micro
        prompt = """You are an AI assistant that parses user requests about AWS S3 operations.
Extract the intent and parameters from the user's message.
Return a JSON object with the following structure:
{
  "service": "s3",
  "action": "action_name",
  "parameters": {"param1": "value1", "param2": "value2"},
  "needs_followup": true/false,
  "question": "Follow-up question if more information is needed"
}

Examples:
User: "List my S3 buckets"
{"service": "s3", "action": "list_buckets", "parameters": {}, "needs_followup": false}

User: "List files"
{"service": "s3", "action": "list_objects", "needs_followup": true, "question": "Which bucket would you like to list objects from?"}

User: "List files in bucket1"
{"service": "s3", "action": "list_objects", "parameters": {"bucket": "bucket1"}, "needs_followup": false}

User: "bucket1"
{"service": "s3", "action": "list_objects", "parameters": {"bucket": "bucket1"}, "needs_followup": false}

Parse this request: "{0}"
"""

        # Correctly formatted Nova Micro invocation
        response = bedrock.invoke_model(
            modelId='amazon.nova-micro-v1:0',
            body=json.dumps({
                'messages': [{'role': 'user', 'content': prompt.format(user_message)}]
            })
        )
        
        result = json.loads(response['body'].read())
        content = result['output']['message']['content'][0]['text']
        
        print(f"Raw Nova response: {content}")
        
        # Improved JSON extraction with regex
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            # Clean up any potential issues
            json_str = json_str.replace('\n', ' ').replace('\r', '')
            try:
                parsed = json.loads(json_str)
                print(f"Successfully parsed: {parsed}")
                return parsed
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {str(e)}")
                # Try to fix common JSON issues
                json_str = re.sub(r'([{,])\s*([a-zA-Z0-9_]+):', r'\1"\2":', json_str)
                json_str = re.sub(r':\s*([a-zA-Z0-9_]+)([,}])', r':"\1"\2', json_str)
                try:
                    parsed = json.loads(json_str)
                    print(f"Fixed and parsed: {parsed}")
                    return parsed
                except:
                    pass
        
        # Direct parsing for bucket name
        if user_message.strip().lower() == user_message.strip():  # If message is just a word
            return {
                'service': 's3',
                'action': 'list_objects',
                'parameters': {'bucket': user_message.strip()},
                'needs_followup': False
            }
        
        return {
            'service': 'unknown',
            'action': 'unknown',
            'needs_followup': True,
            'question': 'I couldn\'t understand your request. Could you please rephrase it?'
        }
        
    except Exception as e:
        print(f"Nova parsing error: {str(e)}")
        return {
            'service': 'unknown',
            'action': 'unknown',
            'needs_followup': True,
            'question': f'Error parsing your request: {str(e)}'
        }

# Test the function
if __name__ == "__main__":
    test_messages = [
        "list buckets",
        "list files",
        "tarbucket102424",  # Just a bucket name
        "list files in tarbucket102424"
    ]
    
    for message in test_messages:
        print(f"\nTesting: '{message}'")
        result = parse_with_nova(message)
        print(f"Result: {result}")
        print("-" * 50)