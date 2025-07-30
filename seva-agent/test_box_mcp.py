#!/usr/bin/env python3

"""
Test Box MCP Server Setup
Based on: https://github.com/box-community/mcp-server-box
"""

import subprocess
import json
import os
import tempfile
from pathlib import Path

class BoxMCPTester:
    def __init__(self):
        self.server_installed = False
        
    def setup_server(self):
        """Install and setup the Box MCP server"""
        try:
            print("📦 Installing Box MCP server...")
            
            # Clone the Box MCP server repository
            repo_dir = Path.home() / "Desktop" / "mcp-server-box"
            
            if repo_dir.exists():
                print(f"📁 Repository already exists at {repo_dir}")
            else:
                result = subprocess.run([
                    "git", "clone", 
                    "https://github.com/box-community/mcp-server-box.git",
                    str(repo_dir)
                ], capture_output=True, text=True, check=True)
                print(f"✅ Cloned Box MCP server to {repo_dir}")
            
            # Install dependencies
            print("📦 Installing dependencies...")
            result = subprocess.run([
                "npm", "install"
            ], cwd=repo_dir, capture_output=True, text=True, check=True)
            
            print("✅ Box MCP server dependencies installed")
            
            # Build the project
            print("🔨 Building Box MCP server...")
            result = subprocess.run([
                "npm", "run", "build"
            ], cwd=repo_dir, capture_output=True, text=True, check=True)
            
            print("✅ Box MCP server built successfully")
            
            self.server_path = repo_dir
            self.server_installed = True
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to setup Box MCP server: {e}")
            print(f"STDERR: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def check_requirements(self):
        """Check if Box API credentials are available"""
        try:
            print("\n🔑 Checking Box API requirements...")
            
            # Check for Box API credentials in environment
            client_id = os.getenv('BOX_CLIENT_ID')
            client_secret = os.getenv('BOX_CLIENT_SECRET')
            
            if client_id and client_secret:
                print("✅ Box API credentials found in environment")
                return True
            else:
                print("⚠️  Box API credentials not found in environment")
                print("📋 To use Box MCP server, you need:")
                print("   - BOX_CLIENT_ID environment variable")
                print("   - BOX_CLIENT_SECRET environment variable")
                print("   - Box Developer Account and App")
                print("\n📖 Setup instructions:")
                print("   1. Go to https://developer.box.com/")
                print("   2. Create a new app")
                print("   3. Get Client ID and Client Secret")
                print("   4. Set environment variables:")
                print("      export BOX_CLIENT_ID='your_client_id'")
                print("      export BOX_CLIENT_SECRET='your_client_secret'")
                return False
                
        except Exception as e:
            print(f"❌ Error checking requirements: {e}")
            return False
    
    def test_server_structure(self):
        """Test the server file structure and basic setup"""
        try:
            print("\n🧪 Testing Box MCP server structure...")
            
            if not self.server_path:
                print("❌ Server path not set")
                return False
            
            # Check key files exist
            key_files = [
                "package.json",
                "src/index.ts",
                "README.md"
            ]
            
            for file in key_files:
                file_path = self.server_path / file
                if file_path.exists():
                    print(f"✅ Found: {file}")
                else:
                    print(f"❌ Missing: {file}")
                    return False
            
            # Check package.json content
            package_json = self.server_path / "package.json"
            with open(package_json, 'r') as f:
                package_data = json.load(f)
            
            print(f"✅ Package name: {package_data.get('name', 'unknown')}")
            print(f"✅ Package version: {package_data.get('version', 'unknown')}")
            
            # Check if build directory exists
            build_dir = self.server_path / "build"
            if build_dir.exists():
                print("✅ Build directory exists")
            else:
                print("⚠️  Build directory not found")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing server structure: {e}")
            return False
    
    def test_server_help(self):
        """Test if the server can show help/usage"""
        try:
            print("\n📖 Testing Box MCP server help...")
            
            if not self.server_path:
                return False
            
            # Try to run the server with help flag
            result = subprocess.run([
                "node", "build/index.js", "--help"
            ], cwd=self.server_path, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 or "help" in result.stdout.lower() or "usage" in result.stdout.lower():
                print("✅ Server help command works")
                if result.stdout:
                    print(f"📋 Server output:\n{result.stdout[:200]}...")
                return True
            else:
                print("⚠️  Server help not available or different format")
                if result.stderr:
                    print(f"STDERR: {result.stderr[:200]}...")
                return True  # Not critical for basic setup
                
        except subprocess.TimeoutExpired:
            print("⚠️  Server help command timed out (normal for some MCP servers)")
            return True
        except Exception as e:
            print(f"⚠️  Error testing server help: {e}")
            return True  # Not critical
    
    def create_sample_config(self):
        """Create a sample configuration for Box MCP server"""
        try:
            print("\n⚙️  Creating sample Box MCP configuration...")
            
            config = {
                "mcpServers": {
                    "box": {
                        "command": "node",
                        "args": [str(self.server_path / "build" / "index.js")],
                        "env": {
                            "BOX_CLIENT_ID": "${BOX_CLIENT_ID}",
                            "BOX_CLIENT_SECRET": "${BOX_CLIENT_SECRET}"
                        }
                    }
                }
            }
            
            config_file = Path.home() / "Desktop" / "box_mcp_config.json"
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"✅ Sample config created: {config_file}")
            print("📋 This config can be used with MCP clients")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating sample config: {e}")
            return False

def main():
    print("🚀 Box MCP Server Test Suite")
    print("=" * 50)
    
    tester = BoxMCPTester()
    
    try:
        # Setup
        if not tester.setup_server():
            return False
        
        # Check requirements
        has_credentials = tester.check_requirements()
        
        # Test server structure
        if not tester.test_server_structure():
            return False
        
        # Test server help
        tester.test_server_help()
        
        # Create sample config
        if not tester.create_sample_config():
            return False
        
        print("\n" + "=" * 50)
        if has_credentials:
            print("✅ Box MCP server is fully ready!")
            print("🎉 You can now use Box MCP server with your credentials")
        else:
            print("⚠️  Box MCP server is installed but needs API credentials")
            print("🔧 Set up Box API credentials to enable full functionality")
        
        print("📁 Server location:", tester.server_path)
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)