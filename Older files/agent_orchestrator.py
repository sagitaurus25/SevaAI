import json
import boto3
import os
import time
import uuid
import re
from decimal import Decimal

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime')
lambda_client = boto3.client('lambda')

# Table names
COMMAND_PATTERNS_TABLE = os.environ.get('COMMAND_PATTERNS_TABLE', 'AWSAgentCommandPatterns')
SESSION_STATE_TABLE = os.environ.get('SESSION_STATE_TABLE', 'AWSAgentSessionState')
CONVERSATION_HISTORY_TABLE = os.environ.get('CONVERSATION_HISTORY_TABLE', 'AWSAgentConversationHistory')

# Service handler Lambda functions
SERVICE_HANDLERS = {
    's3': os.environ.get('S3_HANDLER_FUNCTION', 'AWSAgent-S3Handler'),
    'lambda': os.environ.get('LAMBDA_HANDLER_FUNCTION', 'AWSAgent-LambdaHandler'),
    'ec2': os.environ.get('EC2_HANDLER_FUNCTION', 'AWSAgent-EC2Handler'),
    'iam': os.environ.get('IAM_HANDLER_FUNCTION', 'AWSAgent-IAMHandler'),
    'cloudwatch': os.environ.get('CLOUDWATCH_HANDLER_FUNCTION', 'AWSAgent-CloudWatchHandler')
}

# LLM settings
LLM_MODEL = os.environ.get('LLM_MODEL', 'anthropic.claude-3-sonnet-20240229-v1:0')
USE_MCP = os.environ.get('USE_MCP', 'false').lower() == 'true'
MCP_ENDPOINT = os.environ.get('MCP_ENDPOINT', '')

def lambda_handler(event, context):
    """Main Lambda handler function"""
    
    # Handle WebSocket events
    if 'requestContext' in event and 'routeKey' in event['requestContext']:
        connection_id = event['requestContext']['connectionId']
        route_key = event['requestContext']['routeKey']
        
        if route_key == '$connect':
            return handle_connect(event)
        elif route_key == '$disconnect':
            return handle_disconnect(event)
        elif route_key == 'sendMessage':
            return handle_message(event, connection_id)
    
    # Handle API Gateway REST API events
    elif 'body' in event:
        body = json.loads(event['body'])
        session_id = body.get('session_id')
        
        if not session_id:
            session_id = create_new_session()
        
        return process_user_request(body.get('message', ''), session_id)
    
    return {
        'statusCode': 400,
        'body': json.dumps({'error': 'Invalid request format'})
    }

def handle_connect(event):
    """Handle WebSocket connect event"""
    # Create a new session for this connection
    session_id = create_new_session()
    
    return {
        'statusCode': 200,
        'body': json.dumps({'session_id': session_id, 'message': 'Connected successfully'})
    }

def handle_disconnect(event):
    """Handle WebSocket disconnect event"""
    # Clean up could be done here if needed
    return {'statusCode': 200}

def handle_message(event, connection_id):
    """Handle WebSocket message event"""
    body = json.loads(event['body'])
    session_id = body.get('session_id')
    message = body.get('message', '')
    
    if not session_id:
        session_id = create_new_session()
    
    # Process the message
    response = process_user_request(message, session_id)
    
    # Send response back through WebSocket
    api_client = boto3.client('apigatewaymanagementapi', 
                             endpoint_url=f"https://{event['requestContext']['domainName']}/{event['requestContext']['stage']}")
    
    api_client.post_to_connection(
        ConnectionId=connection_id,
        Data=json.dumps(response['body'] if isinstance(response['body'], dict) else json.loads(response['body']))
    )
    
    return {'statusCode': 200}

def create_new_session():
    """Create a new session and return the session ID"""
    session_id = str(uuid.uuid4())
    table = dynamodb.Table(SESSION_STATE_TABLE)
    
    table.put_item(Item={
        'session_id': session_id,
        'context': {},
        'created_at': Decimal(str(time.time())),
        'last_updated': Decimal(str(time.time()))
    })
    
    return session_id

def get_session_state(session_id):
    """Get the current session state"""
    table = dynamodb.Table(SESSION_STATE_TABLE)
    
    response = table.get_item(Key={'session_id': session_id})
    if 'Item' not in response:
        # Create a new session if it doesn't exist
        return {'session_id': session_id, 'context': {}}
    
    return response['Item']

