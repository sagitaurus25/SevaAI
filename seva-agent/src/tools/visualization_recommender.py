from strands.tools import tool
import json

@tool
def visualization_recommender(data_type: str, analysis_goal: str) -> str:
    """Recommends appropriate visualization techniques based on data type and analysis goal.
    
    Args:
        data_type: Type of data (e.g., categorical, numerical, time-series, geospatial)
        analysis_goal: What you want to understand from the data (e.g., distribution, comparison, relationship)
        
    Returns:
        str: JSON string with visualization recommendations
    """
    # Dictionary mapping data types and analysis goals to visualization techniques
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