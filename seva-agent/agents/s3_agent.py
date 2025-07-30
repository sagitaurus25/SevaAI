"""
S3 Service Agent
"""
from .base_agent import BaseAgent
from typing import Dict, List, Any
import re
import json

class S3Agent(BaseAgent):
    def get_service_name(self) -> str:
        return "s3"
    
    def get_capabilities(self) -> List[str]:
        return [
            "list_buckets",
            "list_objects", 
            "create_bucket",
            "delete_bucket",
            "upload_file",
            "download_file",
            "move_object",
            "copy_object",
            "get_bucket_size",
            "analyze_storage_class",
            "delete_object",
            "set_bucket_policy",
            "remove_bucket_policy",
            "make_bucket_public",
            "make_bucket_private",
            "show_public_access_block"
        ]
    
    def can_handle(self, command: str) -> bool:
        s3_keywords = ["s3", "bucket", "object", "upload", "download", "move", "copy", "size", "storage", "info", "test", "access", "policy", "delete", "set", "make", "public", "private", "remove", "block"]
        return any(keyword in command.lower() for keyword in s3_keywords)
    
    def execute(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        command_lower = command.lower()
        
        try:
            if "list" in command_lower and "bucket" in command_lower:
                if "objects" in command_lower or "contents" in command_lower:
                    bucket_name = self._extract_bucket_name(command)
                    if bucket_name:
                        return self._list_objects(bucket_name)
                    else:
                        return {"error": "Bucket name not found"}
                else:
                    return self._list_buckets()
            
            elif "show" in command_lower and "objects" in command_lower and "bucket" in command_lower:
                bucket_name = self._extract_bucket_name(command)
                if bucket_name:
                    return self._list_objects(bucket_name)
                else:
                    return {"error": "Bucket name not found"}
            
            elif "create" in command_lower and "bucket" in command_lower:
                bucket_name = self._extract_bucket_name(command)
                if bucket_name:
                    return self._create_bucket(bucket_name)
                else:
                    return {"error": "Please specify bucket name"}
            
            elif "size" in command_lower and "bucket" in command_lower:
                bucket_name = self._extract_bucket_name(command)
                if bucket_name:
                    return self._get_bucket_size(bucket_name)
                else:
                    return {"error": "Please specify bucket name"}
            
            elif "policy" in command_lower and "bucket" in command_lower:
                bucket_name = self._extract_bucket_name(command)
                if bucket_name:
                    return self._get_bucket_policy(bucket_name)
                else:
                    return {"error": "Please specify bucket name"}
            
            elif "delete" in command_lower and "object" in command_lower:
                return self._delete_object(command)
            
            else:
                return {"error": f"S3 command not recognized: {command}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_bucket_name(self, command: str) -> str:
        words = command.split()
        
        # Handle "objects in my bucket bucketname" pattern
        for i, word in enumerate(words):
            if word.lower() == "bucket" and i + 1 < len(words):
                next_word = words[i + 1]
                if next_word.lower() not in ['in', 'from', 'to', 'with', 'for', 'policy', 'size', 'info']:
                    return next_word
        
        # Handle "in bucketname" or "in my bucket bucketname"
        for i, word in enumerate(words):
            if word.lower() == "in":
                # Look for bucket name after "in"
                for j in range(i + 1, len(words)):
                    candidate = words[j]
                    if candidate.lower() not in ['my', 'bucket', 'the', 'a', 'an', 'objects']:
                        return candidate
        
        # Look for known bucket patterns
        for word in words:
            if any(pattern in word for pattern in ["tarbucket", "aws-agent", "tar-"]):
                return word
        
        # Last resort: find any word that looks like a bucket name
        for word in reversed(words):
            if (len(word) > 3 and 
                not word.startswith('-') and 
                word.lower() not in ['show', 'list', 'get', 'bucket', 'buckets', 'objects', 'policy', 'size', 'info', 'in', 'from', 'to', 'my', 'the']):
                return word
        
        return None
    
    def _list_buckets(self) -> Dict[str, Any]:
        s3 = self.session.client('s3')
        response = s3.list_buckets()
        
        buckets = []
        for bucket in response['Buckets']:
            buckets.append({
                "name": bucket['Name'],
                "created": bucket['CreationDate'].isoformat()
            })
        
        return {
            "service": "s3",
            "operation": "list_buckets",
            "result": buckets,
            "count": len(buckets)
        }
    
    def _list_objects(self, bucket_name: str) -> Dict[str, Any]:
        s3 = self.session.client('s3')
        response = s3.list_objects_v2(Bucket=bucket_name)
        
        objects = []
        if 'Contents' in response:
            for obj in response['Contents']:
                objects.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "modified": obj['LastModified'].isoformat()
                })
        
        return {
            "service": "s3",
            "operation": "list_objects",
            "bucket": bucket_name,
            "result": objects,
            "count": len(objects)
        }
    
    def _create_bucket(self, bucket_name: str) -> Dict[str, Any]:
        s3 = self.session.client('s3')
        s3.create_bucket(Bucket=bucket_name)
        
        return {
            "service": "s3",
            "operation": "create_bucket",
            "bucket": bucket_name,
            "result": "success"
        }
    
    def _get_bucket_size(self, bucket_name: str) -> Dict[str, Any]:
        try:
            s3 = self.session.client('s3')
            try:
                location = s3.get_bucket_location(Bucket=bucket_name)
                bucket_region = location['LocationConstraint'] or 'us-east-1'
                s3 = self.session.client('s3', region_name=bucket_region)
            except:
                pass
            
            response = s3.list_objects_v2(Bucket=bucket_name)
            
            total_size = 0
            object_count = 0
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    total_size += obj['Size']
                    object_count += 1
            
            size_gb = total_size / (1024 * 1024 * 1024)
            
            return {
                "service": "s3",
                "operation": "get_bucket_size",
                "bucket": bucket_name,
                "result": {
                    "total_size_gb": round(size_gb, 2),
                    "object_count": object_count
                }
            }
        except Exception as e:
            return {"error": f"Failed to get bucket size: {str(e)}"}
    
    def _get_bucket_policy(self, bucket_name: str) -> Dict[str, Any]:
        try:
            s3 = self.session.client('s3')
            try:
                location = s3.get_bucket_location(Bucket=bucket_name)
                bucket_region = location['LocationConstraint'] or 'us-east-1'
                s3 = self.session.client('s3', region_name=bucket_region)
            except:
                pass
            
            try:
                response = s3.get_bucket_policy(Bucket=bucket_name)
                policy = json.loads(response['Policy'])
                
                return {
                    "service": "s3",
                    "operation": "get_bucket_policy",
                    "bucket": bucket_name,
                    "result": {
                        "has_policy": True,
                        "policy": policy
                    }
                }
            except Exception as e:
                if 'NoSuchBucketPolicy' in str(e):
                    return {
                        "service": "s3",
                        "operation": "get_bucket_policy",
                        "bucket": bucket_name,
                        "result": {
                            "has_policy": False,
                            "message": "No bucket policy configured"
                        }
                    }
                else:
                    raise e
                    
        except Exception as e:
            return {"error": f"Failed to get bucket policy: {str(e)}"}
    
    def _delete_object(self, command: str) -> Dict[str, Any]:
        try:
            words = command.split()
            
            object_name = None
            for i, word in enumerate(words):
                if word.lower() == "object" and i + 1 < len(words):
                    object_name = words[i + 1]
                    break
            
            if not object_name:
                return {"error": "Object name not found"}
            
            bucket_name = self._extract_bucket_name(command)
            if not bucket_name:
                return {"error": "Bucket name not found"}
            
            s3 = self.session.client('s3')
            try:
                location = s3.get_bucket_location(Bucket=bucket_name)
                bucket_region = location['LocationConstraint'] or 'us-east-1'
                s3 = self.session.client('s3', region_name=bucket_region)
            except:
                pass
            
            s3.delete_object(Bucket=bucket_name, Key=object_name)
            
            return {
                "service": "s3",
                "operation": "delete_object",
                "bucket": bucket_name,
                "key": object_name,
                "result": "Object deleted successfully"
            }
            
        except Exception as e:
            return {"error": f"Failed to delete object: {str(e)}"}