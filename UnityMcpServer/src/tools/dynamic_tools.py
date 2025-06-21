from mcp.server.fastmcp import FastMCP, Context
from typing import Dict, Any, Optional
from unity_connection import get_unity_connection
import json
import logging

logger = logging.getLogger("unity-mcp-server")

def register_dynamic_tools(mcp: FastMCP):
    """Register dynamic tool discovery and execution with the MCP server."""

    @mcp.tool()
    def unity_custom_tool(
        ctx: Context,
        command_type: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a custom Unity MCP tool dynamically.
        
        This tool acts as a universal proxy for any custom Unity MCP tools
        that users have created by implementing the IUnityMcpTool interface.
        
        Args:
            command_type: The command type identifier of the custom tool
            parameters: Dictionary of parameters to pass to the tool
            
        Returns:
            Dictionary with results from the custom tool execution
        """
        try:
            # Prepare parameters for Unity
            params = parameters or {}
            
            # Send command to Unity
            response = get_unity_connection().send_command(command_type, params)
            
            # Process response from Unity
            if response.get("success"):
                return {
                    "success": True, 
                    "message": response.get("message", "Custom tool executed successfully."), 
                    "data": response.get("data")
                }
            else:
                return {
                    "success": False, 
                    "message": response.get("error", "An unknown error occurred in custom tool.")
                }

        except Exception as e:
            # Handle Python-side errors (e.g., connection issues)
            return {
                "success": False, 
                "message": f"Python error executing custom tool '{command_type}': {str(e)}"
            }

    @mcp.tool()
    def list_unity_tools(ctx: Context) -> Dict[str, Any]:
        """List all available Unity MCP tools, including custom ones.
        
        This tool queries Unity Bridge to discover all registered tools,
        both built-in and custom user-defined tools.
        
        Returns:
            Dictionary containing list of available tools with their descriptions
        """
        try:
            # Send a special command to Unity to get tool information
            # We'll use a reserved command type that lists all registered tools
            response = get_unity_connection().send_command("list_tools", {})
            
            if response.get("success"):
                return {
                    "success": True,
                    "message": "Tools listed successfully.",
                    "data": response.get("data", [])
                }
            else:
                # If Unity doesn't support list_tools command, return basic info
                return {
                    "success": True,
                    "message": "Tool listing not supported by Unity Bridge version.",
                    "data": {
                        "note": "Use unity_custom_tool with specific command_type to execute custom tools",
                        "built_in_tools": [
                            "manage_script",
                            "manage_scene", 
                            "manage_editor",
                            "manage_gameobject",
                            "manage_asset",
                            "read_console",
                            "execute_menu_item"
                        ]
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Python error listing Unity tools: {str(e)}"
            }

    @mcp.tool()
    def project_info(
        ctx: Context,
        action: str = "summary"
    ) -> Dict[str, Any]:
        """Get Unity project information using the custom project_info tool.
        
        This is a convenience wrapper for the project_info custom tool example.
        
        Args:
            action: Action to perform ('summary', 'assets', 'settings', 'scenes', 'packages')
            
        Returns:
            Dictionary with project information
        """
        return unity_custom_tool(ctx, "project_info", {"action": action})

    @mcp.tool()
    def editor_ui(
        ctx: Context,
        action: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Interact with Unity Editor UI using the custom editor_ui tool.
        
        This is a convenience wrapper for the editor_ui custom tool example.
        
        Args:
            action: Action to perform (e.g., 'get_windows', 'focus_window', 'show_notification')
            **kwargs: Additional parameters specific to the action
            
        Returns:
            Dictionary with UI operation results
        """
        params = {"action": action}
        params.update(kwargs)
        return unity_custom_tool(ctx, "editor_ui", params)