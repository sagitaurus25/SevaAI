from strands.tools import tool
import json

@tool
def data_summary(data_description: str) -> str:
    """Provides recommendations for summarizing a dataset based on its description.
    
    Args:
        data_description: Description of the dataset including its format, size, and content
        
    Returns:
        str: Recommendations for summarizing and understanding the dataset
    """
    # In a real implementation, this would contain more sophisticated logic
    # This is a simplified example
    
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