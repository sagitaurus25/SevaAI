#!/usr/bin/env python3

"""
Simple Filesystem Integration for S3 Agent
Direct Python file operations
"""

import os
import shutil
from typing import Dict, Any

class SimpleFilesystem:
    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read file content"""
        try:
            file_path = os.path.expanduser(file_path)
            
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "path": file_path
                }
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "path": file_path,
                "size": len(content)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }
    
    def read_binary_file(self, file_path: str) -> Dict[str, Any]:
        """Read binary file content"""
        try:
            file_path = os.path.expanduser(file_path)
            
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "path": file_path
                }
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "path": file_path,
                "size": len(content)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }
    
    def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Write text content to file"""
        try:
            file_path = os.path.expanduser(file_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "path": file_path,
                "size": len(content),
                "message": "File written successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }
    
    def write_binary_file(self, file_path: str, content: bytes) -> Dict[str, Any]:
        """Write binary content to file"""
        try:
            file_path = os.path.expanduser(file_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            return {
                "success": True,
                "path": file_path,
                "size": len(content),
                "message": "Binary file written successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information"""
        try:
            file_path = os.path.expanduser(file_path)
            
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": "File not found",
                    "path": file_path
                }
            
            stat = os.stat(file_path)
            
            return {
                "success": True,
                "path": file_path,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "is_file": os.path.isfile(file_path),
                "is_directory": os.path.isdir(file_path),
                "readable": os.access(file_path, os.R_OK),
                "writable": os.access(file_path, os.W_OK)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }
    
    def list_directory(self, dir_path: str) -> Dict[str, Any]:
        """List directory contents"""
        try:
            dir_path = os.path.expanduser(dir_path)
            
            if not os.path.exists(dir_path):
                return {
                    "success": False,
                    "error": "Directory not found",
                    "path": dir_path
                }
            
            if not os.path.isdir(dir_path):
                return {
                    "success": False,
                    "error": "Path is not a directory",
                    "path": dir_path
                }
            
            files = []
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                stat = os.stat(item_path)
                files.append({
                    "name": item,
                    "path": item_path,
                    "size": stat.st_size,
                    "is_file": os.path.isfile(item_path),
                    "is_directory": os.path.isdir(item_path)
                })
            
            return {
                "success": True,
                "path": dir_path,
                "files": files,
                "count": len(files)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": dir_path
            }

# Global filesystem instance
fs = SimpleFilesystem()

if __name__ == "__main__":
    # Test the filesystem integration
    print("🧪 Testing Simple Filesystem Integration")
    
    test_file = "~/Desktop/test_fs.txt"
    
    # Test write
    result = fs.write_file(test_file, "Hello from Simple Filesystem!")
    print(f"Write test: {result}")
    
    # Test read
    result = fs.read_file(test_file)
    print(f"Read test: {result}")
    
    # Test file info
    result = fs.get_file_info(test_file)
    print(f"File info: {result}")
    
    # Test list directory
    result = fs.list_directory("~/Desktop")
    print(f"List directory: Found {result.get('count', 0)} items")
    
    print("✅ Simple Filesystem integration working!")