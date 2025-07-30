#!/usr/bin/env python3

"""
MCP Filesystem Integration for S3 Agent
Uses the official MCP filesystem server
"""

import subprocess
import json
import os
from typing import Dict, Any, List

class MCPFilesystem:
    def __init__(self):
        self.server_process = None
        
    def start_server(self):
        """Start the MCP filesystem server"""
        try:
            # Install the MCP filesystem server if not already installed
            subprocess.run([
                "npx", "-y", "@modelcontextprotocol/server-filesystem", 
                "--help"
            ], capture_output=True, check=True)
            
            print("✅ MCP Filesystem server is available")
            return True
        except subprocess.CalledProcessError:
            print("❌ MCP Filesystem server not available. Installing...")
            try:
                subprocess.run([
                    "npm", "install", "-g", "@modelcontextprotocol/server-filesystem"
                ], check=True)
                print("✅ MCP Filesystem server installed")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install MCP Filesystem server: {e}")
                return False
    
    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read file using MCP filesystem server"""
        try:
            # Expand user path
            file_path = os.path.expanduser(file_path)
            
            # Use MCP server to read file
            result = subprocess.run([
                "npx", "@modelcontextprotocol/server-filesystem",
                "read_file", file_path
            ], capture_output=True, text=True, check=True)
            
            return {
                "success": True,
                "content": result.stdout,
                "path": file_path
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Failed to read file: {e.stderr}",
                "path": file_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }
    
    def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Write file using MCP filesystem server"""
        try:
            # Expand user path
            file_path = os.path.expanduser(file_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Use MCP server to write file
            result = subprocess.run([
                "npx", "@modelcontextprotocol/server-filesystem",
                "write_file", file_path
            ], input=content, capture_output=True, text=True, check=True)
            
            return {
                "success": True,
                "path": file_path,
                "message": "File written successfully"
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Failed to write file: {e.stderr}",
                "path": file_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }
    
    def list_directory(self, dir_path: str) -> Dict[str, Any]:
        """List directory using MCP filesystem server"""
        try:
            # Expand user path
            dir_path = os.path.expanduser(dir_path)
            
            # Use MCP server to list directory
            result = subprocess.run([
                "npx", "@modelcontextprotocol/server-filesystem",
                "list_directory", dir_path
            ], capture_output=True, text=True, check=True)
            
            # Parse the output
            files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            return {
                "success": True,
                "files": files,
                "path": dir_path,
                "count": len(files)
            }
        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Failed to list directory: {e.stderr}",
                "path": dir_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": dir_path
            }
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        file_path = os.path.expanduser(file_path)
        return os.path.exists(file_path)
    
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
                "is_directory": os.path.isdir(file_path)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }

# Global MCP filesystem instance
mcp_fs = MCPFilesystem()

if __name__ == "__main__":
    # Test the MCP filesystem integration
    print("🧪 Testing MCP Filesystem Integration")
    
    if mcp_fs.start_server():
        print("✅ MCP Filesystem server started successfully")
        
        # Test file operations
        test_file = "~/Desktop/test_mcp.txt"
        
        # Test write
        result = mcp_fs.write_file(test_file, "Hello from MCP Filesystem!")
        print(f"Write test: {result}")
        
        # Test read
        result = mcp_fs.read_file(test_file)
        print(f"Read test: {result}")
        
        # Test file info
        result = mcp_fs.get_file_info(test_file)
        print(f"File info: {result}")
        
        # Test list directory
        result = mcp_fs.list_directory("~/Desktop")
        print(f"List directory: {result}")
    else:
        print("❌ Failed to start MCP Filesystem server")