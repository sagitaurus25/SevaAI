#!/bin/bash

# Load environment variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Install dependencies if needed
pip install -r aws_requirements.txt

# Run the agent
uvicorn aws_agent:app --host 0.0.0.0 --port 8084