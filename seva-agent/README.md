# Seva Data Analyst Agent

A specialized AI agent built with the Agent Development Toolkit (ADT) for Strands that helps with data analysis tasks.

## Features

- Provides data analysis recommendations and insights
- Suggests appropriate visualization techniques based on data type and analysis goals
- Offers code examples for common data analysis tasks
- Includes built-in calculator tool for mathematical operations

## Custom Tools

1. **Data Summary Tool** - Provides recommendations for summarizing datasets
2. **Visualization Recommender** - Suggests visualization techniques based on data type and analysis goals

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Node.js 18+ (for UI assets)
- Docker (optional, for container mode)

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install ADT:
   ```bash
   pip install git+https://github.com/awslabs/agent-dev-toolkit.git
   ```

### Running the Agent

#### Development Mode

```bash
adt dev --port 8083
```

The agent chat playground will be available at http://localhost:8083.

#### Container Mode

```bash
adt dev --container --port 9000
```

### Configuration

The agent is configured in the `.agent.yaml` file. You can modify:

- System prompt
- Model provider and parameters
- MCP server integrations

## AWS Credentials

To use AWS Bedrock, set up your AWS credentials:

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-west-2
```

Or use a profile:

```bash
adt dev --aws-profile your-profile-name
```

## Adding New Tools

1. Create a new Python file in the `src/tools/` directory
2. Define your tool function with the `@tool` decorator
3. Restart the development server

Example:
```python
from strands.tools import tool

@tool
def my_new_tool(param1: str, param2: int) -> str:
    """Tool description
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        str: Description of return value
    """
    # Tool implementation
    return f"Result: {param1}, {param2}"
```

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.