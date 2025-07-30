"""
Simple Data Analysis Agent using AWS Bedrock directly
"""
import os
import json
import boto3
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Initialize FastAPI app
app = FastAPI(title="Seva Data Analyst Agent")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Bedrock client
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
)

# System prompt for the agent
SYSTEM_PROMPT = """
You are a helpful AI data analyst assistant. You can help with data analysis tasks, 
provide insights on data processing techniques, and assist with data visualization recommendations.

When asked about data analysis:
1. Ask clarifying questions about the data format, size, and analysis goals
2. Suggest appropriate tools and libraries for the specific analysis task
3. Provide code examples when relevant
4. Explain your reasoning and methodology
"""

# Tool definitions
def data_summary(data_description: str) -> str:
    """Provides recommendations for summarizing a dataset based on its description."""
    recommendations = {
        "summary_techniques": [
            "Descriptive statistics (mean, median, mode, standard deviation)",
            "Data distribution visualization (histograms, box plots)",
            "Correlation analysis between variables",
            "Missing value analysis"
        ],
        "recommended_libraries": [
            "pandas - for data manipulation and basic statistics",
            "numpy - for numerical operations",
            "matplotlib/seaborn - for visualization",
            "scipy.stats - for statistical analysis"
        ],
        "sample_code": """
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load data
df = pd.read_csv('your_data.csv')

# Basic summary
print(df.describe())
print(df.info())

# Check missing values
print(df.isnull().sum())

# Visualize distributions
plt.figure(figsize=(12, 8))
for i, col in enumerate(df.select_dtypes(include=['float64', 'int64']).columns):
    plt.subplot(3, 3, i+1)
    sns.histplot(df[col], kde=True)
    plt.title(col)
plt.tight_layout()
plt.show()
"""
    }
    return json.dumps(recommendations, indent=2)

def visualization_recommender(data_type: str, analysis_goal: str) -> str:
    """Recommends appropriate visualization techniques based on data type and analysis goal."""
    viz_recommendations = {
        "categorical": {
            "distribution": ["Bar charts", "Pie charts", "Treemaps"],
            "comparison": ["Grouped bar charts", "Stacked bar charts", "Heatmaps"],
            "relationship": ["Mosaic plots", "Contingency tables", "Network diagrams"]
        },
        "numerical": {
            "distribution": ["Histograms", "Density plots", "Box plots", "Violin plots"],
            "comparison": ["Box plots", "Violin plots", "Strip plots", "Swarm plots"],
            "relationship": ["Scatter plots", "Bubble charts", "Hexbin plots", "2D density plots"]
        },
        "time-series": {
            "distribution": ["Histograms by time period", "Box plots by time period"],
            "comparison": ["Line charts", "Area charts", "Stacked area charts"],
            "relationship": ["Lag plots", "Autocorrelation plots", "Cross-correlation plots"]
        },
        "geospatial": {
            "distribution": ["Choropleth maps", "Dot density maps"],
            "comparison": ["Choropleth maps", "Cartograms", "Proportional symbol maps"],
            "relationship": ["Flow maps", "Connection maps", "Bivariate choropleth maps"]
        }
    }
    
    # Normalize inputs
    data_type = data_type.lower()
    analysis_goal = analysis_goal.lower()
    
    # Find matching recommendations
    if data_type in viz_recommendations and analysis_goal in viz_recommendations[data_type]:
        recommendations = viz_recommendations[data_type][analysis_goal]
        libraries = {
            "categorical": ["matplotlib", "seaborn", "plotly"],
            "numerical": ["matplotlib", "seaborn", "plotly"],
            "time-series": ["matplotlib", "seaborn", "plotly", "statsmodels"],
            "geospatial": ["geopandas", "folium", "plotly", "kepler.gl"]
        }
        
        result = {
            "recommended_visualizations": recommendations,
            "recommended_libraries": libraries.get(data_type, ["matplotlib", "seaborn"]),
            "tips": f"For {data_type} data with {analysis_goal} goals, focus on showing the data in a way that highlights the {analysis_goal} patterns."
        }
        
        return json.dumps(result, indent=2)
    else:
        return json.dumps({
            "error": "Invalid data type or analysis goal",
            "supported_data_types": list(viz_recommendations.keys()),
            "supported_analysis_goals": ["distribution", "comparison", "relationship"]
        }, indent=2)

def calculator(expression: str) -> str:
    """Performs mathematical calculations."""
    try:
        # Using eval is generally not safe, but this is a simple example
        # In a real implementation, you would use a safer approach
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"

