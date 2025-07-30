#!/bin/bash
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
