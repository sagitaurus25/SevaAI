import json
import boto3
from typing import Dict, Any

ec2_client = boto3.client('ec2')

def lambda_handler(event, context):
    """EC2 Service Lambda - Handles all EC2 operations"""
    try:
        request = event.get('request', '').lower()
        operation = event.get('operation', '')
        parameters = event.get('parameters', {})
        
        if 'list' in request and 'instance' in request:
            return list_instances()
        elif 'start' in request:
            instance_name = extract_instance_name(request)
            instance_id = parameters.get('instance_id', extract_instance_id(request))
            return start_instance(instance_id, instance_name)
        elif 'stop' in request:
            instance_name = extract_instance_name(request)
            instance_id = parameters.get('instance_id', extract_instance_id(request))
            return stop_instance(instance_id, instance_name)
        elif 'reboot' in request:
            instance_name = extract_instance_name(request)
            instance_id = parameters.get('instance_id', extract_instance_id(request))
            return reboot_instance(instance_id, instance_name)
        elif 'recreate' in request:
            instance_name = extract_instance_name(request)
            return recreate_instance(instance_name)
        elif ('describe' in request or 'details' in request or 'show' in request) and not ('key' in request and 'pair' in request):
            instance_name = extract_instance_name(request)
            instance_id = parameters.get('instance_id', extract_instance_id(request))
            return describe_instance(instance_id, instance_name)
        elif 'security' in request and 'group' in request:
            return list_security_groups()
        elif ('key' in request and 'pair' in request) or 'key pairs' in request:
            return list_key_pairs()
        elif 'vpc' in request:
            return list_vpcs()
        else:
            return {
                'error': 'EC2 operation not recognized',
                'supported_operations': [
                    'List all instances',
                    'Start instance i-1234567890abcdef0',
                    'Stop instance i-1234567890abcdef0',
                    'Reboot instance i-1234567890abcdef0',
                    'Describe instance i-1234567890abcdef0',
                    'List security groups',
                    'List key pairs'
                ]
            }
            
    except Exception as e:
        return {'error': f'EC2 service error: {str(e)}'}

def list_instances():
    """List all EC2 instances"""
    try:
        response = ec2_client.describe_instances()
        instances = []
        follow_up_questions = []
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                # Get instance name from tags
                name = 'Unnamed'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break
                
                instance_id = instance['InstanceId']
                state = instance['State']['Name']
                display_name = f"{name} ({instance_id})"
                instances.append(display_name)
                
                # Check if instance has root volume issues
                has_root_volume = True
                try:
                    if not instance.get('BlockDeviceMappings'):
                        has_root_volume = False
                except:
                    pass
                
                # Generate context-aware follow-up questions based on instance state
                follow_up_questions.append(f"Show details of {name}")
                
                if not has_root_volume or state == 'terminated':
                    follow_up_questions.append(f"Recreate {name}")
                elif state == 'stopped':
                    follow_up_questions.append(f"Start {name}")
                elif state == 'running':
                    follow_up_questions.extend([
                        f"Stop {name}",
                        f"Reboot {name}"
                    ])
                elif state == 'stopping':
                    follow_up_questions.append(f"Start {name} (when stopped)")
                elif state == 'pending':
                    follow_up_questions.append(f"Stop {name} (when running)")
        
        return {
            'instances': instances,
            'count': len(instances),
            'follow_up_questions': follow_up_questions[:12]  # Limit to 12 questions
        }
    except Exception as e:
        return {'error': f'Failed to list instances: {str(e)}'}

def start_instance(instance_id, instance_name=None):
    """Start an EC2 instance"""
    if not instance_id and not instance_name:
        return {'error': 'Instance ID or name is required'}
    
    try:
        if instance_name and not instance_id:
            instance_id = find_instance_id_by_name(instance_name)
            if not instance_id:
                return {'error': f'Instance "{instance_name}" not found'}
        
        response = ec2_client.start_instances(InstanceIds=[instance_id])
        current_state = response['StartingInstances'][0]['CurrentState']['Name']
        
        display_name = instance_name if instance_name else instance_id
        return {'message': f'{display_name} is starting (now {current_state})'}
    except Exception as e:
        display_name = instance_name if instance_name else instance_id
        error_msg = str(e)
        if 'does not have a volume attached at root' in error_msg:
            return {'error': f'{display_name} cannot be started - missing root volume. This instance may need to be recreated.'}
        return {'error': f'Failed to start {display_name}: {error_msg}'}

def stop_instance(instance_id, instance_name=None):
    """Stop an EC2 instance"""
    if not instance_id and not instance_name:
        return {'error': 'Instance ID or name is required'}
    
    try:
        if instance_name and not instance_id:
            instance_id = find_instance_id_by_name(instance_name)
            if not instance_id:
                return {'error': f'Instance "{instance_name}" not found'}
        
        response = ec2_client.stop_instances(InstanceIds=[instance_id])
        current_state = response['StoppingInstances'][0]['CurrentState']['Name']
        
        display_name = instance_name if instance_name else instance_id
        return {'message': f'{display_name} is stopping (now {current_state})'}
    except Exception as e:
        display_name = instance_name if instance_name else instance_id
        error_msg = str(e)
        if 'InvalidInstanceID.NotFound' in error_msg:
            return {'error': f'{display_name} not found - it may have been terminated.'}
        return {'error': f'Failed to stop {display_name}: {error_msg}'}

def reboot_instance(instance_id, instance_name=None):
    """Reboot an EC2 instance"""
    if not instance_id and not instance_name:
        return {'error': 'Instance ID or name is required'}
    
    try:
        if instance_name and not instance_id:
            instance_id = find_instance_id_by_name(instance_name)
            if not instance_id:
                return {'error': f'Instance "{instance_name}" not found'}
        
        ec2_client.reboot_instances(InstanceIds=[instance_id])
        display_name = instance_name if instance_name else instance_id
        return {'message': f'{display_name} is rebooting'}
    except Exception as e:
        display_name = instance_name if instance_name else instance_id
        error_msg = str(e)
        if 'InvalidInstanceID.NotFound' in error_msg:
            return {'error': f'{display_name} not found - it may have been terminated.'}
        elif 'does not have a volume attached at root' in error_msg:
            return {'error': f'{display_name} cannot be rebooted - missing root volume. This instance may need to be recreated.'}
        return {'error': f'Failed to reboot {display_name}: {error_msg}'}

def describe_instance(instance_id, instance_name=None):
    """Get detailed information about an instance"""
    if not instance_id and not instance_name:
        return {'error': 'Instance ID or name is required'}
    
    try:
        if instance_name and not instance_id:
            # Find instance by name
            response = ec2_client.describe_instances()
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name' and tag['Value'].lower() == instance_name.lower():
                            instance_id = instance['InstanceId']
                            break
                    if instance_id:
                        break
                if instance_id:
                    break
        
        if not instance_id:
            return {'error': f'Instance with name "{instance_name}" not found'}
        
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        
        # Get instance name
        name = 'Unnamed'
        for tag in instance.get('Tags', []):
            if tag['Key'] == 'Name':
                name = tag['Value']
                break
        
        return {
            'instance_name': name,
            'instance_id': instance['InstanceId'],
            'state': instance['State']['Name'],
            'instance_type': instance['InstanceType'],
            'public_ip': instance.get('PublicIpAddress', 'None'),
            'private_ip': instance.get('PrivateIpAddress', 'None'),
            'availability_zone': instance['Placement']['AvailabilityZone']
        }
    except Exception as e:
        return {'error': f'Failed to describe instance: {str(e)}'}

def list_security_groups():
    """List all security groups"""
    try:
        response = ec2_client.describe_security_groups()
        groups = [f"{group['GroupName']} ({group['GroupId']})" for group in response['SecurityGroups']]
        
        return {
            'security_groups': groups,
            'count': len(groups)
        }
    except Exception as e:
        return {'error': f'Failed to list security groups: {str(e)}'}

def list_key_pairs():
    """List all key pairs"""
    try:
        response = ec2_client.describe_key_pairs()
        key_pairs = [key_pair['KeyName'] for key_pair in response['KeyPairs']]
        
        return {
            'key_pairs': key_pairs,
            'count': len(key_pairs)
        }
    except Exception as e:
        return {'error': f'Failed to list key pairs: {str(e)}'}

def extract_instance_id(request):
    """Extract instance ID from natural language request"""
    words = request.split()
    for word in words:
        if word.startswith('i-') and len(word) == 19:  # Standard instance ID format
            return word
    return None

def extract_instance_name(request):
    """Extract instance name from natural language request"""
    words = request.split()
    
    # Look for patterns like "Show details of MyInstance", "Start MyInstance", "Stop MyInstance"
    if 'of' in words:
        of_index = words.index('of')
        if of_index + 1 < len(words):
            return words[of_index + 1]
    
    # Look for patterns like "Start MyInstance", "Stop MyInstance", "Reboot MyInstance", "Recreate MyInstance"
    # Check both original case and lowercase
    for action in ['Start', 'Stop', 'Reboot', 'Recreate', 'start', 'stop', 'reboot', 'recreate']:
        if action in words:
            action_index = words.index(action)
            if action_index + 1 < len(words):
                return words[action_index + 1]
    
    return None

def recreate_instance(instance_name):
    """Recreate a problematic instance"""
    if not instance_name:
        return {'error': 'Instance name is required'}
    
    try:
        # Find the problematic instance
        instance_id = find_instance_id_by_name(instance_name)
        if not instance_id:
            return {'error': f'Instance "{instance_name}" not found'}
        
        # Get instance details before terminating
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        instance_type = instance['InstanceType']
        subnet_id = instance.get('SubnetId')
        security_groups = [sg['GroupId'] for sg in instance['SecurityGroups']]
        key_name = instance.get('KeyName')
        
        # Terminate the old instance
        ec2_client.terminate_instances(InstanceIds=[instance_id])
        
        # Launch a new instance with similar configuration
        launch_params = {
            'ImageId': 'ami-0c02fb55956c7d316',  # Amazon Linux 2 AMI
            'InstanceType': instance_type,
            'MinCount': 1,
            'MaxCount': 1,
            'TagSpecifications': [
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': instance_name}
                    ]
                }
            ]
        }
        
        if subnet_id:
            launch_params['SubnetId'] = subnet_id
        if security_groups:
            launch_params['SecurityGroupIds'] = security_groups
        if key_name:
            launch_params['KeyName'] = key_name
        
        new_response = ec2_client.run_instances(**launch_params)
        new_instance_id = new_response['Instances'][0]['InstanceId']
        
        return {
            'message': f'{instance_name} recreated successfully',
            'old_instance_id': instance_id,
            'new_instance_id': new_instance_id,
            'status': 'Instance terminated and new one launched'
        }
        
    except Exception as e:
        return {'error': f'Failed to recreate {instance_name}: {str(e)}'}

def list_vpcs():
    """List all VPCs"""
    try:
        response = ec2_client.describe_vpcs()
        vpcs = []
        for vpc in response['Vpcs']:
            name = 'Unnamed'
            for tag in vpc.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']
                    break
            vpcs.append(f"{name} ({vpc['VpcId']})")
        
        return {
            'vpcs': vpcs,
            'count': len(vpcs)
        }
    except Exception as e:
        return {'error': f'Failed to list VPCs: {str(e)}'}

def find_instance_id_by_name(instance_name):
    """Find instance ID by name tag (case-insensitive)"""
    try:
        response = ec2_client.describe_instances()
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name' and tag['Value'].lower() == instance_name.lower():
                        return instance['InstanceId']
        return None
    except Exception:
        return None