def update_session_state(session_id, context):
    """Update the session state with new context"""
    table = dynamodb.Table(SESSION_STATE_TABLE)
    
    table.update_item(
        Key={'session_id': session_id},
        UpdateExpression='SET context = :c, last_updated = :t',
        ExpressionAttributeValues={
            ':c': context,
            ':t': Decimal(str(time.time()))
        }
    )

def add_to_conversation_history(session_id, role, message, metadata=None):
    """Add a message to the conversation history"""
    table = dynamodb.Table(CONVERSATION_HISTORY_TABLE)
    
    if metadata is None:
        metadata = {}
    
    table.put_item(Item={
        'session_id': session_id,
        'timestamp': Decimal(str(time.time())),
        'role': role,  # 'user' or 'assistant'
        'message': message,
        'metadata': metadata
    })

def get_conversation_history(session_id, limit=10):
    """Get the conversation history for a session"""
    table = dynamodb.Table(CONVERSATION_HISTORY_TABLE)
    
    response = table.query(
        KeyConditionExpression='session_id = :sid',
        ExpressionAttributeValues={':sid': session_id},
        ScanIndexForward=True,  # ascending order
        Limit=limit
    )
    
    return response.get('Items', [])

def find_command_pattern(query, service=None):
    """Find a matching command pattern in the knowledge base"""
    table = dynamodb.Table(COMMAND_PATTERNS_TABLE)
    
    # If service is specified, filter by service
    if service:
        response = table.scan(
            FilterExpression='service = :svc',
            ExpressionAttributeValues={':svc': service}
        )
    else:
        response = table.scan()
    
    items = response.get('Items', [])
    best_match = None
    
    # Simple matching logic - can be enhanced with fuzzy matching
    query_lower = query.lower()
    
    for item in items:
        # Check if intent pattern is in the query
        if item['intent_pattern'].lower() in query_lower:
            return item
        
        # Check example phrases
        for phrase in item.get('example_phrases', []):
            if phrase.lower() in query_lower:
                best_match = item
                break
        
        if best_match:
            break
    
    return best_match

def extract_parameters(query, required_params):
    """Extract required parameters from the query"""
    extracted = {}
    
    # Simple parameter extraction - can be enhanced with regex or NLP
    for param in required_params:
        # Example: Extract bucket_name
        if param == 'bucket_name':
            match = re.search(r'(?:bucket|s3)[:\s]+([a-z0-9.-]+)', query, re.IGNORECASE)
            if match:
                extracted['bucket_name'] = match.group(1)
        
        # Example: Extract instance_id
        elif param == 'instance_id':
            match = re.search(r'(?:instance|server|ec2)[:\s]+(i-[a-z0-9]+)', query, re.IGNORECASE)
            if match:
                extracted['instance_id'] = match.group(1)
        
        # Example: Extract function_name
        elif param == 'function_name':
            match = re.search(r'(?:function|lambda)[:\s]+([a-zA-Z0-9_-]+)', query, re.IGNORECASE)
            if match:
                extracted['function_name'] = match.group(1)
    
    return extracted

def parse_with_llm(query, conversation_history=None):
    """Parse the query using the LLM to identify intent and parameters"""
    
    # Prepare conversation history for context
    history_text = ""
    if conversation_history:
        for msg in conversation_history:
            role = msg['role']
            content = msg['message']
            history_text += f"{role}: {content}\n"
    
    # Create the prompt for the LLM
    prompt = f"""You are an AI assistant that helps users interact with AWS services through natural language.
Given the following user request, identify:
1. The AWS service being referenced (e.g., s3, ec2, lambda, iam)
2. The specific action the user wants to perform
3. Any parameters needed for the action

User request: "{query}"

Previous conversation context:
{history_text}

Respond in JSON format:
{{
  "service": "service_name",
  "action": "action_name",
  "parameters": {{
    "param1": "value1",
    "param2": "value2"
  }}
}}
"""

    # Call Bedrock with the prompt
    response = bedrock.invoke_model(
        modelId=LLM_MODEL,
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })
    )
    
    response_body = json.loads(response['body'].read().decode('utf-8'))
    content = response_body['content'][0]['text']
    
    # Extract JSON from the response
    try:
        # Find JSON in the response
        json_match = re.search(r'({[\s\S]*})', content)
        if json_match:
            json_str = json_match.group(1)
            parsed_result = json.loads(json_str)
            return parsed_result
        else:
            return {
                "service": "unknown",
                "action": "unknown",
                "parameters": {}
            }
    except Exception as e:
        print(f"Error parsing LLM response: {str(e)}")
        return {
            "service": "unknown",
            "action": "unknown",
            "parameters": {}
        }

