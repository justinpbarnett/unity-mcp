# File: fix_asmdef_references.py
# Placed in: C:\Users\admin\AppData\Local\Programs\UnityMCP\UnityMcpServer\src\tools
# Description: A tool to automatically analyze and fix .asmdef references for a given C# script.

from mcp.server.fastmcp import FastMCP, Context
from typing import Dict, Any
from unity_connection import get_unity_connection

def register_fix_asmdef_references_tools(mcp: FastMCP):
    """
    This function is called by the MCP server to register the tools in this file.
    """

    @mcp.tool()
    def fix_asmdef_references(
        ctx: Context,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        Analyzes the dependencies of a C# file and automatically updates the
        references in its corresponding .asmdef file.

        Args:
            file_path: The full project path to the C# file to be analyzed
                       (e.g., 'Assets/Scripts/MyNewSystem.cs').

        Returns:
            A dictionary containing the result of the operation.
        """
        if not file_path:
            return {"success": False, "message": "Error: file_path cannot be empty."}

        try:
            # Prepare parameters for the command to be sent to Unity
            params = {
                "filePath": file_path,
            }
            
            # Send the command to Unity.
            # The command name "fix_asmdef_references" must exactly match the
            # [CommandHandler] attribute in the C# script.
            response = get_unity_connection().send_command("fix_asmdef_references", params)

            # Process and return the response from Unity
            if response and response.get("success"):
                return {"success": True, "message": response.get("message", "Asmdef references fixed successfully.")}
            else:
                error_message = response.get("message", "An unknown error occurred in Unity.")
                return {"success": False, "message": error_message}

        except Exception as e:
            return {"success": False, "message": f"Python error calling fix_asmdef_references: {str(e)}"}
