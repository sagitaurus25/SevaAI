"""
Simple Data Analysis Agent using Anthropic Claude API directly
"""
import os
import json
from openai import OpenAI
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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

# Initialize OpenAI client
api_key = os.environ.get("OPENAI_API_KEY", "your_api_key_here")
client = OpenAI(api_key=api_key)

# System prompt for the agent
SYSTEM_PROMPT = """
You are a helpful AI data analyst assistant. You can help with data analysis tasks, 
provide insights on data processing techniques, and assist with data visualization recommendations.

When asked about data analysis:
1. Ask clarifying questions about the data format, size, and analysis goals
2. Suggest appropriate tools and libraries for the specific analysis task
3. Provide code examples when relevant
4. Explain your reasoning and methodology

You have access to the following tools:

1. data_summary - Provides recommendations for summarizing a dataset based on its description
2. visualization_recommender - Recommends visualization techniques based on data type and analysis goal
3. calculator - Performs mathematical calculations
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
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

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
        # Convert messages to the format expected by OpenAI
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Add system message
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        
        # Create the OpenAI message
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "data_summary",
                        "description": TOOLS["data_summary"]["description"],
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "data_description": {"type": "string", "description": "Description of the dataset"}
                            },
                            "required": ["data_description"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "visualization_recommender",
                        "description": TOOLS["visualization_recommender"]["description"],
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "data_type": {"type": "string", "description": "Type of data"},
                                "analysis_goal": {"type": "string", "description": "Analysis goal"}
                            },
                            "required": ["data_type", "analysis_goal"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "calculator",
                        "description": TOOLS["calculator"]["description"],
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "expression": {"type": "string", "description": "Mathematical expression"}
                            },
                            "required": ["expression"]
                        }
                    }
                }
            ]
        )
        
        # Process tool calls if any
        message = response.choices[0].message
        content = message.content or ""
        
        if message.tool_calls:
            for tool_call in message.tool_calls:
                function_call = tool_call.function
                tool_name = function_call.name
                tool_params = json.loads(function_call.arguments)
                
                if tool_name in TOOLS:
                    tool_fn = TOOLS[tool_name]["function"]
                    result = tool_fn(**tool_params)
                    
                    # Add tool result to the conversation
                    messages.append({"role": "assistant", "content": None, "tool_calls": [
                        {"type": "function", "function": {"name": tool_name, "arguments": function_call.arguments}, "id": tool_call.id}
                    ]})
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
                    
                    # Get a new response with the tool result
                    follow_up = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=2048
                    )
                    content = follow_up.choices[0].message.content
        
        return ChatResponse(role="assistant", content=content)
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)