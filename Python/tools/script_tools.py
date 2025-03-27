from mcp.server.fastmcp import FastMCP, Context
from typing import List,Optional
from unity_connection import get_unity_connection
import base64


def register_script_tools(mcp: FastMCP):
    """Register all script-related tools with the MCP server."""

    @mcp.tool()
    def view_script(ctx: Context, script_path: str, require_exists: bool = True) -> str:
        """View the contents of a Unity script file.

        Args:
            ctx: The MCP context
            script_path: Path to the script file relative to the Assets folder
            require_exists: Whether to raise an error if the file doesn't exist (default: True)

        Returns:
            str: The contents of the script file or error message
        """
        try:
            # Normalize script path to ensure it has the correct format
            if not script_path.startswith("Assets/"):
                script_path = f"Assets/{script_path}"

            # Debug to help diagnose issues
            print(f"ViewScript - Using normalized script path: {script_path}")

            # Send command to Unity to read the script file
            response = get_unity_connection().send_command(
                "VIEW_SCRIPT",
                {"script_path": script_path, "require_exists": require_exists},
            )

            if response.get("exists", True):
                if response.get("encoding", "base64") == "base64":
                    decoded_content = base64.b64decode(response.get("content")).decode(
                        "utf-8"
                    )
                    return decoded_content
                return response.get("content", "Script contents not available")
            else:
                return response.get("message", "Script not found")
        except Exception as e:
            return f"Error viewing script: {str(e)}"

    @mcp.tool()
    def create_script(
        ctx: Context,
        script_name: str,
        script_type: str = "MonoBehaviour",
        namespace: Optional[str] = None,
        template: Optional[str] = None,
        script_folder: Optional[str] = None,
        overwrite: bool = False,
        content: Optional[str] = None,
    ) -> str:
        """Create a new Unity script file.

        Args:
            ctx: The MCP context
            script_name: Name of the script (without .cs extension)
            script_type: Type of script (e.g., MonoBehaviour, ScriptableObject)
            namespace: Optional namespace for the script
            template: Optional custom template to use
            script_folder: Optional folder path within Assets to create the script
            overwrite: Whether to overwrite if script already exists (default: False)
            content: Optional custom content for the script

        Returns:
            str: Success message or error details
        """
        try:
            unity = get_unity_connection()

            # Determine script path based on script_folder parameter
            if script_folder:
                # Use provided folder path
                # Normalize the folder path first
                if script_folder.startswith("Assets/"):
                    normalized_folder = script_folder
                else:
                    normalized_folder = f"Assets/{script_folder}"

                # Create the full path
                if normalized_folder.endswith("/"):
                    script_path = f"{normalized_folder}{script_name}.cs"
                else:
                    script_path = f"{normalized_folder}/{script_name}.cs"

                # Debug to help diagnose issues
                print(f"CreateScript - Folder: {script_folder}")
                print(f"CreateScript - Normalized folder: {normalized_folder}")
                print(f"CreateScript - Script path: {script_path}")
            else:
                # Default to Scripts folder when no folder is provided
                script_path = f"Assets/Scripts/{script_name}.cs"
                print(f"CreateScript - Using default script path: {script_path}")

            # Send command to Unity to create the script directly
            # The C# handler will handle the file existence check
            params = {
                "script_name": script_name,
                "script_type": script_type,
                "namespace": namespace,
                "template": template,
                "overwrite": overwrite,
            }

            # Add script_folder if provided
            if script_folder:
                params["script_folder"] = script_folder

            # Add content if provided
            if content:
                params["content"] = content

            response = unity.send_command("CREATE_SCRIPT", params)
            return response.get("message", "Script created successfully")
        except Exception as e:
            return f"Error creating script: {str(e)}"

    @mcp.tool()
    def update_script(
        ctx: Context,
        script_path: str,
        content: str,
        create_if_missing: bool = False,
        create_folder_if_missing: bool = False,
    ) -> str:
        """Update the contents of an existing Unity script.

        Args:
            ctx: The MCP context
            script_path: Path to the script file relative to the Assets folder
            content: New content for the script
            create_if_missing: Whether to create the script if it doesn't exist (default: False)
            create_folder_if_missing: Whether to create the parent directory if it doesn't exist (default: False)

        Returns:
            str: Success message or error details
        """
        try:
            unity = get_unity_connection()

            # Normalize script path to ensure it has the correct format
            # Make sure the path starts with Assets/ but not Assets/Assets/
            if not script_path.startswith("Assets/"):
                script_path = f"Assets/{script_path}"

            # Debug to help diagnose issues
            print(f"UpdateScript - Original path: {script_path}")

            # Parse script path (for potential creation)
            script_name = script_path.split("/")[-1]
            if not script_name.endswith(".cs"):
                script_name += ".cs"
                script_path = f"{script_path}.cs"

            if create_if_missing:
                # When create_if_missing is true, we'll just try to update directly,
                # and let Unity handle the creation if needed
                params = {
                    "script_path": script_path,
                    "content": content,
                    "create_if_missing": True,
                }

                # Add folder creation flag if requested
                if create_folder_if_missing:
                    params["create_folder_if_missing"] = True

                # Send command to Unity to update/create the script
                response = unity.send_command("UPDATE_SCRIPT", params)
                return response.get("message", "Script updated successfully")
            else:
                # Standard update without creation flags
                response = unity.send_command(
                    "UPDATE_SCRIPT", {"script_path": script_path, "content": content}
                )
                return response.get("message", "Script updated successfully")
        except Exception as e:
            return f"Error updating script: {str(e)}"

    @mcp.tool()
    def list_scripts(ctx: Context, folder_path: str = "Assets") -> str:
        """List all script files in a specified folder.

        Args:
            ctx: The MCP context
            folder_path: Path to the folder to search (default: Assets)

        Returns:
            str: List of script files or error message
        """
        try:
            # Send command to Unity to list scripts
            response = get_unity_connection().send_command(
                "LIST_SCRIPTS", {"folder_path": folder_path}
            )
            scripts = response.get("scripts", [])
            if not scripts:
                return "No scripts found in the specified folder"
            return "\n".join(scripts)
        except Exception as e:
            return f"Error listing scripts: {str(e)}"

    @mcp.tool()
    def attach_script(
        ctx: Context, object_name: str, script_name: str, script_path: Optional[str] = None
    ) -> str:
        """Attach a script component to a GameObject.

        Args:
            ctx: The MCP context
            object_name: Name of the target GameObject in the scene
            script_name: Name of the script to attach (with or without .cs extension)
            script_path: Optional full path to the script (if not in the default Scripts folder)

        Returns:
            str: Success message or error details
        """
        try:
            unity = get_unity_connection()

            # Check if the object exists
            object_response = unity.send_command(
                "FIND_OBJECTS_BY_NAME", {"name": object_name}
            )

            objects = object_response.get("objects", [])
            if not objects:
                return f"GameObject '{object_name}' not found in the scene."

            # Ensure script_name has .cs extension
            if not script_name.lower().endswith(".cs"):
                script_name = f"{script_name}.cs"

            # Remove any path information from script_name if it contains slashes
            script_basename = script_name.split("/")[-1]

            # Determine the full script path if provided
            if script_path is not None:
                # Ensure script_path starts with Assets/
                if not script_path.startswith("Assets/"):
                    script_path = f"Assets/{script_path}"

                # If path is just a directory, append the script name
                if not script_path.endswith(script_basename):
                    if script_path.endswith("/"):
                        script_path = f"{script_path}{script_basename}"
                    else:
                        script_path = f"{script_path}/{script_basename}"

            # Check if the script is already attached
            object_props = unity.send_command(
                "GET_OBJECT_PROPERTIES", {"name": object_name}
            )

            # Extract script name without .cs and without path for component type checking
            script_class_name = script_basename.replace(".cs", "")

            # Check if component is already attached
            components = object_props.get("components", [])
            for component in components:
                if component.get("type") == script_class_name:
                    return f"Script '{script_class_name}' is already attached to '{object_name}'."

            # Send command to Unity to attach the script
            params = {"object_name": object_name, "script_name": script_basename}

            # Add script_path if provided
            if script_path:
                params["script_path"] = script_path

            response = unity.send_command("ATTACH_SCRIPT", params)
            return response.get("message", "Script attached successfully")
        except Exception as e:
            return f"Error attaching script: {str(e)}"
