#!/usr/bin/env python3

import boto3
import json
import time
import uuid

def setup_s3_replication(source_bucket, destination_bucket, destination_region='us-west-2'):
    """
    Set up cross-region replication between S3 buckets
    
    Args:
        source_bucket (str): Name of the source bucket
        destination_bucket (str): Name of the destination bucket
        destination_region (str): Region for the destination bucket
    """
    print(f"Setting up cross-region replication from {source_bucket} to {destination_bucket} in {destination_region}")
    
    # Initialize clients
    s3 = boto3.client('s3')
    iam = boto3.client('iam')
    s3_dest = boto3.client('s3', region_name=destination_region)
    
    # Step 1: Enable versioning on source bucket
    print("1. Enabling versioning on source bucket...")
    try:
        s3.put_bucket_versioning(
            Bucket=source_bucket,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        print("✅ Versioning enabled on source bucket")
    except Exception as e:
        print(f"❌ Error enabling versioning on source bucket: {str(e)}")
        return False
    
    # Step 2: Create destination bucket if it doesn't exist
    print(f"2. Creating destination bucket in {destination_region}...")
    try:
        # Check if bucket exists
        try:
            s3_dest.head_bucket(Bucket=destination_bucket)
            print(f"✓ Destination bucket already exists")
        except:
            # Create bucket in the specified region
            if destination_region == 'us-east-1':
                s3_dest.create_bucket(Bucket=destination_bucket)
            else:
                s3_dest.create_bucket(
                    Bucket=destination_bucket,
                    CreateBucketConfiguration={'LocationConstraint': destination_region}
                )
            print(f"✅ Destination bucket created in {destination_region}")
        
        # Enable versioning on destination bucket
        s3_dest.put_bucket_versioning(
            Bucket=destination_bucket,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        print("✅ Versioning enabled on destination bucket")
    except Exception as e:
        print(f"❌ Error setting up destination bucket: {str(e)}")
        return False
    
    # Step 3: Create IAM role for replication
    role_name = f"s3-replication-role-{uuid.uuid4().hex[:8]}"
    print(f"3. Creating IAM role: {role_name}...")
    
    # Create trust policy
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "s3.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        # Create the role
        role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Role for S3 replication from {source_bucket} to {destination_bucket}"
        )
        role_arn = role_response['Role']['Arn']
        print(f"✅ IAM role created: {role_arn}")
        
        # Create policy document
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetReplicationConfiguration",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{source_bucket}"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObjectVersion",
                        "s3:GetObjectVersionAcl",
                        "s3:GetObjectVersionTagging"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{source_bucket}/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:ReplicateObject",
                        "s3:ReplicateDelete",
                        "s3:ReplicateTags"
                    ],
                    "Resource": f"arn:aws:s3:::{destination_bucket}/*"
                }
            ]
        }
        
        # Attach policy to role
        policy_name = f"s3-replication-policy-{uuid.uuid4().hex[:8]}"
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print(f"✅ Policy attached to role")
        
        # Wait for role to propagate
        print("Waiting for IAM role to propagate...")
        time.sleep(15)
        
    except Exception as e:
        print(f"❌ Error creating IAM role: {str(e)}")
        return False
    
    # Step 4: Configure replication
    print("4. Configuring replication...")
    try:
        replication_config = {
            'Role': role_arn,
            'Rules': [
                {
                    'ID': f"ReplicationRule-{uuid.uuid4().hex[:8]}",
                    'Status': 'Enabled',
                    'Priority': 1,
                    'DeleteMarkerReplication': {'Status': 'Disabled'},
                    'Destination': {
                        'Bucket': f"arn:aws:s3:::{destination_bucket}",
                        'StorageClass': 'STANDARD'
                    }
                }
            ]
        }
        
        s3.put_bucket_replication(
            Bucket=source_bucket,
            ReplicationConfiguration=replication_config
        )
        print("✅ Replication configuration applied")
        
    except Exception as e:
        print(f"❌ Error configuring replication: {str(e)}")
        return False
    
    # Step 5: Verify replication status
    print("5. Verifying replication configuration...")
    try:
        response = s3.get_bucket_replication(Bucket=source_bucket)
        if 'ReplicationConfiguration' in response:
            print("✅ Replication configuration verified")
            print(f"✅ Cross-region replication setup complete!")
            print(f"Source bucket: {source_bucket}")
            print(f"Destination bucket: {destination_bucket} (in {destination_region})")
            print(f"IAM role: {role_name}")
            print("\nNote: Initial replication may take some time to complete.")
            return True
        else:
            print("❌ Replication configuration not found")
            return False
    except Exception as e:
        print(f"❌ Error verifying replication: {str(e)}")
        return False

