"""
Enhanced AWS Agent with comprehensive service support
Supports S3, EC2, Lambda, IAM, RDS, CloudWatch, VPC, Route53, CloudFormation, and more
"""
import os
import json
import boto3
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from enhanced_aws_tools import EnhancedAWSTools

# Initialize FastAPI app
app = FastAPI(title="SevaAI Enhanced AWS Agent")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AWS tools
aws_tools = EnhancedAWSTools(
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    region_name=os.environ.get("AWS_REGION", "us-east-1")
)

# Initialize Bedrock client
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
)

# Enhanced system prompt
SYSTEM_PROMPT = """
You are SevaAI, an expert AWS assistant with comprehensive knowledge of AWS services. You can help with:

**Core Services:**
- S3: Bucket management, object operations, policies, lifecycle
- EC2: Instance management, security groups, key pairs, networking
- Lambda: Function management, invocation, logs, triggers
- IAM: Users, roles, policies, permissions, security
- RDS: Database instances, snapshots, monitoring
- CloudWatch: Metrics, alarms, logs, monitoring
- VPC: Virtual networks, subnets, security, routing
- Route53: DNS management, hosted zones
- CloudFormation: Infrastructure as code, stack management

**Capabilities:**
- List, create, modify, and delete AWS resources
- Monitor performance and costs
- Troubleshoot issues and provide solutions
- Security best practices and recommendations
- Cost optimization suggestions
- Architecture guidance

When helping users:
1. Ask clarifying questions about their specific needs
2. Provide step-by-step guidance
3. Include relevant AWS CLI commands when helpful
4. Suggest best practices and security considerations
5. Offer cost optimization tips when relevant

Available tools: {tools}
"""

