from mcp.server.fastmcp import FastMCP, Context
from typing import Dict, Any, List
from unity_connection import get_unity_connection, send_command_with_retry
from config import config
import time
import os
import base64


def register_manage_script_tools(mcp: FastMCP):
    """Register all script management tools with the MCP server."""

    def _split_uri(uri: str) -> tuple[str, str]:
        if uri.startswith("unity://path/"):
            path = uri[len("unity://path/") :]
        elif uri.startswith("file://"):
            path = uri[len("file://") :]
        else:
            path = uri
        path = path.replace("\\", "/")
        name = os.path.splitext(os.path.basename(path))[0]
        directory = os.path.dirname(path)
        return name, directory

    @mcp.tool()
    def apply_text_edits(
        ctx: Context,
        uri: str,
        edits: List[Dict[str, Any]],
        precondition_sha256: str | None = None,
    ) -> Dict[str, Any]:
        """Apply small text edits to a C# script identified by URI."""
        name, directory = _split_uri(uri)
        params = {
            "action": "apply_text_edits",
            "name": name,
            "path": directory,
            "edits": edits,
            "precondition_sha256": precondition_sha256,
        }
        params = {k: v for k, v in params.items() if v is not None}
        resp = send_command_with_retry("manage_script", params)
        return resp if isinstance(resp, dict) else {"success": False, "message": str(resp)}

    @mcp.tool()
    def create_script(
        ctx: Context,
        path: str,
        contents: str = "",
        script_type: str | None = None,
        namespace: str | None = None,
    ) -> Dict[str, Any]:
        """Create a new C# script at the given path."""
        name = os.path.splitext(os.path.basename(path))[0]
        directory = os.path.dirname(path)
        params: Dict[str, Any] = {
            "action": "create",
            "name": name,
            "path": directory,
            "namespace": namespace,
            "scriptType": script_type,
        }
        if contents is not None:
            params["encodedContents"] = base64.b64encode(contents.encode("utf-8")).decode("utf-8")
            params["contentsEncoded"] = True
        params = {k: v for k, v in params.items() if v is not None}
        resp = send_command_with_retry("manage_script", params)
        return resp if isinstance(resp, dict) else {"success": False, "message": str(resp)}

    @mcp.tool()
    def delete_script(ctx: Context, uri: str) -> Dict[str, Any]:
        """Delete a C# script by URI."""
        name, directory = _split_uri(uri)
        params = {"action": "delete", "name": name, "path": directory}
        resp = send_command_with_retry("manage_script", params)
        return resp if isinstance(resp, dict) else {"success": False, "message": str(resp)}

    @mcp.tool()
    def validate_script(
        ctx: Context, uri: str, level: str = "basic"
    ) -> Dict[str, Any]:
        """Validate a C# script and return diagnostics."""
        name, directory = _split_uri(uri)
        params = {
            "action": "validate",
            "name": name,
            "path": directory,
            "level": level,
        }
        resp = send_command_with_retry("manage_script", params)
        return resp if isinstance(resp, dict) else {"success": False, "message": str(resp)}

    @mcp.tool()
    def manage_script(
        ctx: Context,
        action: str,
        name: str,
        path: str,
        contents: str,
        script_type: str,
        namespace: str,
    ) -> Dict[str, Any]:
        """Compatibility router for legacy script operations.

        IMPORTANT:
        - Direct file reads should use resources/read.
        - Edits should use apply_text_edits.

        Args:
            action: Operation ('create', 'read', 'update', 'delete').
            name: Script name (no .cs extension).
            path: Asset path (default: "Assets/").
            contents: C# code for 'create'/'update'.
            script_type: Type hint (e.g., 'MonoBehaviour').
            namespace: Script namespace.

        Returns:
            Dictionary with results ('success', 'message', 'data').
        """
        try:
            # Deprecate full-file update path entirely
            if action == 'update':
                return {"success": False, "message": "Deprecated: use apply_text_edits or resources/read + small edits."}

            # Prepare parameters for Unity
            params = {
                "action": action,
                "name": name,
                "path": path,
                "namespace": namespace,
                "scriptType": script_type,
            }

            # Base64 encode the contents if they exist to avoid JSON escaping issues
            if contents is not None:
                if action in ['create', 'update']:
                    params["encodedContents"] = base64.b64encode(contents.encode('utf-8')).decode('utf-8')
                    params["contentsEncoded"] = True
                else:
                    params["contents"] = contents

            params = {k: v for k, v in params.items() if v is not None}

            response = send_command_with_retry("manage_script", params)

            if isinstance(response, dict) and response.get("success"):
                if response.get("data", {}).get("contentsEncoded"):
                    decoded_contents = base64.b64decode(response["data"]["encodedContents"]).decode('utf-8')
                    response["data"]["contents"] = decoded_contents
                    del response["data"]["encodedContents"]
                    del response["data"]["contentsEncoded"]

                return {
                    "success": True,
                    "message": response.get("message", "Operation successful."),
                    "data": response.get("data"),
                }
            return response if isinstance(response, dict) else {
                "success": False,
                "message": str(response),
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Python error managing script: {str(e)}",
            }
