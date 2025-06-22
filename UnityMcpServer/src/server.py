from mcp.server.fastmcp import FastMCP, Context, Image
import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List, Optional
from config import config
from tools import register_all_tools
from unity_connection import get_unity_connection, UnityConnection
import json

# Configure logging using settings from config
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format=config.log_format
)
logger = logging.getLogger("unity-mcp-server")

# Global connection state
_unity_connection: UnityConnection = None
_discovered_tools: List[Dict[str, Any]] = []

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Handle server startup and shutdown."""
    global _unity_connection
    logger.info("Unity MCP Server starting up")
    try:
        # Use existing connection if available, otherwise create new one
        if not _unity_connection:
            _unity_connection = get_unity_connection()
            logger.info("Connected to Unity on startup")
        
    except Exception as e:
        logger.warning(f"Could not connect to Unity on startup: {str(e)}")
        _unity_connection = None
    try:
        # Yield the connection object so it can be attached to the context
        # The key 'bridge' matches how tools like read_console expect to access it (ctx.bridge)
        yield {"bridge": _unity_connection}
    finally:
        if _unity_connection:
            _unity_connection.disconnect()
            _unity_connection = None
        logger.info("Unity MCP Server shut down")

def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server."""
    global _unity_connection, _discovered_tools
    
    # Initialize MCP server
    mcp = FastMCP(
        "unity-mcp-server",
        description="Unity Editor integration via Model Context Protocol",
        lifespan=server_lifespan
    )
    
    # Register all tools (static + dynamic interface)
    register_all_tools(mcp)
    
    # Try to connect to Unity early for tool discovery metadata
    try:
        temp_connection = get_unity_connection()
        if temp_connection:
            logger.info("Early Unity connection successful, discovering tools...")
            
            # Discover Unity tools for metadata only (don't register duplicates)
            response = temp_connection.send_command("list_tools", {})
            if response.get("success") and response.get("data"):
                tools_data = response["data"]
                if isinstance(tools_data, dict) and "tools" in tools_data:
                    _discovered_tools = tools_data["tools"]
                    logger.info(f"Discovered {len(_discovered_tools)} Unity tools for metadata")
            
            # Keep the connection for later use
            _unity_connection = temp_connection
        
    except Exception as e:
        logger.warning(f"Could not perform early tool discovery: {str(e)}")
    
    return mcp

# Create the MCP server instance
mcp = create_mcp_server()

# Asset Creation Strategy

@mcp.prompt()
def asset_creation_strategy() -> str:
    """Guide for discovering and using Unity MCP tools effectively."""
    global _discovered_tools
    
    # Build tools list from discovered Unity tools
    tools_list = []
    for tool in _discovered_tools:
        command_type = tool.get("commandType", "unknown")
        description = tool.get("description", "Unknown tool")
        tools_list.append(f"- `{command_type}`: {description}")
    
    # Build tools section
    if tools_list:
        tools_section = "\\n".join(tools_list)
    else:
        tools_section = "No tools discovered. Make sure Unity MCP Bridge is running and connected."
    
    return (
        f"Available Unity MCP Server Tools:\\n\\n"
        f"{tools_section}\\n\\n"
        "Tips:\\n"
        "- Create prefabs for reusable GameObjects.\\n"
        "- Always include a camera and main light in your scenes.\\n"
        "- Tools are automatically discovered from your Unity project.\\n"
    )

# Run the server
if __name__ == "__main__":
    mcp.run(transport='stdio')