def add_replication_command():
    """Add replication command to the S3 agent Lambda"""
    
    # Lambda function name
    FUNCTION_NAME = 'SevaAI-S3Agent'
    
    print(f"Adding replication command to Lambda: {FUNCTION_NAME}")
    
    # Get the current Lambda function code
    lambda_client = boto3.client('lambda')
    response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
    code_location = response['Code']['Location']
    
    import requests
    r = requests.get(code_location)
    
    # Save the current code
    with open('lambda_current.zip', 'wb') as f:
        f.write(r.content)
    
    # Extract the current code
    import zipfile
    import os
    import io
    with zipfile.ZipFile('lambda_current.zip', 'r') as zip_ref:
        zip_ref.extractall('lambda_extract')
    
    # Read the current lambda_function.py
    with open('lambda_extract/lambda_function.py', 'r') as f:
        current_code = f.read()
    
    # Add replication function
    replication_function = '''
def setup_bucket_replication(source_bucket, destination_bucket, destination_region='us-west-2'):
    """Set up cross-region replication between S3 buckets"""
    try:
        # Step 1: Enable versioning on source bucket
        s3.put_bucket_versioning(
            Bucket=source_bucket,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        
        # Step 2: Check if destination bucket exists, create if not
        s3_dest = boto3.client('s3', region_name=destination_region)
        try:
            s3_dest.head_bucket(Bucket=destination_bucket)
        except:
            # Create bucket in the specified region
            if destination_region == 'us-east-1':
                s3_dest.create_bucket(Bucket=destination_bucket)
            else:
                s3_dest.create_bucket(
                    Bucket=destination_bucket,
                    CreateBucketConfiguration={'LocationConstraint': destination_region}
                )
        
        # Enable versioning on destination bucket
        s3_dest.put_bucket_versioning(
            Bucket=destination_bucket,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        
        # Step 3: Create IAM role for replication
        iam = boto3.client('iam')
        role_name = f"s3-replication-role-{uuid.uuid4().hex[:8]}"
        
        # Create trust policy
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "s3.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        # Create the role
        role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Role for S3 replication from {source_bucket} to {destination_bucket}"
        )
        role_arn = role_response['Role']['Arn']
        
        # Create policy document
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetReplicationConfiguration",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{source_bucket}"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObjectVersion",
                        "s3:GetObjectVersionAcl",
                        "s3:GetObjectVersionTagging"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{source_bucket}/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:ReplicateObject",
                        "s3:ReplicateDelete",
                        "s3:ReplicateTags"
                    ],
                    "Resource": f"arn:aws:s3:::{destination_bucket}/*"
                }
            ]
        }
        
        # Attach policy to role
        policy_name = f"s3-replication-policy-{uuid.uuid4().hex[:8]}"
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        
        # Wait for role to propagate
        import time
        time.sleep(15)
        
        # Step 4: Configure replication
        replication_config = {
            'Role': role_arn,
            'Rules': [
                {
                    'ID': f"ReplicationRule-{uuid.uuid4().hex[:8]}",
                    'Status': 'Enabled',
                    'Priority': 1,
                    'DeleteMarkerReplication': {'Status': 'Disabled'},
                    'Destination': {
                        'Bucket': f"arn:aws:s3:::{destination_bucket}",
                        'StorageClass': 'STANDARD'
                    }
                }
            ]
        }
        
        s3.put_bucket_replication(
            Bucket=source_bucket,
            ReplicationConfiguration=replication_config
        )
        
        # Step 5: Verify replication status
        response = s3.get_bucket_replication(Bucket=source_bucket)
        if 'ReplicationConfiguration' in response:
            return f"✅ Cross-region replication setup complete!\\n" + \\
                   f"Source bucket: {source_bucket}\\n" + \\
                   f"Destination bucket: {destination_bucket} (in {destination_region})\\n" + \\
                   f"IAM role: {role_name}\\n\\n" + \\
                   f"Note: Initial replication may take some time to complete."
        else:
            return f"❌ Replication configuration not found"
            
    except Exception as e:
        return f"❌ Error setting up replication: {str(e)}"
'''
    
    # Add import for json if not already there
    if 'import json' not in current_code:
        current_code = current_code.replace('import boto3', 'import boto3\nimport json')
    
    # Add the function to the code
    function_insertion_point = current_code.rfind('def test_connectivity')
    updated_code = current_code[:function_insertion_point] + replication_function + '\n\n' + current_code[function_insertion_point:]
    
    # Add command handler
    command_handler = '''
        # Setup replication command
        if 'setup replication' in user_message_lower or 'configure replication' in user_message_lower:
            # Extract source bucket
            source_bucket = None
            if 'from' in user_message_lower and 'to' in user_message_lower:
                from_index = user_message_lower.index('from') + 5
                to_index = user_message_lower.index('to')
                source_bucket = user_message_lower[from_index:to_index].strip()
                
                # Extract destination bucket
                dest_index = to_index + 3
                dest_parts = user_message_lower[dest_index:].split('in')
                destination_bucket = dest_parts[0].strip()
                
                # Extract region if specified
                destination_region = 'us-west-2'  # Default
                if len(dest_parts) > 1 and 'region' in dest_parts[1]:
                    region_parts = dest_parts[1].split('region')
                    if len(region_parts) > 1:
                        destination_region = region_parts[1].strip()
                
                if source_bucket and destination_bucket:
                    result = setup_bucket_replication(source_bucket, destination_bucket, destination_region)
                    return create_response(result)
            
            return create_response("Please specify source and destination buckets.\\nExample: setup replication from source-bucket to destination-bucket in region us-west-2")
'''
    
    # Find a good place to insert the command handler
    handler_insertion_point = updated_code.find('# Handle bucket name response after list files')
    updated_code = updated_code[:handler_insertion_point] + command_handler + updated_code[handler_insertion_point:]
    
    # Add syntax helper
    syntax_helper = '''
        if user_message_lower == 'replication' or user_message_lower == 'setup replication':
            return create_response("Syntax: `setup replication from SOURCE_BUCKET to DESTINATION_BUCKET in region REGION`\\nExample: setup replication from my-source-bucket to my-backup-bucket in region us-west-2")
'''
    
    # Find a good place to insert the syntax helper
    helper_insertion_point = updated_code.find('# List buckets')
    updated_code = updated_code[:helper_insertion_point] + syntax_helper + updated_code[helper_insertion_point:]
    
    # Update help message
    help_message = updated_code.split('def get_help_message()')[1]
    help_message_start = help_message.find('return """')
    help_message_end = help_message.find('"""', help_message_start + 8)
    
    current_help = help_message[help_message_start:help_message_end + 3]
    updated_help = current_help.replace('• `copy file FILE from BUCKET1 to BUCKET2` - ', 
                                       '• `copy file FILE from BUCKET1 to BUCKET2` - Copy a file between buckets\n• `setup replication from BUCKET1 to BUCKET2 in region REGION` - Configure cross-region replication')
    
    updated_code = updated_code.split('def get_help_message()')[0] + 'def get_help_message()' + help_message[:help_message_start] + updated_help + help_message[help_message_end + 3:]
    
    # Write the updated code
    with open('lambda_extract/lambda_function.py', 'w') as f:
        f.write(updated_code)
    
    # Create a new zip file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.write('lambda_extract/lambda_function.py', 'lambda_function.py')
    
    # Get the zip file content
    zip_buffer.seek(0)
    zip_content = zip_buffer.read()
    
    # Update the Lambda function
    try:
        # Update the function code
        response = lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_content,
            Publish=True
        )
        
        print(f"✅ Lambda function updated successfully")
        print(f"Version: {response.get('Version')}")
        
        # Update the function configuration to increase timeout
        lambda_client.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Timeout=300  # 5 minutes
        )
        
        print("✅ Lambda function timeout increased to 5 minutes")
        
        # Clean up
        import shutil
        os.remove('lambda_current.zip')
        shutil.rmtree('lambda_extract')
        
        print("\n✅ Deployment complete!")
        print("The S3 agent now supports setting up cross-region replication.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        # Add replication command to Lambda
        add_replication_command()
    elif len(sys.argv) >= 3:
        # Direct setup of replication
        source_bucket = sys.argv[1]
        destination_bucket = sys.argv[2]
        destination_region = sys.argv[3] if len(sys.argv) > 3 else 'us-west-2'
        setup_s3_replication(source_bucket, destination_bucket, destination_region)
    else:
        print("Usage:")
        print("  python3 s3_replication.py                                      # Add replication command to Lambda")
        print("  python3 s3_replication.py SOURCE_BUCKET DEST_BUCKET [REGION]   # Setup replication directly")