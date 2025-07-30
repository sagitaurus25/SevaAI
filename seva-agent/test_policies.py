#!/usr/bin/env python3

"""
Test script for S3 bucket policies
"""

def test_bucket_policies():
    """Test various bucket policy commands"""
    
    test_commands = [
        # Basic policy operations
        "make bucket public tar-trial-2025",
        "make bucket private tar-trial-2025", 
        "set bucket policy tar-trial-2025 public-read",
        "set bucket policy tar-trial-2025 https-only",
        "get bucket policy tar-trial-2025",
        "remove bucket policy tar-trial-2025",
        
        # IAM operations
        "grant s3 permissions",
        "list iam users",
        "list iam roles",
        
        # Analytics
        "get bucket size tar-trial-2025",
        "analyze storage class tar-trial-2025",
        
        # Object operations
        "show objects in bucket tar-trial-2025",
        "delete object test.txt in bucket tar-trial-2025"
    ]
    
    print("🧪 S3 & IAM Policy Test Commands:")
    print("=" * 50)
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"{i:2d}. {cmd}")
    
    print("\n" + "=" * 50)
    print("Copy and paste these commands one by one into the web interface at http://localhost:8097")
    print("Each command will test different policy and permission scenarios.")

if __name__ == "__main__":
    test_bucket_policies()