# Available tools
TOOLS = {
    "data_summary": {
        "function": data_summary,
        "description": "Provides recommendations for summarizing a dataset based on its description",
        "parameters": {
            "data_description": "Description of the dataset including its format, size, and content"
        }
    },
    "visualization_recommender": {
        "function": visualization_recommender,
        "description": "Recommends visualization techniques based on data type and analysis goal",
        "parameters": {
            "data_type": "Type of data (e.g., categorical, numerical, time-series, geospatial)",
            "analysis_goal": "What you want to understand from the data (e.g., distribution, comparison, relationship)"
        }
    },
    "calculator": {
        "function": calculator,
        "description": "Performs mathematical calculations",
        "parameters": {
            "expression": "Mathematical expression to evaluate"
        }
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

# API endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with HTML interface."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Seva Data Analyst Agent</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            #chatbox { height: 400px; border: 1px solid #ddd; padding: 10px; overflow-y: auto; margin-bottom: 10px; }
            #input { width: 80%; padding: 8px; }
            button { padding: 8px 15px; background: #4CAF50; color: white; border: none; cursor: pointer; }
            .user-msg { text-align: right; margin: 5px; padding: 8px; background: #e1ffc7; border-radius: 5px; }
            .bot-msg { text-align: left; margin: 5px; padding: 8px; background: #f1f1f1; border-radius: 5px; }
            pre { white-space: pre-wrap; background: #f8f8f8; padding: 10px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>Seva Data Analyst Agent</h1>
        <div id="chatbox"></div>
        <div>
            <input type="text" id="input" placeholder="Ask about data analysis..." />
            <button onclick="sendMessage()">Send</button>
        </div>
        <script>
            const chatbox = document.getElementById('chatbox');
            const input = document.getElementById('input');
            
            // Add initial message
            addBotMessage("Hello! I'm your data analyst assistant. How can I help you today?");
            
            function addUserMessage(text) {
                const div = document.createElement('div');
                div.className = 'user-msg';
                div.textContent = text;
                chatbox.appendChild(div);
                chatbox.scrollTop = chatbox.scrollHeight;
            }
            
            function addBotMessage(text) {
                const div = document.createElement('div');
                div.className = 'bot-msg';
                
                // Check if the text contains code blocks
                if (text.includes('```')) {
                    const parts = text.split(/```(\w*)\n/);
                    let html = '';
                    
                    for (let i = 0; i < parts.length; i++) {
                        if (i % 3 === 0) {
                            // Regular text
                            html += parts[i];
                        } else if (i % 3 === 1) {
                            // Language (ignored for now)
                        } else {
                            // Code block
                            html += `<pre>${parts[i]}</pre>`;
                        }
                    }
                    
                    div.innerHTML = html;
                } else {
                    div.textContent = text;
                }
                
                chatbox.appendChild(div);
                chatbox.scrollTop = chatbox.scrollHeight;
            }
            
            async function sendMessage() {
                const text = input.value.trim();
                if (!text) return;
                
                addUserMessage(text);
                input.value = '';
                
                // Add loading message
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'bot-msg';
                loadingDiv.textContent = 'Thinking...';
                chatbox.appendChild(loadingDiv);
                
                try {
                    console.log('Sending request to /chat');
                    const requestBody = {
                        messages: [
                            { role: 'user', content: text }
                        ]
                    };
                    console.log('Request body:', requestBody);
                    
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(requestBody),
                    });
                    
                    console.log('Response status:', response.status);
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    console.log('Response data:', data);
                    
                    // Remove loading message
                    chatbox.removeChild(loadingDiv);
                    
                    addBotMessage(data.content);
                } catch (error) {
                    // Remove loading message
                    chatbox.removeChild(loadingDiv);
                    
                    addBotMessage(`Sorry, there was an error processing your request: ${error.message}`);
                    console.error('Error:', error);
                }
            }
            
            // Allow pressing Enter to send message
            input.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify API is working."""
    return {"message": "API is working!"}

@app.get("/info")
async def get_info():
    """Return information about the agent."""
    return {
        "name": "Seva Data Analyst Agent",
        "version": "1.0.0",
        "description": "An AI assistant for data analysis tasks",
        "tools": list(TOOLS.keys())
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat request."""
    try:
        print(f"Received chat request: {request}")
        
        # Convert messages to the format expected by Claude
        formatted_messages = []
        for msg in request.messages:
            if msg.role == "user":
                formatted_messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                formatted_messages.append({"role": "assistant", "content": msg.content})
        
        print(f"Formatted messages: {formatted_messages}")
        
        # Create the Claude request body
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "temperature": 0.7,
            "system": SYSTEM_PROMPT,
            "messages": formatted_messages
        }
        
        print("Calling Bedrock API...")
        
        # Call Bedrock with Claude model
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(body)
        )
        
        print("Received response from Bedrock")
        
        # Parse the response
        response_body = json.loads(response["body"].read().decode("utf-8"))
        print(f"Response body: {response_body}")
        
        content = response_body.get("content", [{"text": "No response generated"}])[0]["text"]
        
        print(f"Extracted content: {content[:100]}...")
        
        # For simplicity, we're not handling tool calls in this basic version
        # In a real implementation, you would parse tool calls and execute them
        
        return ChatResponse(role="assistant", content=content)
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)