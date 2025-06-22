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
    """Create and configure the MCP server with dynamic tool discovery."""
    global _unity_connection, _discovered_tools
    
    # Initialize MCP server
    mcp = FastMCP(
        "unity-mcp-server",
        description="Unity Editor integration via Model Context Protocol",
        lifespan=server_lifespan
    )
    
    # Register static tools first
    register_all_tools(mcp)
    
    # Try to connect to Unity and discover tools early if possible
    try:
        temp_connection = get_unity_connection()
        if temp_connection:
            logger.info("Early Unity connection successful, discovering tools...")
            
            # Discover Unity tools
            response = temp_connection.send_command("list_tools", {})
            if response.get("success") and response.get("data"):
                tools_data = response["data"]
                if isinstance(tools_data, dict) and "tools" in tools_data:
                    _discovered_tools = tools_data["tools"]
                    
                    # Register dynamic tools
                    for tool_info in _discovered_tools:
                        command_type = tool_info.get("commandType")
                        description = tool_info.get("description", "Unity custom tool")
                        is_dynamic = tool_info.get("isDynamic", False)
                        
                        if not command_type or not is_dynamic:
                            continue
                        
                        # Create and register dynamic tool
                        def create_tool_handler(cmd_type: str, desc: str):
                            def tool_handler(ctx: Context, **kwargs) -> Dict[str, Any]:
                                f"""Execute Unity tool: {cmd_type}
                                
                                {desc}
                                """
                                try:
                                    bridge = getattr(ctx, 'bridge', None) or _unity_connection
                                    if not bridge:
                                        return {"success": False, "message": "No Unity connection available"}
                                    
                                    response = bridge.send_command(cmd_type, kwargs)
                                    
                                    if response.get("success"):
                                        return {
                                            "success": True,
                                            "message": response.get("message", f"Tool {cmd_type} executed successfully"),
                                            "data": response.get("data")
                                        }
                                    else:
                                        return {
                                            "success": False,
                                            "message": response.get("error", f"Tool {cmd_type} execution failed")
                                        }
                                        
                                except Exception as e:
                                    return {"success": False, "message": f"Error executing tool {cmd_type}: {str(e)}"}
                            
                            return tool_handler
                        
                        # Register the tool
                        tool_handler = create_tool_handler(command_type, description)
                        tool_handler.__name__ = command_type.replace("_", " ").title().replace(" ", "")
                        tool_handler.__doc__ = f"Execute Unity tool: {command_type}\n\n{description}"
                        
                        mcp.tool()(tool_handler)
                        logger.info(f"Registered dynamic MCP tool: {command_type}")
                    
                    logger.info(f"Successfully registered {len([t for t in _discovered_tools if t.get('isDynamic')])} dynamic tools")
            
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
    
    # Base built-in tools information
    builtin_tools = [
        "- `manage_editor`: Controls editor state and queries info.",
        "- `execute_menu_item`: Executes Unity Editor menu items by path.",
        "- `read_console`: Reads or clears Unity console messages, with filtering options.",
        "- `manage_scene`: Manages scenes.",
        "- `manage_gameobject`: Manages GameObjects in the scene.",
        "- `manage_script`: Manages C# script files.",
        "- `manage_asset`: Manages prefabs and assets."
    ]
    
    # Add discovered dynamic tools
    dynamic_tools = []
    for tool in _discovered_tools:
        if tool.get("isDynamic", False):
            command_type = tool.get("commandType", "unknown")
            description = tool.get("description", "Custom Unity tool")
            dynamic_tools.append(f"- `{command_type}`: {description}")
    
    tools_section = "\\n".join(builtin_tools)
    if dynamic_tools:
        tools_section += "\\n\\nCustom Tools:\\n" + "\\n".join(dynamic_tools)
    
    return (
        f"Available Unity MCP Server Tools:\\n\\n"
        f"{tools_section}\\n\\n"
        "Tips:\\n"
        "- Create prefabs for reusable GameObjects.\\n"
        "- Always include a camera and main light in your scenes.\\n"
        "- Custom tools are automatically discovered from your Unity project.\\n"
    )

# Run the server
if __name__ == "__main__":
    mcp.run(transport='stdio')
