#!/usr/bin/env python3

"""
Live Test for Box MCP Server with Credentials
"""

import subprocess
import sys
import os
from pathlib import Path

class BoxMCPLiveTester:
    def __init__(self):
        self.server_path = Path.home() / "Desktop" / "mcp-server-box"
        
    def test_env_file(self):
        """Test if .env file exists and has required variables"""
        try:
            print("🔍 Checking .env file...")
            
            env_file = self.server_path / ".env"
            if not env_file.exists():
                print("❌ .env file not found")
                return False
            
            with open(env_file, 'r') as f:
                content = f.read()
            
            required_vars = ['BOX_CLIENT_ID', 'BOX_CLIENT_SECRET', 'BOX_ENTERPRISE_ID']
            found_vars = []
            
            for var in required_vars:
                if f"{var}=" in content and not f"{var}=your_" in content:
                    found_vars.append(var)
                    print(f"✅ Found {var}")
                else:
                    print(f"❌ Missing or empty {var}")
            
            return len(found_vars) == len(required_vars)
            
        except Exception as e:
            print(f"❌ Error checking .env: {e}")
            return False
    
    def test_server_import(self):
        """Test importing the server with credentials"""
        try:
            print("\n🐍 Testing server import with credentials...")
            
            # Change to server directory and add to path
            os.chdir(self.server_path)
            sys.path.insert(0, str(self.server_path / "src"))
            
            # Load environment variables
            from dotenv import load_dotenv
            load_dotenv()
            
            print("✅ Environment loaded")
            
            # Try importing the server
            import mcp_server_box
            print("✅ Successfully imported mcp_server_box")
            
            # Check if we can access the app
            if hasattr(mcp_server_box, 'app'):
                print("✅ Found MCP app")
                return True
            else:
                print("⚠️  MCP app not found in expected location")
                return False
                
        except ImportError as e:
            print(f"❌ Import error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        finally:
            # Clean up
            if str(self.server_path / "src") in sys.path:
                sys.path.remove(str(self.server_path / "src"))
    
    def test_server_run(self):
        """Test running the server directly"""
        try:
            print("\n🚀 Testing server execution...")
            
            # Try to run the server with a timeout
            process = subprocess.Popen([
                "python", "src/mcp_server_box.py"
            ], cwd=self.server_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Wait a few seconds to see if it starts
            import time
            time.sleep(3)
            
            if process.poll() is None:
                print("✅ Server started successfully")
                process.terminate()
                process.wait()
                return True
            else:
                stdout, stderr = process.communicate()
                print("❌ Server failed to start")
                if stdout:
                    print(f"STDOUT: {stdout[:300]}")
                if stderr:
                    print(f"STDERR: {stderr[:300]}")
                return False
                
        except Exception as e:
            print(f"❌ Error running server: {e}")
            return False
    
    def test_box_connection(self):
        """Test actual Box API connection"""
        try:
            print("\n📦 Testing Box API connection...")
            
            os.chdir(self.server_path)
            sys.path.insert(0, str(self.server_path / "src"))
            
            from dotenv import load_dotenv
            load_dotenv()
            
            # Try to create a Box client
            from box_ai_agents_toolkit import BoxAIAgentsToolkit
            
            client_id = os.getenv('BOX_CLIENT_ID')
            client_secret = os.getenv('BOX_CLIENT_SECRET')
            enterprise_id = os.getenv('BOX_ENTERPRISE_ID')
            
            if not all([client_id, client_secret, enterprise_id]):
                print("❌ Missing required credentials")
                return False
            
            # Initialize toolkit
            toolkit = BoxAIAgentsToolkit(
                client_id=client_id,
                client_secret=client_secret,
                enterprise_id=enterprise_id
            )
            
            print("✅ Box toolkit initialized")
            
            # Try a simple API call
            try:
                # This should test the connection
                user_info = toolkit.get_current_user()
                print(f"✅ Connected to Box as: {user_info.get('name', 'Unknown')}")
                return True
            except Exception as api_error:
                print(f"⚠️  Box API call failed: {api_error}")
                print("🔧 This might be due to:")
                print("   - Incorrect credentials")
                print("   - App not authorized")
                print("   - Network issues")
                return False
                
        except ImportError as e:
            print(f"❌ Import error: {e}")
            print("🔧 Try: pip install box-ai-agents-toolkit")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
        finally:
            if str(self.server_path / "src") in sys.path:
                sys.path.remove(str(self.server_path / "src"))

def main():
    print("🧪 Box MCP Server Live Test")
    print("=" * 40)
    
    tester = BoxMCPLiveTester()
    
    # Test .env file
    if not tester.test_env_file():
        print("\n❌ .env file test failed")
        return False
    
    # Test server import
    if not tester.test_server_import():
        print("\n❌ Server import test failed")
        return False
    
    # Test server run
    if not tester.test_server_run():
        print("\n❌ Server run test failed")
        return False
    
    # Test Box connection
    if not tester.test_box_connection():
        print("\n⚠️  Box connection test failed (check credentials)")
        return False
    
    print("\n" + "=" * 40)
    print("🎉 All Box MCP tests passed!")
    print("✅ Box MCP server is ready for integration")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)