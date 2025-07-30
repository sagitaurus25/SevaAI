"""Auto-discovery of custom tools in this directory."""
import importlib
import inspect
import os
import sys
from pathlib import Path
from typing import List, Callable

from strands.tools import PythonAgentTool as Tool


def get_tools() -> List[Tool]:
    """Auto-discover and load all tools in this directory.
    
    Returns:
        List[Tool]: List of discovered tool functions
    """
    tools = []
    tools_dir = Path(__file__).parent
    
    # Get all .py files in the tools directory
    for file_path in tools_dir.glob("*.py"):
        if file_path.name == "__init__.py":
            continue
            
        # Import the module
        module_name = f"src.tools.{file_path.stem}"
        try:
            module = importlib.import_module(module_name)
            
            # Find all functions decorated with @tool
            for name, obj in inspect.getmembers(module):
                if isinstance(obj, Tool):
                    tools.append(obj)
                    print(f"Loaded tool: {obj.name}")
        except Exception as e:
            print(f"Error loading tool module {module_name}: {e}")
    
    return tools