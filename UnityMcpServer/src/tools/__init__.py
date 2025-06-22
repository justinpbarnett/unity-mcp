from .dynamic_tools import register_dynamic_tools

def register_all_tools(mcp):
    """Register all refactored tools with the MCP server."""
    print("Registering Unity MCP Server refactored tools...")
    register_dynamic_tools(mcp)
    print("Unity MCP Server tool registration complete.")
