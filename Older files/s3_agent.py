import json
import boto3
import re
import uuid
from datetime import datetime
from decimal import Decimal

# AWS Services
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime')

# DynamoDB tables
command_patterns_table = dynamodb.Table('S3CommandPatterns')
session_table = dynamodb.Table('AgentSessions')

class S3Agent:
    def __init__(self):
        """Initialize the S3 Agent"""
        self.session_id = None
        self.session_data = {}
    
    def process_request(self, user_message, session_id=None):
        """Process a user request and return appropriate response"""
        # Initialize or retrieve session
        if session_id:
            self.session_id = session_id
            self.session_data = self._get_session(session_id)
        else:
            self.session_id = str(uuid.uuid4())
            self.session_data = {
                'pending_params': {},
                'current_intent': None,
                'history': []
            }
        
        # Add message to history
        self.session_data['history'].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Check if we're waiting for specific parameters
        if self.session_data.get('pending_params'):
            return self._handle_parameter_followup(user_message)
        
        # Try to match against known patterns first
        intent_match = self._match_known_patterns(user_message)
        
        if intent_match:
            # Known pattern found in knowledge base
            intent = intent_match['intent']
            params = intent_match['params']
            missing_params = intent_match['missing_params']
            
            if missing_params:
                # Need more information from user
                return self._request_missing_params(intent, params, missing_params)
            else:
                # Execute the command with all parameters
                return self._execute_s3_command(intent, params)
        else:
            # No match in knowledge base, use LLM
            return self._parse_with_llm(user_message)
    
    def _match_known_patterns(self, user_message):
        """Try to match user message against known patterns in knowledge base"""
        try:
            # Scan the command patterns table
            response = command_patterns_table.scan()
            patterns = response.get('Items', [])
            
            for pattern in patterns:
                regex = pattern.get('pattern_regex')
                if not regex:
                    continue
                
                match = re.search(regex, user_message, re.IGNORECASE)
                if match:
                    # Pattern matched
                    intent = pattern.get('intent')
                    required_params = pattern.get('required_params', [])
                    
                    # Extract parameters from regex groups
                    params = {}
                    for param in required_params:
                        if param in match.groupdict():
                            params[param] = match.group(param)
                    
                    # Check for missing parameters
                    missing_params = [p for p in required_params if p not in params]
                    
                    return {
                        'intent': intent,
                        'params': params,
                        'missing_params': missing_params
                    }
            
            return None
            
        except Exception as e:
            print(f"Error matching patterns: {str(e)}")
            return None
    
    def _parse_with_llm(self, user_message):
        """Parse user message using LLM when no known pattern matches"""
        try:
            # Prepare prompt for Nova Micro
            prompt = f"""
You are an S3 command parser. Extract the S3 operation and parameters from this request.
Return a JSON object with these fields:
- service: The AWS service (e.g., "s3")
- action: The specific operation (e.g., "list_objects", "create_bucket")
- parameters: An object containing all parameters needed
- needs_followup: Boolean indicating if more information is needed
- question: If needs_followup is true, the question to ask the user

Example: For "list files in my-bucket", return:
{{"service": "s3", "action": "list_objects", "parameters": {{"bucket": "my-bucket"}}, "needs_followup": false}}

Example: For "list files", return:
{{"service": "s3", "action": "list_objects", "needs_followup": true, "question": "Which bucket would you like to list objects from?"}}

Parse this request: "{user_message}"
"""

            # Invoke Nova Micro
            response = bedrock_runtime.invoke_model(
                modelId='amazon.nova-micro-v1:0',
                body=json.dumps({
                    'messages': [{'role': 'user', 'content': prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            content = result['output']['message']['content'][0]['text']
            
            # Extract JSON from response
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                parsed = json.loads(content[start:end])
                
                # Update knowledge base with new pattern if appropriate
                self._update_knowledge_base(user_message, parsed)
                
                # Check if we need more information
                if parsed.get('needs_followup', False):
                    # Save current intent and parameters
                    self.session_data['current_intent'] = parsed.get('action')
                    self.session_data['pending_params'] = parsed.get('parameters', {})
                    
                    # Save session and return question
                    self._save_session()
                    return {
                        'response': parsed.get('question', 'Could you provide more information?'),
                        'session_id': self.session_id,
                        'session_state': 'WAITING_INPUT'
                    }
                else:
                    # Execute command with all parameters
                    return self._execute_s3_command(
                        parsed.get('action'),
                        parsed.get('parameters', {})
                    )
            
            return {
                'response': "I couldn't understand your request. Could you please rephrase it?",
                'session_id': self.session_id,
                'session_state': 'ERROR'
            }
            
        except Exception as e:
            print(f"LLM parsing error: {str(e)}")
            return {
                'response': f"Error processing your request: {str(e)}",
                'session_id': self.session_id,
                'session_state': 'ERROR'
            }
    
    def _request_missing_params(self, intent, params, missing_params):
        """Request missing parameters from the user"""
        try:
            # Get question templates for missing parameters
            param_questions = {}
            response = command_patterns_table.scan(
                FilterExpression='intent = :intent',
                ExpressionAttributeValues={':intent': intent}
            )
            
            for item in response.get('Items', []):
                if 'param_questions' in item:
                    param_questions = item['param_questions']
                    break
            
            # Get the first missing parameter
            missing_param = missing_params[0]
            question = param_questions.get(
                missing_param, 
                f"Please provide the {missing_param} for this operation:"
            )
            
            # Update session data
            self.session_data['current_intent'] = intent
            self.session_data['pending_params'] = params
            self.session_data['missing_param'] = missing_param
            
            # Save session
            self._save_session()
            
            return {
                'response': question,
                'session_id': self.session_id,
                'session_state': 'WAITING_INPUT'
            }
            
        except Exception as e:
            print(f"Error requesting parameters: {str(e)}")
            return {
                'response': "I'm having trouble processing your request. Could you try again?",
                'session_id': self.session_id,
                'session_state': 'ERROR'
            }
    
    def _handle_parameter_followup(self, user_message):
        """Handle user response to parameter request"""
        try:
            # Get the parameter we're waiting for
            missing_param = self.session_data.get('missing_param')
            if not missing_param:
                return self.process_request(user_message)
            
            # Update the parameter with user's response
            params = self.session_data.get('pending_params', {})
            params[missing_param] = user_message.strip()
            
            # Get the intent
            intent = self.session_data.get('current_intent')
            
            # Check if we have all required parameters
            required_params = []
            response = command_patterns_table.scan(
                FilterExpression='intent = :intent',
                ExpressionAttributeValues={':intent': intent}
            )
            
            for item in response.get('Items', []):
                if 'required_params' in item:
                    required_params = item['required_params']
                    break
            
            # Check for any remaining missing parameters
            missing_params = [p for p in required_params if p not in params]
            
            if missing_params:
                # Still need more parameters
                return self._request_missing_params(intent, params, missing_params)
            else:
                # We have all parameters, execute the command
                return self._execute_s3_command(intent, params)
            
        except Exception as e:
            print(f"Error handling parameter followup: {str(e)}")
            return {
                'response': f"Error processing your response: {str(e)}",
                'session_id': self.session_id,
                'session_state': 'ERROR'
            }
    
    def _execute_s3_command(self, action, parameters):
        """Execute S3 command with provided parameters"""
        try:
            result = None
            
            # List buckets
            if action == 'list_buckets':
                response = s3.list_buckets()
                buckets = [b['Name'] for b in response.get('Buckets', [])]
                if not buckets:
                    result = "You don't have any S3 buckets."
                else:
                    result = f"📦 S3 Buckets ({len(buckets)}):\n" + "\n".join(buckets)
            
            # List objects in bucket
            elif action == 'list_objects':
                bucket = parameters.get('bucket')
                if not bucket:
                    return self._request_missing_params(action, parameters, ['bucket'])
                
                response = s3.list_objects_v2(Bucket=bucket, MaxKeys=50)
                objects = [obj['Key'] for obj in response.get('Contents', [])]
                
                if not objects:
                    result = f"Bucket '{bucket}' is empty."
                else:
                    result = f"📁 Objects in '{bucket}' ({len(objects)}):\n" + "\n".join(objects)
            
            # Create bucket
            elif action == 'create_bucket':
                bucket = parameters.get('bucket')
                if not bucket:
                    return self._request_missing_params(action, parameters, ['bucket'])
                
                s3.create_bucket(Bucket=bucket)
                result = f"✅ Bucket '{bucket}' created successfully."
            
            # Delete bucket
            elif action == 'delete_bucket':
                bucket = parameters.get('bucket')
                if not bucket:
                    return self._request_missing_params(action, parameters, ['bucket'])
                
                s3.delete_bucket(Bucket=bucket)
                result = f"✅ Bucket '{bucket}' deleted successfully."
            
            # Upload object
            elif action == 'upload_object':
                bucket = parameters.get('bucket')
                key = parameters.get('key')
                body = parameters.get('body')
                
                missing = []
                if not bucket:
                    missing.append('bucket')
                if not key:
                    missing.append('key')
                if not body:
                    missing.append('body')
                
                if missing:
                    return self._request_missing_params(action, parameters, missing)
                
                s3.put_object(Bucket=bucket, Key=key, Body=body)
                result = f"✅ Object '{key}' uploaded to '{bucket}' successfully."
            
            # Download object
            elif action == 'download_object':
                bucket = parameters.get('bucket')
                key = parameters.get('key')
                
                missing = []
                if not bucket:
                    missing.append('bucket')
                if not key:
                    missing.append('key')
                
                if missing:
                    return self._request_missing_params(action, parameters, missing)
                
                response = s3.get_object(Bucket=bucket, Key=key)
                result = f"✅ Object '{key}' downloaded from '{bucket}' successfully."
            
            # Delete object
            elif action == 'delete_object':
                bucket = parameters.get('bucket')
                key = parameters.get('key')
                
                missing = []
                if not bucket:
                    missing.append('bucket')
                if not key:
                    missing.append('key')
                
                if missing:
                    return self._request_missing_params(action, parameters, missing)
                
                s3.delete_object(Bucket=bucket, Key=key)
                result = f"✅ Object '{key}' deleted from '{bucket}' successfully."
            
            # Copy object
            elif action == 'copy_object':
                source_bucket = parameters.get('source_bucket')
                dest_bucket = parameters.get('dest_bucket')
                key = parameters.get('key')
                
                missing = []
                if not source_bucket:
                    missing.append('source_bucket')
                if not dest_bucket:
                    missing.append('dest_bucket')
                if not key:
                    missing.append('key')
                
                if missing:
                    return self._request_missing_params(action, parameters, missing)
                
                s3.copy_object(
                    CopySource={'Bucket': source_bucket, 'Key': key},
                    Bucket=dest_bucket,
                    Key=key
                )
                result = f"✅ Object '{key}' copied from '{source_bucket}' to '{dest_bucket}' successfully."
            
            else:
                result = f"S3 action '{action}' not supported yet."
            
            # Clear session data
            self.session_data = {
                'history': self.session_data.get('history', [])
            }
            
            # Add response to history
            self.session_data['history'].append({
                'role': 'assistant',
                'content': result,
                'timestamp': datetime.now().isoformat()
            })
            
            # Save session
            self._save_session()
            
            return {
                'response': result,
                'session_id': self.session_id,
                'session_state': 'COMPLETED'
            }
            
        except Exception as e:
            print(f"Error executing S3 command: {str(e)}")
            return {
                'response': f"❌ S3 Error: {str(e)}",
                'session_id': self.session_id,
                'session_state': 'ERROR'
            }
    
    def _update_knowledge_base(self, user_message, parsed_intent):
        """Update knowledge base with new pattern if appropriate"""
        try:
            # Only update if we have a valid intent and no followup needed
            if (parsed_intent.get('service') == 's3' and 
                parsed_intent.get('action') and 
                not parsed_intent.get('needs_followup', False)):
                
                # Check if this pattern already exists
                intent = parsed_intent.get('action')
                
                # Create a simple regex pattern from the user message
                # This is a simplified approach - in production you'd want more sophisticated pattern generation
                pattern = user_message.lower()
                pattern = re.escape(pattern)
                
                # Replace parameter values with named capture groups
                for param, value in parsed_intent.get('parameters', {}).items():
                    if value and value in pattern:
                        pattern = pattern.replace(re.escape(value), f"(?P<{param}>.+?)")
                
                # Add the pattern to the knowledge base
                command_patterns_table.put_item(
                    Item={
                        'pattern_id': str(uuid.uuid4()),
                        'intent': intent,
                        'pattern_regex': pattern,
                        'required_params': list(parsed_intent.get('parameters', {}).keys()),
                        'param_questions': {
                            param: f"Please provide the {param} for this operation:"
                            for param in parsed_intent.get('parameters', {})
                        },
                        'examples': [user_message],
                        'created_at': datetime.now().isoformat()
                    }
                )
                
                print(f"Added new pattern for intent: {intent}")
                
        except Exception as e:
            print(f"Error updating knowledge base: {str(e)}")
    
    def _get_session(self, session_id):
        """Retrieve session data from DynamoDB"""
        try:
            response = session_table.get_item(Key={'session_id': session_id})
            if 'Item' in response:
                return response['Item']
            return {'history': []}
        except Exception as e:
            print(f"Error retrieving session: {str(e)}")
            return {'history': []}
    
    def _save_session(self):
        """Save session data to DynamoDB"""
        try:
            # Convert to DynamoDB format (handling decimal)
            session_data = json.loads(json.dumps(self.session_data), parse_float=Decimal)
            
            session_table.put_item(
                Item={
                    'session_id': self.session_id,
                    'session_data': session_data,
                    'updated_at': datetime.now().isoformat()
                }
            )
        except Exception as e:
            print(f"Error saving session: {str(e)}")

# Lambda handler
def lambda_handler(event, context):
    """AWS Lambda handler"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        user_message = body.get('message', '')
        session_id = body.get('session_id')
        
        if not user_message:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No message provided'})
            }
        
        # Process the request
        agent = S3Agent()
        result = agent.process_request(user_message, session_id)
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Lambda error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }