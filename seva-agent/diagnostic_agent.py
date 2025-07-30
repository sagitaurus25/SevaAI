"""
Diagnostic Agent - Analyze IAM and S3 permissions
"""
import boto3
import json
from typing import Dict, Any

def diagnose_permissions(session: boto3.Session) -> Dict[str, Any]:
    """Comprehensive permission diagnosis"""
    results = {}
    
    # 1. Check current identity
    try:
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        results['identity'] = {
            'user_id': identity.get('UserId'),
            'account': identity.get('Account'),
            'arn': identity.get('Arn'),
            'type': 'root' if ':root' in identity.get('Arn', '') else 'iam_user'
        }
    except Exception as e:
        results['identity'] = {'error': str(e)}
    
    # 2. Test basic S3 permissions
    s3_tests = {}
    s3 = session.client('s3')
    
    # Test list buckets
    try:
        response = s3.list_buckets()
        s3_tests['list_buckets'] = {'success': True, 'count': len(response['Buckets'])}
    except Exception as e:
        s3_tests['list_buckets'] = {'success': False, 'error': str(e)}
    
    # Test specific bucket operations
    test_bucket = 'tar-books25'
    
    # Test head bucket
    try:
        s3.head_bucket(Bucket=test_bucket)
        s3_tests['head_bucket'] = {'success': True}
    except Exception as e:
        s3_tests['head_bucket'] = {'success': False, 'error': str(e)}
    
    # Test get bucket location
    try:
        location = s3.get_bucket_location(Bucket=test_bucket)
        s3_tests['get_bucket_location'] = {'success': True, 'region': location.get('LocationConstraint')}
    except Exception as e:
        s3_tests['get_bucket_location'] = {'success': False, 'error': str(e)}
    
    # Test list objects
    try:
        response = s3.list_objects_v2(Bucket=test_bucket, MaxKeys=1)
        s3_tests['list_objects'] = {'success': True, 'has_contents': 'Contents' in response}
    except Exception as e:
        s3_tests['list_objects'] = {'success': False, 'error': str(e)}
    
    # Test get bucket policy
    try:
        policy = s3.get_bucket_policy(Bucket=test_bucket)
        s3_tests['get_bucket_policy'] = {'success': True, 'has_policy': True}
    except Exception as e:
        if 'NoSuchBucketPolicy' in str(e):
            s3_tests['get_bucket_policy'] = {'success': True, 'has_policy': False}
        else:
            s3_tests['get_bucket_policy'] = {'success': False, 'error': str(e)}
    
    results['s3_permissions'] = s3_tests
    
    # 3. Test IAM permissions (if not root)
    if results['identity'].get('type') == 'iam_user':
        iam_tests = {}
        iam = session.client('iam')
        
        try:
            username = results['identity']['arn'].split(':user/')[1]
            
            # Test list attached user policies
            try:
                policies = iam.list_attached_user_policies(UserName=username)
                iam_tests['list_attached_policies'] = {'success': True, 'count': len(policies['AttachedPolicies'])}
            except Exception as e:
                iam_tests['list_attached_policies'] = {'success': False, 'error': str(e)}
            
            # Test get user policy
            try:
                inline_policies = iam.list_user_policies(UserName=username)
                iam_tests['list_inline_policies'] = {'success': True, 'count': len(inline_policies['PolicyNames'])}
            except Exception as e:
                iam_tests['list_inline_policies'] = {'success': False, 'error': str(e)}
                
        except Exception as e:
            iam_tests['general'] = {'error': str(e)}
            
        results['iam_permissions'] = iam_tests
    else:
        results['iam_permissions'] = {'note': 'Root user - has all permissions by default'}
    
    # 4. Check AWS region
    results['session_info'] = {
        'region': session.region_name,
        'profile': session.profile_name
    }
    
    return results

def format_diagnosis(results: Dict[str, Any]) -> str:
    """Format diagnosis results for display"""
    output = "🔍 AWS Permissions Diagnosis:\n\n"
    
    # Identity
    identity = results.get('identity', {})
    if 'error' not in identity:
        output += f"👤 Identity: {identity.get('type', 'unknown')}\n"
        output += f"   ARN: {identity.get('arn', 'unknown')}\n"
        output += f"   Account: {identity.get('account', 'unknown')}\n\n"
    else:
        output += f"❌ Identity Error: {identity['error']}\n\n"
    
    # S3 Permissions
    s3_perms = results.get('s3_permissions', {})
    output += "📦 S3 Permission Tests:\n"
    for test, result in s3_perms.items():
        status = "✅" if result.get('success') else "❌"
        output += f"   {status} {test}: "
        if result.get('success'):
            if 'count' in result:
                output += f"{result['count']} items"
            elif 'region' in result:
                output += f"region: {result['region']}"
            elif 'has_contents' in result:
                output += f"has objects: {result['has_contents']}"
            elif 'has_policy' in result:
                output += f"has policy: {result['has_policy']}"
            else:
                output += "success"
        else:
            output += f"ERROR: {result.get('error', 'unknown')}"
        output += "\n"
    
    # IAM Permissions
    iam_perms = results.get('iam_permissions', {})
    output += "\n🔐 IAM Permission Tests:\n"
    if 'note' in iam_perms:
        output += f"   ℹ️  {iam_perms['note']}\n"
    else:
        for test, result in iam_perms.items():
            if test == 'general':
                output += f"   ❌ General Error: {result.get('error')}\n"
            else:
                status = "✅" if result.get('success') else "❌"
                output += f"   {status} {test}: "
                if result.get('success'):
                    output += f"{result.get('count', 0)} items"
                else:
                    output += f"ERROR: {result.get('error', 'unknown')}"
                output += "\n"
    
    # Session Info
    session_info = results.get('session_info', {})
    output += f"\n⚙️  Session: Region={session_info.get('region')}, Profile={session_info.get('profile')}\n"
    
    return output

if __name__ == "__main__":
    # Test the diagnosis
    import subprocess
    
    def get_aws_credentials():
        try:
            result = subprocess.run(['aws', 'configure', 'get', 'aws_access_key_id'], capture_output=True, text=True)
            access_key = result.stdout.strip()
            result = subprocess.run(['aws', 'configure', 'get', 'aws_secret_access_key'], capture_output=True, text=True)
            secret_key = result.stdout.strip()
            result = subprocess.run(['aws', 'configure', 'get', 'region'], capture_output=True, text=True)
            region = result.stdout.strip() or 'us-east-1'
            return access_key, secret_key, region
        except:
            return None, None, None
    
    access_key, secret_key, region = get_aws_credentials()
    session = boto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
    
    results = diagnose_permissions(session)
    print(format_diagnosis(results))