def call_service_handler(service, action, parameters, session_id):
    """Call the appropriate service handler Lambda function"""
    
    if service not in SERVICE_HANDLERS:
        return {
            'success': False,
            'message': f"Service '{service}' is not supported."
        }
    
    try:
        response = lambda_client.invoke(
            FunctionName=SERVICE_HANDLERS[service],
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'action': action,
                'parameters': parameters,
                'session_id': session_id
            })
        )
        
        payload = json.loads(response['Payload'].read().decode('utf-8'))
        return payload
    except Exception as e:
        print(f"Error calling service handler: {str(e)}")
        return {
            'success': False,
            'message': f"Error executing command: {str(e)}"
        }

def process_user_request(message, session_id):
    """Process a user request and generate a response"""
    
    # Add user message to conversation history
    add_to_conversation_history(session_id, 'user', message)
    
    # Get current session state
    session_state = get_session_state(session_id)
    context = session_state.get('context', {})
    
    # Check if we're in a follow-up state
    if 'awaiting_followup' in context and context['awaiting_followup']:
        # We're expecting a follow-up response from the user
        followup_param = context.get('followup_param')
        service = context.get('service')
        action = context.get('action')
        parameters = context.get('parameters', {})
        
        # Update parameters with the user's response
        if followup_param:
            # Handle comma-separated values
            if ',' in message:
                parameters[followup_param] = [item.strip() for item in message.split(',')]
            else:
                parameters[followup_param] = message.strip()
        
        # Clear the follow-up state
        context['awaiting_followup'] = False
        context['followup_param'] = None
        update_session_state(session_id, context)
        
        # Call the service handler with the updated parameters
        result = call_service_handler(service, action, parameters, session_id)
        
        # Add assistant response to conversation history
        add_to_conversation_history(session_id, 'assistant', result.get('message', 'Command executed'))
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    
    # Not in follow-up state, process as a new request
    
    # First, try to match against known command patterns
    command_pattern = find_command_pattern(message)
    
    if command_pattern:
        service = command_pattern.get('service')
        action = command_pattern.get('action')
        required_params = command_pattern.get('required_params', [])
        
        # Extract parameters from the message
        parameters = extract_parameters(message, required_params)
        
        # Check if we have all required parameters
        missing_params = [param for param in required_params if param not in parameters]
        
        if missing_params and command_pattern.get('needs_followup', False):
            # We need to ask for more information
            followup_question = command_pattern.get('followup_question', f"Please provide the {missing_params[0]}")
            
            # Update session state to indicate we're waiting for a follow-up
            context['awaiting_followup'] = True
            context['followup_param'] = missing_params[0]
            context['service'] = service
            context['action'] = action
            context['parameters'] = parameters
            update_session_state(session_id, context)
            
            # Add assistant response to conversation history
            add_to_conversation_history(session_id, 'assistant', followup_question)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': followup_question,
                    'awaiting_followup': True
                })
            }
        else:
            # We have all required parameters, execute the command
            result = call_service_handler(service, action, parameters, session_id)
            
            # Add assistant response to conversation history
            add_to_conversation_history(session_id, 'assistant', result.get('message', 'Command executed'))
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
    else:
        # No matching pattern found, use LLM to parse the request
        conversation_history = get_conversation_history(session_id)
        parsed_result = parse_with_llm(message, conversation_history)
        
        service = parsed_result.get('service')
        action = parsed_result.get('action')
        parameters = parsed_result.get('parameters', {})
        
        if service == 'unknown' or action == 'unknown':
            response = {
                'success': False,
                'message': "I'm sorry, I couldn't understand what you want to do. Could you please rephrase your request?"
            }
            
            # Add assistant response to conversation history
            add_to_conversation_history(session_id, 'assistant', response['message'])
            
            return {
                'statusCode': 200,
                'body': json.dumps(response)
            }
        
        # Check if we need to use MCP
        if USE_MCP and MCP_ENDPOINT:
            # Implement MCP integration here
            pass
        
        # Call the service handler
        result = call_service_handler(service, action, parameters, session_id)
        
        # Add assistant response to conversation history
        add_to_conversation_history(session_id, 'assistant', result.get('message', 'Command executed'))
        
        # If this was a successful new pattern, consider adding it to the knowledge base
        if result.get('success', False):
            # This would be implemented in a real system
            pass
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }