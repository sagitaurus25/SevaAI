#!/usr/bin/env python3
import os
import subprocess
import sys

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return None

def setup_environment():
    """Set up the Python environment and dependencies"""
    print("📦 Setting up Agent Squad environment...")
    
    # Install Agent Squad
    run_command("pip install 'agent-squad[aws]'", "Installing Agent Squad framework")
    
    # Install additional dependencies
    additional_deps = [
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.23.0", 
        "boto3>=1.26.0",
        "pydantic>=2.0.0"
    ]
    
    for dep in additional_deps:
        run_command(f"pip install '{dep}'", f"Installing {dep}")

def configure_aws_credentials():
    """Configure AWS credentials"""
    print("🔐 Configuring AWS credentials...")
    
    # Check if AWS CLI is configured
    result = run_command("aws sts get-caller-identity", "Checking AWS credentials")
    
    if result:
        print("✅ AWS credentials are configured")
        return True
    else:
        print("❌ AWS credentials not found. Please run: aws configure")
        return False

def setup_directory_structure():
    """Create necessary directory structure"""
    print("📁 Setting up directory structure...")
    
    directories = [
        "src/tools",
        "src/agents", 
        "logs",
        "config"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def create_environment_file():
    """Create .env file with necessary environment variables"""
    print("⚙️ Creating environment configuration...")
    
    env_content = """# SevaAI Agent Squad Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_REGION=us-east-1

# Agent Squad Configuration
AGENT_SQUAD_LOG_LEVEL=INFO
AGENT_SQUAD_MAX_TOKENS=4096
AGENT_SQUAD_TEMPERATURE=0.7

# Knowledge Base Configuration (if available)
KNOWLEDGE_BASE_ID=your-knowledge-base-id
KNOWLEDGE_BASE_REGION=us-east-1

# MCP Server Configuration
MCP_SERVER_PORT=3000
MCP_SERVER_HOST=localhost
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env file")

def test_installation():
    """Test the installation"""
    print("🧪 Testing installation...")
    
    test_script = """
import sys
sys.path.append('src')

try:
    from agent_squad.orchestrator import AgentSquad
    from agent_squad.agents import BedrockLLMAgent, BedrockLLMAgentOptions
    print("✅ Agent Squad import successful")
    
    # Test basic orchestrator creation
    orchestrator = AgentSquad()
    print("✅ Orchestrator creation successful")
    
    print("🎉 Installation test passed!")
    
except Exception as e:
    print(f"❌ Installation test failed: {str(e)}")
    sys.exit(1)
"""
    
    with open('test_install.py', 'w') as f:
        f.write(test_script)
    
    result = run_command("python test_install.py", "Running installation test")
    
    # Clean up test file
    os.remove('test_install.py')
    
    return result is not None

def create_startup_script():
    """Create startup script for the enhanced backend"""
    print("🚀 Creating startup script...")
    
    startup_content = """#!/bin/bash
# SevaAI Agent Squad Startup Script

echo "🤖 Starting SevaAI Agent Squad..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Environment variables loaded"
fi

# Check AWS credentials
echo "🔐 Checking AWS credentials..."
aws sts get-caller-identity > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ AWS credentials verified"
else
    echo "❌ AWS credentials not found. Please run: aws configure"
    exit 1
fi

# Start the enhanced backend
echo "🚀 Starting enhanced backend server..."
cd /Users/tar/Desktop/SevaAI/aws-agent-mvp/backend
python app_enhanced.py

echo "📊 SevaAI Agent Squad is running on http://localhost:8085"
"""
    
    with open('start_seva_agent_squad.sh', 'w') as f:
        f.write(startup_content)
    
    # Make executable
    os.chmod('start_seva_agent_squad.sh', 0o755)
    print("✅ Created startup script: start_seva_agent_squad.sh")

def main():
    """Main deployment function"""
    print("🎯 SevaAI Agent Squad Deployment")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Run deployment steps
    setup_directory_structure()
    setup_environment()
    
    if not configure_aws_credentials():
        print("⚠️ Please configure AWS credentials and run again")
        return
    
    create_environment_file()
    
    if test_installation():
        create_startup_script()
        
        print("\n" + "=" * 50)
        print("🎉 Deployment completed successfully!")
        print("\n📋 Next Steps:")
        print("1. Review and update .env file with your specific configuration")
        print("2. If using Knowledge Base, update KNOWLEDGE_BASE_ID in .env")
        print("3. Run: ./start_seva_agent_squad.sh")
        print("4. Open: http://localhost:8085")
        print("\n🚀 Your Agent Squad is ready to serve!")
    else:
        print("❌ Deployment failed during testing")
        sys.exit(1)

if __name__ == "__main__":
    main()