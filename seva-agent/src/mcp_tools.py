"""MCP (Model Context Protocol) tools integration."""

def get_mcp_tools_sync(mcp_servers_config):
    """Load MCP tools from configured servers.
    
    Args:
        mcp_servers_config: List of MCP server configurations from .agent.yaml
        
    Returns:
        list: List of MCP tools or empty list if MCP is not installed
    """
    try:
        from mcp.client import MCPClient
        from mcp.tools import create_tools_from_mcp_client
    except ImportError:
        print("MCP not installed. Skipping MCP tools.")
        return []
    
    if not mcp_servers_config:
        return []
    
    tools = []
    for server_config in mcp_servers_config:
        try:
            client = MCPClient.from_config(server_config)
            server_tools = create_tools_from_mcp_client(client)
            tools.extend(server_tools)
            print(f"Loaded {len(server_tools)} tools from MCP server: {server_config['name']}")
        except Exception as e:
            print(f"Error loading MCP server {server_config.get('name')}: {e}")
    
    return tools