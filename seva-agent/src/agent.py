import os, importlib, yaml
from pathlib import Path

from strands import Agent

# Built-in tools from strands_tools (uncomment the ones you want to use)
from strands_tools import calculator      # Mathematical calculations
# from strands_tools import file_read       # Read file contents
# from strands_tools import shell           # Execute shell commands
# from strands_tools import web_search      # Search the web
# from strands_tools import image_generator # Generate images

# MCP (Model Context Protocol) integration
from src.mcp_tools import get_mcp_tools_sync

# Custom tools (auto-discovered from src/tools/)
from src.tools import get_tools

# Enable OpenTelemetry tracing for development (console only)
os.environ["STRANDS_OTEL_ENABLE_CONSOLE_EXPORT"] = "true"

def _resolve_env(obj):
    """Replace *_env keys with env-var values (recursively)."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k.endswith("_env"):
                env_val = os.getenv(v)
                if env_val is None:
                    raise RuntimeError(f"Environment variable '{v}' is not set")
                out[k[:-4]] = env_val  # strip _env suffix
            else:
                out[k] = _resolve_env(v)
        return out
    if isinstance(obj, list):
        return [_resolve_env(i) for i in obj]
    return obj


def load_config():
    """Load `.agent.yaml` from project root and return as dict."""
    cfg_path = Path(__file__).parent.parent / ".agent.yaml"
    return yaml.safe_load(cfg_path.read_text()) if cfg_path.exists() else {}


def load_model(cfg: dict):
    """Dynamically import the model class and instantiate it."""
    provider = cfg.get("provider", {})
    fqcn = provider.get("class")
    if not fqcn:
        raise ValueError("Missing 'provider.class' in .agent.yaml")

    module_path, class_name = fqcn.rsplit('.', 1)
    ModelCls = getattr(importlib.import_module(module_path), class_name)

    kwargs = _resolve_env(provider.get("kwargs", {}))
    return ModelCls(**kwargs)


def create_agent():
    """Factory that wires model + tools + system prompt into one Agent."""
    cfg = load_config()
    model = load_model(cfg)
    
    # Configure your tools here
    tools = []
    
    # Add built-in tools
    tools.extend([
        calculator,      # For mathematical calculations
    ])
    
    # Add MCP tools (commented by default)
    # tools.extend(get_mcp_tools_sync(cfg.get("mcp_servers", [])))
    
    # Add custom tools from src/tools/ (auto-discovered)
    tools.extend(get_tools())
    
    return Agent(
        model=model,
        tools=tools,
        system_prompt=cfg.get("system_prompt", "You are a helpful AI assistant.")
    )


# Initialize the singleton agent
agent = create_agent()