# Tool definitions with enhanced AWS operations
TOOLS = {
    # S3 Operations
    "list_s3_buckets": {
        "function": aws_tools.list_s3_buckets,
        "description": "List all S3 buckets in your AWS account"
    },
    "create_s3_bucket": {
        "function": aws_tools.create_s3_bucket,
        "description": "Create a new S3 bucket",
        "parameters": {"bucket_name": "Name of the bucket to create", "region": "AWS region (optional)"}
    },
    "delete_s3_bucket": {
        "function": aws_tools.delete_s3_bucket,
        "description": "Delete an S3 bucket (must be empty)",
        "parameters": {"bucket_name": "Name of the bucket to delete"}
    },
    "list_s3_objects": {
        "function": aws_tools.list_s3_objects,
        "description": "List objects in an S3 bucket",
        "parameters": {"bucket_name": "Name of the bucket", "prefix": "Object prefix filter (optional)"}
    },
    
    # EC2 Operations
    "list_ec2_instances": {
        "function": aws_tools.list_ec2_instances,
        "description": "List all EC2 instances in your account"
    },
    "start_ec2_instance": {
        "function": aws_tools.start_ec2_instance,
        "description": "Start an EC2 instance",
        "parameters": {"instance_id": "ID of the instance to start"}
    },
    "stop_ec2_instance": {
        "function": aws_tools.stop_ec2_instance,
        "description": "Stop an EC2 instance",
        "parameters": {"instance_id": "ID of the instance to stop"}
    },
    "list_security_groups": {
        "function": aws_tools.list_security_groups,
        "description": "List EC2 security groups"
    },
    
    # Lambda Operations
    "list_lambda_functions": {
        "function": aws_tools.list_lambda_functions,
        "description": "List all Lambda functions in your account"
    },
    "invoke_lambda_function": {
        "function": aws_tools.invoke_lambda_function,
        "description": "Invoke a Lambda function",
        "parameters": {"function_name": "Name of the function to invoke", "payload": "JSON payload (optional)"}
    },
    "get_lambda_logs": {
        "function": aws_tools.get_lambda_logs,
        "description": "Get recent Lambda function logs",
        "parameters": {"function_name": "Name of the function", "hours": "Hours of logs to retrieve (default: 1)"}
    },
    
    # IAM Operations
    "list_iam_users": {
        "function": aws_tools.list_iam_users,
        "description": "List IAM users in your account"
    },
    "list_iam_roles": {
        "function": aws_tools.list_iam_roles,
        "description": "List IAM roles in your account"
    },
    "list_iam_policies": {
        "function": aws_tools.list_iam_policies,
        "description": "List IAM policies",
        "parameters": {"scope": "Policy scope: 'Local' or 'AWS' (default: Local)"}
    },
    
    # RDS Operations
    "describe_rds_instances": {
        "function": aws_tools.describe_rds_instances,
        "description": "List RDS database instances"
    },
    "list_rds_snapshots": {
        "function": aws_tools.list_rds_snapshots,
        "description": "List RDS database snapshots"
    },
    
    # CloudWatch Operations
    "list_cloudwatch_alarms": {
        "function": aws_tools.list_cloudwatch_alarms,
        "description": "List CloudWatch alarms"
    },
    "get_cloudwatch_metrics": {
        "function": aws_tools.get_cloudwatch_metrics,
        "description": "Get CloudWatch metrics for a specific metric",
        "parameters": {"namespace": "AWS namespace", "metric_name": "Metric name", "hours": "Hours of data (default: 24)"}
    },
    
    # VPC Operations
    "list_vpcs": {
        "function": aws_tools.list_vpcs,
        "description": "List VPCs in your account"
    },
    "list_subnets": {
        "function": aws_tools.list_subnets,
        "description": "List subnets",
        "parameters": {"vpc_id": "VPC ID to filter by (optional)"}
    },
    
    # Cost and Billing
    "get_cost_and_usage": {
        "function": aws_tools.get_cost_and_usage,
        "description": "Get cost and usage data",
        "parameters": {"days": "Number of days to retrieve (default: 30)"}
    },
    
    # Route 53
    "list_hosted_zones": {
        "function": aws_tools.list_hosted_zones,
        "description": "List Route 53 hosted zones"
    },
    
    # CloudFormation
    "list_cloudformation_stacks": {
        "function": aws_tools.list_cloudformation_stacks,
        "description": "List CloudFormation stacks"
    },
    
    # Utility
    "get_account_info": {
        "function": aws_tools.get_account_info,
        "description": "Get AWS account information"
    },
    "list_regions": {
        "function": aws_tools.list_regions,
        "description": "List available AWS regions"
    }
}

# Pydantic models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class ChatResponse(BaseModel):
    role: str
    content: str

def parse_tool_calls(content: str) -> List[Dict[str, Any]]:
    """Parse tool calls from Claude's response"""
    tool_calls = []
    
    # Simple parsing - in production, use proper XML/JSON parsing
    if "use_tool" in content.lower():
        lines = content.split('\n')
        current_tool = None
        current_params = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('Tool:'):
                if current_tool:
                    tool_calls.append({"name": current_tool, "parameters": current_params})
                current_tool = line.replace('Tool:', '').strip()
                current_params = {}
            elif ':' in line and current_tool:
                key, value = line.split(':', 1)
                current_params[key.strip()] = value.strip()
        
        if current_tool:
            tool_calls.append({"name": current_tool, "parameters": current_params})
    
    return tool_calls

def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> str:
    """Execute a tool with given parameters"""
    if tool_name not in TOOLS:
        return f"Error: Tool '{tool_name}' not found"
    
    try:
        tool_func = TOOLS[tool_name]["function"]
        
        # Call function with parameters
        if parameters:
            result = tool_func(**parameters)
        else:
            result = tool_func()
        
        return result
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"

