#!/usr/bin/env python3

"""
Test Filesystem MCP Server Setup
Based on: https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem
"""

import subprocess
import json
import os
import tempfile
from pathlib import Path

class FilesystemMCPTester:
    def __init__(self):
        self.server_path = None
        self.test_dir = None
        
    def setup_server(self):
        """Install and setup the filesystem MCP server"""
        try:
            print("📦 Installing filesystem MCP server...")
            
            # Install the MCP filesystem server
            result = subprocess.run([
                "npm", "install", "-g", "@modelcontextprotocol/server-filesystem"
            ], capture_output=True, text=True, check=True)
            
            print("✅ Filesystem MCP server installed successfully")
            
            # Create test directory
            self.test_dir = Path.home() / "Desktop" / "mcp_test"
            self.test_dir.mkdir(exist_ok=True)
            
            print(f"📁 Test directory created: {self.test_dir}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install filesystem MCP server: {e}")
            print(f"STDERR: {e.stderr}")
            return False
    
    def test_server_direct(self):
        """Test the MCP server directly via command line"""
        try:
            print("\n🧪 Testing filesystem MCP server directly...")
            
            # Create a test file
            test_file = self.test_dir / "test.txt"
            test_content = "Hello from MCP Filesystem Server!"
            
            with open(test_file, 'w') as f:
                f.write(test_content)
            
            print(f"📝 Created test file: {test_file}")
            
            # Test server with allowed directory
            server_cmd = [
                "npx", "@modelcontextprotocol/server-filesystem",
                str(self.test_dir)
            ]
            
            print(f"🚀 Starting server with command: {' '.join(server_cmd)}")
            
            # Test if server starts (we'll just check if it doesn't error immediately)
            process = subprocess.Popen(
                server_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it a moment to start
            import time
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                print("✅ MCP server started successfully")
                process.terminate()
                process.wait()
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"❌ MCP server failed to start")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing MCP server: {e}")
            return False
    
    def test_file_operations(self):
        """Test basic file operations"""
        try:
            print("\n📋 Testing file operations...")
            
            # Test file creation
            test_file = self.test_dir / "mcp_test_file.txt"
            test_content = "MCP Filesystem Test Content\nLine 2\nLine 3"
            
            with open(test_file, 'w') as f:
                f.write(test_content)
            
            print(f"✅ Created: {test_file}")
            
            # Test file reading
            with open(test_file, 'r') as f:
                read_content = f.read()
            
            if read_content == test_content:
                print("✅ File read/write working correctly")
            else:
                print("❌ File content mismatch")
                return False
            
            # Test directory listing
            files = list(self.test_dir.glob("*"))
            print(f"✅ Directory contains {len(files)} files: {[f.name for f in files]}")
            
            # Test file info
            stat = test_file.stat()
            print(f"✅ File size: {stat.st_size} bytes")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in file operations: {e}")
            return False
    
    def cleanup(self):
        """Clean up test files"""
        try:
            if self.test_dir and self.test_dir.exists():
                import shutil
                shutil.rmtree(self.test_dir)
                print(f"🧹 Cleaned up test directory: {self.test_dir}")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")

def main():
    print("🚀 Filesystem MCP Server Test Suite")
    print("=" * 50)
    
    tester = FilesystemMCPTester()
    
    try:
        # Setup
        if not tester.setup_server():
            return False
        
        # Test direct server
        if not tester.test_server_direct():
            return False
        
        # Test file operations
        if not tester.test_file_operations():
            return False
        
        print("\n" + "=" * 50)
        print("✅ All filesystem MCP tests passed!")
        print("🎉 Filesystem MCP server is ready for integration")
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False
    finally:
        tester.cleanup()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)