from mcp.server.fastmcp import FastMCP, Context
from typing import List, Dict, Any, Optional
import json
from unity_connection import get_unity_connection

def register_scene_tools(mcp: FastMCP):
    """Register all scene-related tools with the MCP server."""
    
    @mcp.tool()
    def get_scene_info(ctx: Context) -> str:
        """Retrieve detailed info about the current Unity scene.
        
        Returns:
            str: JSON string containing scene information including:
                - sceneName: Name of the current scene
                - rootObjects: List of root GameObject names in the scene
        """
        try:
            unity = get_unity_connection()
            result = unity.send_command("GET_SCENE_INFO")
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting scene info: {str(e)}"

    @mcp.tool()
    def open_scene(ctx: Context, scene_path: str) -> str:
        """Open a specified scene in the Unity editor.
        
        Args:
            scene_path: Full path to the scene file (e.g., "Assets/Scenes/MyScene.unity")
            
        Returns:
            str: Success message or error details
        """
        try:
            unity = get_unity_connection()
            
            # Check if the scene exists in the project
            scenes = unity.send_command("GET_ASSET_LIST", {
                "type": "Scene",
                "search_pattern": scene_path.split('/')[-1],
                "folder": '/'.join(scene_path.split('/')[:-1]) or "Assets"
            }).get("assets", [])
            
            # Check if any scene matches the exact path
            scene_exists = any(scene.get("path") == scene_path for scene in scenes)
            if not scene_exists:
                return f"Scene at '{scene_path}' not found in the project."
                
            result = unity.send_command("OPEN_SCENE", {"scene_path": scene_path})
            return result.get("message", "Scene opened successfully")
        except Exception as e:
            return f"Error opening scene: {str(e)}"

    @mcp.tool()
    def save_scene(ctx: Context) -> str:
        """Save the current scene to its file.
        
        Returns:
            str: Success message or error details
        """
        try:
            unity = get_unity_connection()
            result = unity.send_command("SAVE_SCENE")
            return result.get("message", "Scene saved successfully")
        except Exception as e:
            return f"Error saving scene: {str(e)}"

    @mcp.tool()
    def new_scene(ctx: Context, scene_path: str, overwrite: bool = False) -> str:
        """Create a new empty scene in the Unity editor.
        
        Args:
            scene_path: Full path where the new scene should be saved (e.g., "Assets/Scenes/NewScene.unity")
            overwrite: Whether to overwrite if scene already exists (default: False)
            
        Returns:
            str: Success message or error details
        """
        try:
            unity = get_unity_connection()
            
            # Check if a scene with this path already exists
            scenes = unity.send_command("GET_ASSET_LIST", {
                "type": "Scene",
                "search_pattern": scene_path.split('/')[-1],
                "folder": '/'.join(scene_path.split('/')[:-1]) or "Assets"
            }).get("assets", [])
            
            # Check if any scene matches the exact path
            scene_exists = any(scene.get("path") == scene_path for scene in scenes)
            if scene_exists and not overwrite:
                return f"Scene at '{scene_path}' already exists. Use overwrite=True to replace it."
            
            # Create new scene
            result = unity.send_command("NEW_SCENE", {
                "scene_path": scene_path,
                "overwrite": overwrite
            })
            
            # Save the scene to ensure it's properly created
            unity.send_command("SAVE_SCENE")
            
            # Get scene info to verify it's loaded
            scene_info = unity.send_command("GET_SCENE_INFO")
            
            return result.get("message", "New scene created successfully")
        except Exception as e:
            return f"Error creating new scene: {str(e)}"

    @mcp.tool()
    def change_scene(ctx: Context, scene_path: str, save_current: bool = False) -> str:
        """Change to a different scene, optionally saving the current one.
        
        Args:
            scene_path: Full path to the target scene file (e.g., "Assets/Scenes/TargetScene.unity")
            save_current: Whether to save the current scene before changing (default: False)
            
        Returns:
            str: Success message or error details
        """
        try:
            unity = get_unity_connection()
            result = unity.send_command("CHANGE_SCENE", {
                "scene_path": scene_path,
                "save_current": save_current
            })
            return result.get("message", "Scene changed successfully")
        except Exception as e:
            return f"Error changing scene: {str(e)}"

    @mcp.tool()
    def get_object_info(ctx: Context, object_name: str) -> str:
        """
        Get info about a specific game object.
        
        Args:
            object_name: Name of the game object.
        """
        try:
            unity = get_unity_connection()
            result = unity.send_command("GET_OBJECT_INFO", {"name": object_name})
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error getting object info: {str(e)}"

    @mcp.tool()
    def create_object(
        ctx: Context,
        type: str = "CUBE",
        name: str = None,
        location: List[float] = None,
        rotation: List[float] = None,
        scale: List[float] = None,
        replace_if_exists: bool = False
    ) -> str:
        """
        Create a game object in the Unity scene.
        
        Args:
            type: Object type (CUBE, SPHERE, CYLINDER, CAPSULE, PLANE, EMPTY, CAMERA, LIGHT).
            name: Optional name for the game object.
            location: [x, y, z] position (defaults to [0, 0, 0]).
            rotation: [x, y, z] rotation in degrees (defaults to [0, 0, 0]).
            scale: [x, y, z] scale factors (defaults to [1, 1, 1]).
            replace_if_exists: Whether to replace if an object with the same name exists (default: False)
        
        Returns:
            Confirmation message with the created object's name.
        """
        try:
            unity = get_unity_connection()
            
            # Check if an object with the specified name already exists (if name is provided)
            if name:
                found_objects = unity.send_command("FIND_OBJECTS_BY_NAME", {
                    "name": name
                }).get("objects", [])
                
                if found_objects and not replace_if_exists:
                    return f"Object with name '{name}' already exists. Use replace_if_exists=True to replace it."
                elif found_objects and replace_if_exists:
                    # Delete the existing object
                    unity.send_command("DELETE_OBJECT", {"name": name})
            
            # Create the new object
            params = {
                "type": type.upper(),
                "location": location or [0, 0, 0],
                "rotation": rotation or [0, 0, 0],
                "scale": scale or [1, 1, 1]
            }
            if name:
                params["name"] = name
                
            result = unity.send_command("CREATE_OBJECT", params)
            return f"Created {type} game object: {result['name']}"
        except Exception as e:
            return f"Error creating game object: {str(e)}"

    @mcp.tool()
    def modify_object(
        ctx: Context,
        name: str,
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
        visible: Optional[bool] = None,
        set_parent: Optional[str] = None,
        add_component: Optional[str] = None,
        remove_component: Optional[str] = None,
        set_property: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Modify a game object's properties and components.
        
        Args:
            name: Name of the game object to modify.
            location: Optional [x, y, z] position.
            rotation: Optional [x, y, z] rotation in degrees.
            scale: Optional [x, y, z] scale factors.
            visible: Optional visibility toggle.
            set_parent: Optional name of the parent object to set.
            add_component: Optional name of the component type to add (e.g., "Rigidbody", "BoxCollider").
            remove_component: Optional name of the component type to remove.
            set_property: Optional dict with keys:
                - component: Name of the component type
                - property: Name of the property to set
                - value: Value to set the property to
        
        Returns:
            str: Success message or error details
        """
        try:
            unity = get_unity_connection()
            
            # Check if the object exists
            found_objects = unity.send_command("FIND_OBJECTS_BY_NAME", {
                "name": name
            }).get("objects", [])
            
            if not found_objects:
                return f"Object with name '{name}' not found in the scene."
            
            # If set_parent is provided, check if parent object exists
            if set_parent is not None:
                parent_objects = unity.send_command("FIND_OBJECTS_BY_NAME", {
                    "name": set_parent
                }).get("objects", [])
                
                if not parent_objects:
                    return f"Parent object '{set_parent}' not found in the scene."
            
            # If we're adding a component, we could also check if it's already attached
            if add_component is not None:
                object_props = unity.send_command("GET_OBJECT_PROPERTIES", {
                    "name": name
                })
                
                components = object_props.get("components", [])
                component_exists = any(comp.get("type") == add_component for comp in components)
                
                if component_exists:
                    return f"Component '{add_component}' is already attached to '{name}'."
            
            # If we're removing a component, check if it exists
            if remove_component is not None:
                object_props = unity.send_command("GET_OBJECT_PROPERTIES", {
                    "name": name
                })
                
                components = object_props.get("components", [])
                component_exists = any(comp.get("type") == remove_component for comp in components)
                
                if not component_exists:
                    return f"Component '{remove_component}' is not attached to '{name}'."
            
            params = {"name": name}
            
            # Add basic transform properties
            if location is not None:
                params["location"] = location
            if rotation is not None:
                params["rotation"] = rotation
            if scale is not None:
                params["scale"] = scale
            if visible is not None:
                params["visible"] = visible
                
            # Add parent setting
            if set_parent is not None:
                params["set_parent"] = set_parent
                
            # Add component operations
            if add_component is not None:
                params["add_component"] = add_component
            if remove_component is not None:
                params["remove_component"] = remove_component
                
            # Add property setting
            if set_property is not None:
                params["set_property"] = set_property
                
            result = unity.send_command("MODIFY_OBJECT", params)
            return f"Modified game object: {result['name']}"
        except Exception as e:
            return f"Error modifying game object: {str(e)}"

    @mcp.tool()
    def delete_object(ctx: Context, name: str, ignore_missing: bool = False) -> str:
        """
        Remove a game object from the scene.
        
        Args:
            name: Name of the game object to delete.
            ignore_missing: Whether to silently ignore if the object doesn't exist (default: False)
        
        Returns:
            str: Success message or error details
        """
        try:
            unity = get_unity_connection()
            
            # Check if the object exists
            found_objects = unity.send_command("FIND_OBJECTS_BY_NAME", {
                "name": name
            }).get("objects", [])
            
            if not found_objects:
                if ignore_missing:
                    return f"No object named '{name}' found to delete. Ignoring."
                else:
                    return f"Error: Object '{name}' not found in the scene."
            
            result = unity.send_command("DELETE_OBJECT", {"name": name})
            return f"Deleted game object: {name}"
        except Exception as e:
            return f"Error deleting game object: {str(e)}" 