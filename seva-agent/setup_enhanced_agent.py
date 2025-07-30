#!/usr/bin/env python3
"""
Setup script for SevaAI Enhanced AWS Agent
"""
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

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    
    dependencies = [
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.23.0",
        "boto3>=1.26.0",
        "pydantic>=2.0.0"
    ]
    
    for dep in dependencies:
        run_command(f"pip install '{dep}'", f"Installing {dep}")

def check_aws_credentials():
    """Check if AWS credentials are configured"""
    print("🔐 Checking AWS credentials...")
    
    result = run_command("aws sts get-caller-identity", "Verifying AWS credentials")
    
    if result:
        print("✅ AWS credentials are configured")
        return True
    else:
        print("❌ AWS credentials not found")
        print("Please run: aws configure")
        print("Or set environment variables:")
        print("  export AWS_ACCESS_KEY_ID=your_access_key")
        print("  export AWS_SECRET_ACCESS_KEY=your_secret_key")
        print("  export AWS_REGION=us-east-1")
        return False

def create_env_file():
    """Create .env file with AWS configuration"""
    print("⚙️ Creating environment configuration...")
    
    env_content = """# SevaAI Enhanced AWS Agent Configuration
# AWS Credentials (alternatively use aws configure or IAM roles)
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_REGION=us-east-1

# Agent Configuration
AGENT_PORT=8086
AGENT_HOST=0.0.0.0
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file - please update with your AWS credentials")
    else:
        print("✅ .env file already exists")

def create_startup_script():
    """Create startup script"""
    print("🚀 Creating startup script...")
    
    startup_content = """#!/bin/bash
# SevaAI Enhanced AWS Agent Startup Script

echo "🤖 Starting SevaAI Enhanced AWS Agent..."

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
    echo "❌ AWS credentials not found. Please configure AWS credentials first."
    exit 1
fi

# Start the enhanced agent
echo "🚀 Starting SevaAI Enhanced AWS Agent on port 8086..."
python3 enhanced_aws_agent.py

echo "📊 SevaAI Enhanced AWS Agent is running on http://localhost:8086"
"""
    
    with open('start_enhanced_agent.sh', 'w') as f:
        f.write(startup_content)
    
    os.chmod('start_enhanced_agent.sh', 0o755)
    print("✅ Created startup script: start_enhanced_agent.sh")

def create_requirements_file():
    """Create requirements.txt file"""
    print("📋 Creating requirements.txt...")
    
    requirements = """fastapi>=0.100.0
uvicorn[standard]>=0.23.0
boto3>=1.26.0
pydantic>=2.0.0
python-multipart>=0.0.6
"""
    
    with open('enhanced_requirements.txt', 'w') as f:
        f.write(requirements)
    
    print("✅ Created enhanced_requirements.txt")

def test_installation():
    """Test the installation"""
    print("🧪 Testing installation...")
    
    test_script = """
import sys
try:
    import fastapi
    import uvicorn
    import boto3
    import pydantic
    from enhanced_aws_tools import EnhancedAWSTools
    
    print("✅ All imports successful")
    
    # Test AWS tools initialization
    tools = EnhancedAWSTools()
    print("✅ AWS tools initialization successful")
    
    print("🎉 Installation test passed!")
    
except Exception as e:
    print(f"❌ Installation test failed: {str(e)}")
    sys.exit(1)
"""
    
    with open('test_enhanced_install.py', 'w') as f:
        f.write(test_script)
    
    result = run_command("python3 test_enhanced_install.py", "Running installation test")
    
    # Clean up test file
    os.remove('test_enhanced_install.py')
    
    return result is not None

def main():
    """Main setup function"""
    print("🎯 SevaAI Enhanced AWS Agent Setup")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Run setup steps
    install_dependencies()
    
    if not check_aws_credentials():
        print("⚠️ Please configure AWS credentials and run again")
        print("You can still continue setup and configure credentials later")
    
    create_env_file()
    create_requirements_file()
    
    if test_installation():
        create_startup_script()
        
        print("\\n" + "=" * 50)
        print("🎉 Setup completed successfully!")
        print("\\n📋 Next Steps:")
        print("1. Update .env file with your AWS credentials (if not using aws configure)")
        print("2. Run: ./start_enhanced_agent.sh")
        print("3. Open: http://localhost:8086")
        print("\\n🚀 Your Enhanced AWS Agent supports:")
        print("   • S3 - Bucket and object management")
        print("   • EC2 - Instance management and control")
        print("   • Lambda - Function management and invocation")
        print("   • IAM - User, role, and policy management")
        print("   • RDS - Database instance monitoring")
        print("   • CloudWatch - Metrics and alarms")
        print("   • VPC - Network management")
        print("   • Route53 - DNS management")
        print("   • CloudFormation - Stack management")
        print("   • Cost & Billing - Usage monitoring")
        print("\\n💡 Try asking: 'List my S3 buckets' or 'Show my EC2 instances'")
    else:
        print("❌ Setup failed during testing")
        sys.exit(1)

if __name__ == "__main__":
    main()