# API endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Enhanced HTML interface"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SevaAI Enhanced AWS Agent</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
            .header {{ background: #232f3e; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .header h1 {{ margin: 0; }}
            .header p {{ margin: 5px 0 0 0; opacity: 0.8; }}
            .container {{ display: flex; gap: 20px; }}
            .chat-section {{ flex: 2; background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .tools-section {{ flex: 1; background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            #chatbox {{ height: 500px; border: 1px solid #ddd; padding: 15px; overflow-y: auto; margin-bottom: 15px; border-radius: 4px; }}
            #input {{ width: calc(100% - 100px); padding: 10px; border: 1px solid #ddd; border-radius: 4px; }}
            button {{ padding: 10px 20px; background: #ff9900; color: white; border: none; cursor: pointer; border-radius: 4px; margin-left: 10px; }}
            button:hover {{ background: #e88900; }}
            .user-msg {{ text-align: right; margin: 10px 0; padding: 10px; background: #e3f2fd; border-radius: 8px; }}
            .bot-msg {{ text-align: left; margin: 10px 0; padding: 10px; background: #f1f1f1; border-radius: 8px; }}
            .tool-result {{ background: #f8f9fa; border-left: 4px solid #28a745; padding: 10px; margin: 5px 0; font-family: monospace; font-size: 12px; }}
            pre {{ white-space: pre-wrap; background: #f8f8f8; padding: 10px; border-radius: 4px; overflow-x: auto; }}
            .tools-list {{ max-height: 400px; overflow-y: auto; }}
            .tool-item {{ padding: 8px; border-bottom: 1px solid #eee; }}
            .tool-name {{ font-weight: bold; color: #232f3e; }}
            .tool-desc {{ font-size: 12px; color: #666; margin-top: 4px; }}
            .service-section {{ margin-bottom: 20px; }}
            .service-title {{ font-weight: bold; color: #ff9900; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 SevaAI Enhanced AWS Agent</h1>
            <p>Your comprehensive AWS assistant with support for S3, EC2, Lambda, IAM, RDS, CloudWatch, VPC, and more!</p>
        </div>
        
        <div class="container">
            <div class="chat-section">
                <h3>Chat with SevaAI</h3>
                <div id="chatbox"></div>
                <div>
                    <input type="text" id="input" placeholder="Ask about your AWS resources..." />
                    <button onclick="sendMessage()">Send</button>
                </div>
            </div>
            
            <div class="tools-section">
                <h3>Available AWS Tools</h3>
                <div class="tools-list">
                    <div class="service-section">
                        <div class="service-title">S3 Storage</div>
                        <div class="tool-item">
                            <div class="tool-name">list_s3_buckets</div>
                            <div class="tool-desc">List all S3 buckets</div>
                        </div>
                        <div class="tool-item">
                            <div class="tool-name">list_s3_objects</div>
                            <div class="tool-desc">List objects in bucket</div>
                        </div>
                    </div>
                    
                    <div class="service-section">
                        <div class="service-title">EC2 Compute</div>
                        <div class="tool-item">
                            <div class="tool-name">list_ec2_instances</div>
                            <div class="tool-desc">List EC2 instances</div>
                        </div>
                        <div class="tool-item">
                            <div class="tool-name">start/stop_ec2_instance</div>
                            <div class="tool-desc">Control EC2 instances</div>
                        </div>
                    </div>
                    
                    <div class="service-section">
                        <div class="service-title">Lambda Functions</div>
                        <div class="tool-item">
                            <div class="tool-name">list_lambda_functions</div>
                            <div class="tool-desc">List Lambda functions</div>
                        </div>
                        <div class="tool-item">
                            <div class="tool-name">invoke_lambda_function</div>
                            <div class="tool-desc">Invoke Lambda function</div>
                        </div>
                    </div>
                    
                    <div class="service-section">
                        <div class="service-title">IAM Security</div>
                        <div class="tool-item">
                            <div class="tool-name">list_iam_users</div>
                            <div class="tool-desc">List IAM users</div>
                        </div>
                        <div class="tool-item">
                            <div class="tool-name">list_iam_roles</div>
                            <div class="tool-desc">List IAM roles</div>
                        </div>
                    </div>
                    
                    <div class="service-section">
                        <div class="service-title">Monitoring</div>
                        <div class="tool-item">
                            <div class="tool-name">list_cloudwatch_alarms</div>
                            <div class="tool-desc">List CloudWatch alarms</div>
                        </div>
                        <div class="tool-item">
                            <div class="tool-name">get_cost_and_usage</div>
                            <div class="tool-desc">Get cost information</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            const chatbox = document.getElementById('chatbox');
            const input = document.getElementById('input');
            
            addBotMessage("Hello! I'm SevaAI, your enhanced AWS assistant. I can help you manage S3, EC2, Lambda, IAM, RDS, CloudWatch, VPC, and many other AWS services. What would you like to do today?");
            
            function addUserMessage(text) {{
                const div = document.createElement('div');
                div.className = 'user-msg';
                div.textContent = text;
                chatbox.appendChild(div);
                chatbox.scrollTop = chatbox.scrollHeight;
            }}
            
            function addBotMessage(text) {{
                const div = document.createElement('div');
                div.className = 'bot-msg';
                
                if (text.includes('```')) {{
                    const parts = text.split(/```(\\w*)\\n/);
                    let html = '';
                    
                    for (let i = 0; i < parts.length; i++) {{
                        if (i % 3 === 0) {{
                            html += parts[i];
                        }} else if (i % 3 === 1) {{
                            // Language (ignored for now)
                        }} else {{
                            html += `<pre>${{parts[i]}}</pre>`;
                        }}
                    }}
                    
                    div.innerHTML = html;
                }} else {{
                    div.textContent = text;
                }}
                
                chatbox.appendChild(div);
                chatbox.scrollTop = chatbox.scrollHeight;
            }}
            
            function addToolResult(result) {{
                const div = document.createElement('div');
                div.className = 'tool-result';
                div.textContent = result;
                chatbox.appendChild(div);
                chatbox.scrollTop = chatbox.scrollHeight;
            }}
            
            async function sendMessage() {{
                const text = input.value.trim();
                if (!text) return;
                
                addUserMessage(text);
                input.value = '';
                
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'bot-msg';
                loadingDiv.textContent = 'Processing your request...';
                chatbox.appendChild(loadingDiv);
                
                try {{
                    const response = await fetch('/chat', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ messages: [{{ role: 'user', content: text }}] }}),
                    }});
                    
                    if (!response.ok) {{
                        throw new Error(`HTTP error! status: ${{response.status}}`);
                    }}
                    
                    const data = await response.json();
                    chatbox.removeChild(loadingDiv);
                    addBotMessage(data.content);
                    
                }} catch (error) {{
                    chatbox.removeChild(loadingDiv);
                    addBotMessage(`Sorry, there was an error: ${{error.message}}`);
                }}
            }}
            
            input.addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') {{
                    sendMessage();
                }}
            }});
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "services": list(TOOLS.keys())}

@app.get("/tools")
async def list_tools():
    """List available tools"""
    return {"tools": {name: {"description": tool["description"], "parameters": tool.get("parameters", {})} for name, tool in TOOLS.items()}}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Enhanced chat endpoint with tool execution"""
    try:
        # Format messages for Claude
        formatted_messages = []
        for msg in request.messages:
            if msg.role in ["user", "assistant"]:
                formatted_messages.append({"role": msg.role, "content": msg.content})
        
        # Create Claude request
        tools_list = ", ".join(TOOLS.keys())
        system_prompt = SYSTEM_PROMPT.format(tools=tools_list)
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "temperature": 0.7,
            "system": system_prompt,
            "messages": formatted_messages
        }
        
        # Call Bedrock
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
            body=json.dumps(body)
        )
        
        response_body = json.loads(response["body"].read().decode("utf-8"))
        content = response_body.get("content", [{"text": "No response generated"}])[0]["text"]
        
        # Parse and execute any tool calls
        tool_calls = parse_tool_calls(content)
        tool_results = []
        
        for tool_call in tool_calls:
            result = execute_tool(tool_call["name"], tool_call.get("parameters", {}))
            tool_results.append(f"Tool: {tool_call['name']}\\nResult: {result}")
        
        # Append tool results to response
        if tool_results:
            content += "\\n\\n" + "\\n\\n".join(tool_results)
        
        return ChatResponse(role="assistant", content=content)
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8086)