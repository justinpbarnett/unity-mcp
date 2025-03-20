from typing import Optional
from mcp.server.fastmcp import FastMCP, Context
from unity_connection import get_unity_connection

def register_asset_tools(mcp: FastMCP):
    """Register all asset management tools with the MCP server."""
    
    @mcp.tool()
    def import_asset(
        ctx: Context,
        source_path: str,
        target_path: str,
        overwrite: bool = False
    ) -> str:
        """Import an asset (e.g., 3D model, texture) into the Unity project.

        Args:
            ctx: The MCP context
            source_path: Path to the source file on disk
            target_path: Path where the asset should be imported in the Unity project (relative to Assets folder)
            overwrite: Whether to overwrite if an asset already exists at the target path (default: False)

        Returns:
            str: Success message or error details
        """
        try:
            unity = get_unity_connection()
            
            # Parameter validation
            if not source_path or not isinstance(source_path, str):
                return f"Error importing asset: source_path must be a valid string"
            
            if not target_path or not isinstance(target_path, str):
                return f"Error importing asset: target_path must be a valid string"
            
            # Check if the source file exists (on local disk)
            import os
            if not os.path.exists(source_path):
                return f"Error importing asset: Source file '{source_path}' does not exist"
            
            # Extract the target directory and filename
            target_dir = '/'.join(target_path.split('/')[:-1])
            target_filename = target_path.split('/')[-1]
            
            # Check if an asset already exists at the target path
            existing_assets = unity.send_command("GET_ASSET_LIST", {
                "search_pattern": target_filename,
                "folder": target_dir or "Assets"
            }).get("assets", [])
            
            # Check if any asset matches the exact path
            asset_exists = any(asset.get("path") == target_path for asset in existing_assets)
            if asset_exists and not overwrite:
                return f"Asset already exists at '{target_path}'. Use overwrite=True to replace it."
                
            response = unity.send_command("IMPORT_ASSET", {
                "source_path": source_path,
                "target_path": target_path,
                "overwrite": overwrite
            })
            
            if not response.get("success", False):
                return f"Error importing asset: {response.get('error', 'Unknown error')} (Source: {source_path}, Target: {target_path})"
                
            return response.get("message", "Asset imported successfully")
        except Exception as e:
            return f"Error importing asset: {str(e)} (Source: {source_path}, Target: {target_path})"

    @mcp.tool()
    def instantiate_prefab(
        ctx: Context,
        prefab_path: str,
        prefab_suffix: str = ".prefab",
        position_x: float = 0.0,
        position_y: float = 0.0,
        position_z: float = 0.0,
        rotation_x: float = 0.0,
        rotation_y: float = 0.0,
        rotation_z: float = 0.0,
    ) -> str:
        """Instantiate a prefab into the current scene at a specified location.

        Args:
            ctx: The MCP context
            prefab_path: Path to the prefab asset (relative to Assets folder)
            prefab_suffix: The suffix of the prefab file.Must to be included if
                           trying to instantiate something other than ".prefab"
                           are trying to get instantiated, like a model file
                           (".fbx", ".gltf" and others). (default: ".prefab")
            position_x: X position in world space (default: 0.0)
            position_y: Y position in world space (default: 0.0)
            position_z: Z position in world space (default: 0.0)
            rotation_x: X rotation in degrees (default: 0.0)
            rotation_y: Y rotation in degrees (default: 0.0)
            rotation_z: Z rotation in degrees (default: 0.0)

        Returns:
            str: Success message or error details
        """
        try:
            unity = get_unity_connection()
            prefab_suffix = prefab_suffix.lower()
            
            # Parameter validation
            if not prefab_path or not isinstance(prefab_path, str):
                return f"Error instantiating prefab: prefab_path must be a valid string"
                
            # Validate numeric parameters
            position_params = {
                "position_x": position_x,
                "position_y": position_y,
                "position_z": position_z,
                "rotation_x": rotation_x,
                "rotation_y": rotation_y,
                "rotation_z": rotation_z
            }
            
            for param_name, param_value in position_params.items():
                if not isinstance(param_value, (int, float)):
                    return f"Error instantiating prefab: {param_name} must be a number"
            
            # Check if the prefab exists
            prefab_dir = '/'.join(prefab_path.split('/')[:-1]) or "Assets"
            prefab_name = prefab_path.split('/')[-1]
            
            # Ensure prefab has .prefab extension for searching
            if not prefab_name.lower().endswith(prefab_suffix):
                prefab_name = f"{prefab_name}{prefab_suffix}"
                prefab_path = f"{prefab_path}{prefab_suffix}"
                
            prefab_assets = unity.send_command("GET_ASSET_LIST", {
                "type": "Prefab" if prefab_suffix == ".prefab" else "GameObject",
                "search_pattern": prefab_name.removesuffix(prefab_suffix),
                "folder": prefab_dir
            }).get("assets", [])
            
            prefab_exists = any(asset.get("path") == prefab_path for asset in prefab_assets)
            if not prefab_exists:
                return f"Prefab '{prefab_path}' not found in the project."
            
            response = unity.send_command("INSTANTIATE_PREFAB", {
                "prefab_path": prefab_path,
                "position_x": position_x,
                "position_y": position_y,
                "position_z": position_z,
                "rotation_x": rotation_x,
                "rotation_y": rotation_y,
                "rotation_z": rotation_z
            })
            
            if not response.get("success", False):
                return f"Error instantiating prefab: {response.get('error', 'Unknown error')} (Path: {prefab_path})"
                
            return f"Prefab instantiated successfully as '{response.get('instance_name', 'unknown')}'"
        except Exception as e:
            return f"Error instantiating prefab: {str(e)} (Path: {prefab_path})"

    @mcp.tool()
    def create_prefab(
        ctx: Context,
        object_name: str,
        prefab_path: str,
        overwrite: bool = False
    ) -> str:
        """Create a new prefab asset from a GameObject in the scene.

        Args:
            ctx: The MCP context
            object_name: Name of the GameObject in the scene to create prefab from
            prefab_path: Path where the prefab should be saved (relative to Assets folder)
            overwrite: Whether to overwrite if a prefab already exists at the path (default: False)

        Returns:
            str: Success message or error details
        """
        try:
            unity = get_unity_connection()
            
            # Parameter validation
            if not object_name or not isinstance(object_name, str):
                return f"Error creating prefab: object_name must be a valid string"
                
            if not prefab_path or not isinstance(prefab_path, str):
                return f"Error creating prefab: prefab_path must be a valid string"
            
            # Check if the GameObject exists
            found_objects = unity.send_command("FIND_OBJECTS_BY_NAME", {
                "name": object_name
            }).get("objects", [])
            
            if not found_objects:
                return f"GameObject '{object_name}' not found in the scene."
                
            # Verify prefab path has proper extension
            if not prefab_path.lower().endswith('.prefab'):
                prefab_path = f"{prefab_path}.prefab"
            
            # Check if a prefab already exists at this path
            prefab_dir = '/'.join(prefab_path.split('/')[:-1]) or "Assets"
            prefab_name = prefab_path.split('/')[-1]
            
            prefab_assets = unity.send_command("GET_ASSET_LIST", {
                "type": "Prefab",
                "search_pattern": prefab_name,
                "folder": prefab_dir
            }).get("assets", [])
            
            prefab_exists = any(asset.get("path") == prefab_path for asset in prefab_assets)
            if prefab_exists and not overwrite:
                return f"Prefab already exists at '{prefab_path}'. Use overwrite=True to replace it."
            
            response = unity.send_command("CREATE_PREFAB", {
                "object_name": object_name,
                "prefab_path": prefab_path,
                "overwrite": overwrite
            })
            
            if not response.get("success", False):
                return f"Error creating prefab: {response.get('error', 'Unknown error')} (Object: {object_name}, Path: {prefab_path})"
                
            return f"Prefab created successfully at {response.get('path', prefab_path)}"
        except Exception as e:
            return f"Error creating prefab: {str(e)} (Object: {object_name}, Path: {prefab_path})"

    @mcp.tool()
    def apply_prefab(
        ctx: Context,
        object_name: str
    ) -> str:
        """Apply changes made to a prefab instance back to the original prefab asset.

        Args:
            ctx: The MCP context
            object_name: Name of the prefab instance in the scene

        Returns:
            str: Success message or error details
        """
        try:
            unity = get_unity_connection()
            
            # Check if the GameObject exists
            found_objects = unity.send_command("FIND_OBJECTS_BY_NAME", {
                "name": object_name
            }).get("objects", [])
            
            if not found_objects:
                return f"GameObject '{object_name}' not found in the scene."
            
            # Check if the object is a prefab instance
            object_props = unity.send_command("GET_OBJECT_PROPERTIES", {
                "name": object_name
            })
            
            # Try to extract prefab status from properties
            is_prefab_instance = object_props.get("isPrefabInstance", False)
            if not is_prefab_instance:
                return f"GameObject '{object_name}' is not a prefab instance."
            
            response = unity.send_command("APPLY_PREFAB", {
                "object_name": object_name
            })
            return response.get("message", "Prefab changes applied successfully")
        except Exception as e:
            return f"Error applying prefab changes: {str(e)}" 