#!/bin/bash

# S3 Autonomous Agent Setup Script
echo "Setting up S3 Autonomous Agent..."

# Check Python and boto3
echo "Checking prerequisites..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

if ! python3 -c "import boto3" &> /dev/null; then
    echo "❌ boto3 is required but not installed."
    echo "Installing boto3..."
    pip3 install boto3
fi

# Run the setup script
echo "Running setup script..."
python3 setup_s3_agent.py

# Check if setup was successful
if [ $? -eq 0 ]; then
    echo "✅ Setup completed successfully!"
    echo "You can now open s3_agent_interface.html in your browser to use the S3 Autonomous Agent."
else
    echo "❌ Setup failed. Please check the error messages above."
    exit 1
fi