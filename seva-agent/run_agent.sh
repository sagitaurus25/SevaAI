#!/bin/bash

# Load environment variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Install dependencies if needed
pip install -r simple_requirements.txt

# Run the agent
uvicorn simple_agent:app --host 0.0.0.0 --port 8084