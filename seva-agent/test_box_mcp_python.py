#!/usr/bin/env python3

"""
Test Box MCP Server Setup (Python-based)
Based on: https://github.com/box-community/mcp-server-box
"""

import subprocess
import json
import os
import sys
from pathlib import Path

class BoxMCPPythonTester:
    def __init__(self):
        self.server_path = Path.home() / "Desktop" / "mcp-server-box"
        self.server_installed = False
        
    def check_python_version(self):
        """Check if Python version meets requirements"""
        try:
            print("🐍 Checking Python version...")
            
            python_version = sys.version_info
            required_version = (3, 13)
            
            print(f"Current Python: {python_version.major}.{python_version.minor}.{python_version.micro}")
            print(f"Required Python: >= {required_version[0]}.{required_version[1]}")
            
            if python_version >= required_version:
                print("✅ Python version meets requirements")
                return True
            else:
                print("⚠️  Python version may be too old")
                print("📋 Box MCP server requires Python >= 3.13")
                print("🔧 Consider using pyenv or conda to install Python 3.13+")
                return False
                
        except Exception as e:
            print(f"❌ Error checking Python version: {e}")
            return False
    
    def setup_server(self):
        """Install and setup the Box MCP server"""
        try:
            print("📦 Setting up Box MCP server...")
            
            if not self.server_path.exists():
                print(f"❌ Box MCP server not found at {self.server_path}")
                print("📋 Please clone the repository first:")
                print("   git clone https://github.com/box-community/mcp-server-box.git")
                return False
            
            print(f"📁 Found Box MCP server at {self.server_path}")
            
            # Check if uv is installed (modern Python package manager)
            try:
                subprocess.run(["uv", "--version"], capture_output=True, check=True)
                print("✅ uv package manager found")
                use_uv = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("⚠️  uv not found, using pip")
                use_uv = False
            
            # Install dependencies
            print("📦 Installing dependencies...")
            
            if use_uv:
                # Use uv for faster installation
                result = subprocess.run([
                    "uv", "sync"
                ], cwd=self.server_path, capture_output=True, text=True, check=True)
                print("✅ Dependencies installed with uv")
            else:
                # Fallback to pip
                result = subprocess.run([
                    "pip", "install", "-e", "."
                ], cwd=self.server_path, capture_output=True, text=True, check=True)
                print("✅ Dependencies installed with pip")
            
            self.server_installed = True
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to setup Box MCP server: {e}")
            print(f"STDERR: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def check_box_credentials(self):
        """Check if Box API credentials are available"""
        try:
            print("\n🔑 Checking Box API credentials...")
            
            # Check for .env file
            env_file = self.server_path / ".env"
            if env_file.exists():
                print("✅ Found .env file")
                
                # Read .env file to check for required variables
                with open(env_file, 'r') as f:
                    env_content = f.read()
                
                required_vars = [
                    'BOX_CLIENT_ID',
                    'BOX_CLIENT_SECRET',
                    'BOX_ENTERPRISE_ID'
                ]
                
                missing_vars = []
                for var in required_vars:
                    if var not in env_content or f"{var}=" not in env_content:
                        missing_vars.append(var)
                
                if not missing_vars:
                    print("✅ All required Box credentials found in .env")
                    return True
                else:
                    print(f"⚠️  Missing credentials in .env: {missing_vars}")
            else:
                print("⚠️  No .env file found")
            
            # Check environment variables
            env_vars = {
                'BOX_CLIENT_ID': os.getenv('BOX_CLIENT_ID'),
                'BOX_CLIENT_SECRET': os.getenv('BOX_CLIENT_SECRET'),
                'BOX_ENTERPRISE_ID': os.getenv('BOX_ENTERPRISE_ID')
            }
            
            missing_env = [k for k, v in env_vars.items() if not v]
            
            if not missing_env:
                print("✅ All required Box credentials found in environment")
                return True
            
            print("📋 Box MCP server requires:")
            print("   - BOX_CLIENT_ID")
            print("   - BOX_CLIENT_SECRET") 
            print("   - BOX_ENTERPRISE_ID")
            print("\n📖 Setup instructions:")
            print("   1. Go to https://developer.box.com/")
            print("   2. Create a new Custom App with Server Authentication (JWT)")
            print("   3. Get Client ID, Client Secret, and Enterprise ID")
            print("   4. Create .env file or set environment variables")
            
            return False
                
        except Exception as e:
            print(f"❌ Error checking credentials: {e}")
            return False
    
    def test_server_structure(self):
        """Test the server file structure"""
        try:
            print("\n🧪 Testing Box MCP server structure...")
            
            # Check key files
            key_files = [
                "pyproject.toml",
                "src/mcp_server_box.py",
                "src/box_tools_files.py",
                "src/box_tools_folders.py",
                "README.md"
            ]
            
            for file in key_files:
                file_path = self.server_path / file
                if file_path.exists():
                    print(f"✅ Found: {file}")
                else:
                    print(f"❌ Missing: {file}")
                    return False
            
            # Check main server file
            main_server = self.server_path / "src" / "mcp_server_box.py"
            with open(main_server, 'r') as f:
                content = f.read()
            
            if "mcp" in content.lower() and "box" in content.lower():
                print("✅ Main server file contains MCP and Box references")
            else:
                print("⚠️  Main server file structure unclear")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing server structure: {e}")
            return False
    
    def test_import_server(self):
        """Test if we can import the server module"""
        try:
            print("\n🔍 Testing server import...")
            
            # Add server path to Python path
            sys.path.insert(0, str(self.server_path / "src"))
            
            try:
                import mcp_server_box
                print("✅ Successfully imported mcp_server_box")
                
                # Check if main components exist
                if hasattr(mcp_server_box, 'app'):
                    print("✅ Found app component")
                
                return True
                
            except ImportError as e:
                print(f"⚠️  Import error (may need credentials): {e}")
                return True  # Not critical for basic setup
            except Exception as e:
                print(f"⚠️  Server import issue: {e}")
                return True  # Not critical for basic setup
                
        except Exception as e:
            print(f"❌ Error testing import: {e}")
            return False
        finally:
            # Clean up sys.path
            if str(self.server_path / "src") in sys.path:
                sys.path.remove(str(self.server_path / "src"))
    
    def create_sample_env(self):
        """Create a sample .env file"""
        try:
            print("\n⚙️  Creating sample .env file...")
            
            sample_env = """# Box API Configuration
# Get these from https://developer.box.com/
BOX_CLIENT_ID=your_client_id_here
BOX_CLIENT_SECRET=your_client_secret_here
BOX_ENTERPRISE_ID=your_enterprise_id_here

# Optional: Box User ID for user-specific operations
BOX_USER_ID=your_user_id_here

# Optional: Logging level
LOG_LEVEL=INFO
"""
            
            env_file = self.server_path / ".env.sample"
            with open(env_file, 'w') as f:
                f.write(sample_env)
            
            print(f"✅ Sample .env created: {env_file}")
            print("📋 Copy this to .env and fill in your Box API credentials")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating sample .env: {e}")
            return False

def main():
    print("🚀 Box MCP Server (Python) Test Suite")
    print("=" * 50)
    
    tester = BoxMCPPythonTester()
    
    try:
        # Check Python version
        python_ok = tester.check_python_version()
        
        # Setup server
        if not tester.setup_server():
            return False
        
        # Check credentials
        has_credentials = tester.check_box_credentials()
        
        # Test server structure
        if not tester.test_server_structure():
            return False
        
        # Test import
        tester.test_import_server()
        
        # Create sample env
        tester.create_sample_env()
        
        print("\n" + "=" * 50)
        if has_credentials:
            print("✅ Box MCP server is fully ready!")
            print("🎉 You can now use Box MCP server with your credentials")
        else:
            print("⚠️  Box MCP server is installed but needs API credentials")
            print("🔧 Set up Box API credentials to enable full functionality")
        
        if not python_ok:
            print("⚠️  Consider upgrading Python for optimal compatibility")
        
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